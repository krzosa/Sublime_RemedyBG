from .Pywin32 import setup
import win32pipe, win32file, pywintypes, win32api
import subprocess, os, io, ctypes
import sublime, sublime_plugin
from .remedy_api import *

def get_remedy_variable(name, default):
    settings = sublime.load_settings("Preferences.sublime-settings")
    result = settings.get(name)
    if result != None:
        return result

    settings = sublime.load_settings("Remedy.sublime-settings")
    result = settings.get(name)
    if result != None:
        return result

    return default

def get_current_dir(window):
    vars = window.extract_variables()
    result = vars.get("project_path")
    if result == None:
        result = vars.get("folder")
        if result == None:
            result = vars.get("file_path")
            if result == None:
                sublime.message_dialog("RemedyBG: Trying to launch but cant figure out starting directory, open a file or project")
                return None
    return result

class RemedyInstance:
    def __init__(self):
        self.cmd_pipe = None
        self.event_pipe = None
        self.process = None
        self.servername = ""

    def begin_command(self, cmd):
        cmd_buffer = io.BytesIO()
        cmd_buffer.write(ctypes.c_uint16(cmd))
        return cmd_buffer

    def end_command(self, cmd_buffer):
        if self.cmd_pipe == None:
            return 0

        try:
            out_data = win32pipe.TransactNamedPipe(self.cmd_pipe, cmd_buffer.getvalue(), 8192, None)
        except pywintypes.error as pipe_error:
            print('RemedyBG: ', pipe_error)
            self.close()
            return 0

        out_buffer = io.BytesIO(out_data[1])
        result_code = int.from_bytes(out_buffer.read(2), 'little')
        if result_code != 1:
            cmd_buffer.seek(0)
            cmd = int.from_bytes(out_buffer.read(2), 'little')
            sublime.message_dialog('RemedyBG: ' + str(cmd) + ' failed')
        return out_buffer, result_code

    def set_bring_to_foreground_on_suspended(self, enabled = True):
        buff = self.begin_command(COMMAND_SET_BRING_TO_FOREGROUND_ON_SUSPENDED)
        buff.write(ctypes.c_uint8(enabled))
        buff, result_code = self.end_command(buff)
        if result_code != 1:
            print("set_bring_to_foreground_on_suspended")

    def add_breakpoint_at_filename_line(self, view, filename, line, region, expr = None):
        buff = self.begin_command(COMMAND_ADD_BREAKPOINT_AT_FILENAME_LINE)
        buff.write(ctypes.c_uint16(len(filename)))
        buff.write(bytes(filename, 'utf-8'))
        buff.write(ctypes.c_uint32(line))
        if expr:
            buff.write(ctypes.c_uint16(len(expr)))
            buff.write(bytes(expr, 'utf-8'))
        else:
            buff.write(ctypes.c_uint16(0))

        buff, result_code = self.end_command(buff)

    def run_to_file_at_line(self, filename, line):
        buff = self.begin_command(COMMAND_RUN_TO_FILE_AT_LINE)
        buff.write(ctypes.c_uint16(len(filename)))
        buff.write(bytes(filename, 'utf-8'))
        buff.write(ctypes.c_uint32(line))
        buff, result_code = self.end_command(buff)

    def goto_file_at_line(self, filename, line):
        buff = self.begin_command(COMMAND_GOTO_FILE_AT_LINE)
        buff.write(ctypes.c_uint16(len(filename)))
        buff.write(bytes(filename, 'utf-8'))
        buff.write(ctypes.c_uint32(line))
        buff, result_code = self.end_command(buff)

    def get_target_state(self):
        buff = self.begin_command(COMMAND_GET_TARGET_STATE)
        buff, result_code = self.end_command(buff)
        if result_code == 1:
            return int.from_bytes(buff.read(2), 'little')
        return 0

    def add_watch(self, expr):
        buff = self.begin_command(COMMAND_ADD_WATCH)
        buff.write(ctypes.c_uint8(1))     # watch window 1
        buff.write(ctypes.c_uint16(len(expr)))
        buff.write(bytes(expr, 'utf-8'))
        buff.write(ctypes.c_uint16(0))
        buff, result_code = self.end_command(buff)
        if result_code == 1:
            return int.from_bytes(buff.read(4), 'little')
        return 0

    def send_command(self, cmd):
        buff = self.begin_command(cmd)
        if cmd == COMMAND_START_DEBUGGING:
            buff.write(ctypes.c_uint8(0))
        buff, result_code = self.end_command(buff)
        return buff, result_code

    def stop_debugging(self):
        if self.get_target_state() != TARGETSTATE_NONE:
            self.send_command(COMMAND_STOP_DEBUGGING)

    def is_connected(self):
        result = self.cmd_pipe != None
        return result

    def close(self):
        if self.cmd_pipe:
            win32file.CloseHandle(self.cmd_pipe)
            self.cmd_pipe = None

        if self.event_pipe is not None:
            win32file.CloseHandle(self.event_pipe)
            self.event_pipe = None

        if self.process is not None:
            self.process.kill()
            self.process = None

        print("RemedyBG: Connection closed")

    def try_launching(self):
        if self.process == None:
            self.figure_out_target_and_launch()
            return True
        return False

    def cmd_pipe_name(self):
        return "\\\\.\\pipe\\" + self.servername

    def event_pipe_name(self):
        return "\\\\.\\pipe\\" + self.servername + "-events"

    def figure_out_target_and_launch(self):
        self.window = sublime.active_window()

        current_dir = get_current_dir(self.window)
        remedy_target = None
        search_for_remedy_file = get_remedy_variable("search_for_remedy_file_in_current_dir", True)
        if search_for_remedy_file:
            for it in os.listdir(current_dir):
                if it.endswith("rdbg"):
                    remedy_target = current_dir + "/" + it

        if remedy_target:
            self.launch(remedy_target)
            return

        if current_dir == None: return
        self.current_dir = current_dir

        self.filelist = os.listdir(self.current_dir)
        def walk_the_user_to_executable(item_index):
            if item_index == -1:
                return
            item = self.filelist[item_index]
            item_path = self.current_dir + "/" + item
            if os.path.isdir(item_path):
                self.current_dir += "/" + item
                self.filelist = os.listdir(self.current_dir)
                self.window.show_quick_panel(self.filelist, walk_the_user_to_executable)
            elif os.path.isfile(item_path):
                self.launch(item_path)
        self.window.show_quick_panel(self.filelist, walk_the_user_to_executable)

    def launch(self, target):
        try:
            os.chdir(os.path.dirname(target))
            self.servername = "default"
            window = sublime.active_window()
            vars = window.extract_variables()
            project = vars.get("project_base_name")
            if project:
                self.servername = project + hex(hash(vars["project"]))
            else:
                folder = vars.get("folder")
                if folder:
                    self.servername = hex(hash(folder))
            print("RemedyBG: Server name = ", self.servername)


            cmd = [get_remedy_variable("executable", "remedybg.exe"), "--servername", self.servername, target]
            print("Launching Remedy with command: " + str(cmd))
            self.process = subprocess.Popen(cmd)

            import time
            wait_time = 0.1
            time.sleep(wait_time)
            pipe_success = False
            for retry in range(0, 5):
                try:
                    self.cmd_pipe = win32file.CreateFile(self.cmd_pipe_name(), win32file.GENERIC_READ|win32file.GENERIC_WRITE, \
                        0, None, win32file.OPEN_EXISTING, 0, None)
                except pywintypes.error:
                    time.sleep(wait_time)
                    wait_time = wait_time*2.0
                    continue
                except Exception as e:
                    sublime.error_message('RemedyBG: Pipe error:' +  str(e))
                    return False
                pipe_success = True
                break

            if not pipe_success:
                sublime.error_message('RemedyBG: Named pipe could not be opened to remedybg. Make sure remedybg version is above 0.3.8')
                return False

            win32pipe.SetNamedPipeHandleState(self.cmd_pipe, win32pipe.PIPE_READMODE_MESSAGE, None, None)

            assert self.event_pipe == None
            self.event_pipe = win32file.CreateFile(self.event_pipe_name(), win32file.GENERIC_READ|256, \
                0, None, win32file.OPEN_EXISTING, 0, None)
            win32pipe.SetNamedPipeHandleState(self.event_pipe, win32pipe.PIPE_READMODE_MESSAGE, None, None)

            print("RemedyBG: Connected")

            def update():
                global remedy_instance
                if self.process is None:
                    return
                if self.process and self.process.poll():
                    print('RemedyBG: quit with code: %i' % (self.process.poll()))
                    self.process = None
                    self.close()
                    return
                if self.process and self.event_pipe:
                    event_buffer, event_type = self.get_event()
                    self.process_event(event_buffer, event_type)

                sublime.set_timeout(update, 100)
            #update() end

            sublime.set_timeout(update, 100)
        except FileNotFoundError as not_found:
            sublime.error_message("RemedyBG: " + str(not_found) + ': ' + target)
        except pywintypes.error as connection_error:
            sublime.error_message("RemedyBG: " + str(connection_error))
        except OSError as os_error:
            sublime.error_message("RemedyBG: " + str(os_error))

    def process_event(self, event_buffer, event_type):
        if event_type == EVENTTYPE_EXIT_PROCESS:
            exit_code = int.from_bytes(event_buffer.read(4), 'little')
            #print('RemedyBG: Debugging terminated with exit code:', exit_code)

    def get_event(self):
        try:
            buffer, nbytes, result = win32pipe.PeekNamedPipe(self.event_pipe, 0)
            if nbytes:
                hr, data = win32file.ReadFile(self.event_pipe, nbytes, None)
                event_buffer = io.BytesIO(data)
                event_type = int.from_bytes(event_buffer.read(2), 'little')
                return event_buffer, event_type
            return None, None
        except win32api.error as pipe_error:
            print('RemedyBG: Error occured while trying to update, we got disconnected:', pipe_error)
            self.close()
            return None, None

    def filename_and_line():
        window = sublime.active_window()
        view = window.active_view()
        sel = view.sel()[0].b
        line = view.rowcol(sel)[0] + 1
        filename = view.file_name()
        return filename, line, sel

    def run_to_cursor(self):
        filename, line, cursor = RemedyInstance.filename_and_line()
        self.run_to_file_at_line(filename, line)

    def goto_cursor(self):
        filename, line, cursor = RemedyInstance.filename_and_line()
        self.goto_file_at_line(filename, line)

    def breakpoint_on_cursor(self, view):
        filename, line, cursor = RemedyInstance.filename_and_line()
        self.add_breakpoint_at_filename_line(view, filename, line, sublime.Region(cursor))


remedy_instance = RemedyInstance()

class RemedyLaunchCommand(sublime_plugin.WindowCommand):
    def run(self):
        remedy_instance.figure_out_target_and_launch()

class RemedyStartDebuggingCommand(sublime_plugin.WindowCommand):
    def run(self):
        if remedy_instance.try_launching(): return

        state = remedy_instance.get_target_state()
        if state == TARGETSTATE_NONE:
            remedy_instance.send_command(COMMAND_START_DEBUGGING)
        elif state == TARGETSTATE_SUSPENDED:
            remedy_instance.send_command(COMMAND_CONTINUE_EXECUTION)

class RemedyStopDebuggingCommand(sublime_plugin.WindowCommand):
    def run(self):
        if remedy_instance.try_launching(): return
        remedy_instance.stop_debugging()

class RemedyRestartDebuggingCommand(sublime_plugin.WindowCommand):
    def run(self):
        if remedy_instance.try_launching(): return
        state = remedy_instance.get_target_state()
        if state == TARGETSTATE_EXECUTING or state == TARGETSTATE_SUSPENDED:
            remedy_instance.send_command(COMMAND_RESTART_DEBUGGING)

class RemedyRunToCursorCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if remedy_instance.try_launching(): return
        window = sublime.active_window()
        remedy_instance.run_to_cursor()

class RemedyGotoCursorCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if remedy_instance.try_launching(): return
        remedy_instance.goto_cursor()

class RemedySetBreakpointCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if remedy_instance.try_launching(): return
        remedy_instance.breakpoint_on_cursor(self.view)

class RemedySetConditionalBreakpointCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if remedy_instance.try_launching(): return
        window = self.view.window()

        def on_done(expr):
            filename, line, cursor = RemedyInstance.filename_and_line()
            remedy_instance.add_breakpoint_at_filename_line(self.view, filename, line, sublime.Region(cursor), expr)

        window.show_input_panel("Enter conditional breakpoint expression:", "", on_done, None, None)

class RemedyAddToWatchCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if remedy_instance.try_launching(): return

        sel = self.view.sel()
        if len(sel) > 1:
            return

        region_cursor = sel[0]
        if region_cursor.a - region_cursor.b == 0:
            settings = self.view.settings()
            old_boundaries = settings.get("word_separators")
            settings.set("word_separators"," ;,")
            region_cursor = self.view.word(region_cursor)
            settings.set("word_separators", old_boundaries)

        remedy_instance.add_watch(self.view.substr(region_cursor))

def plugin_unloaded():
    remedy_instance.close()
"""
CREDITS
* septag - plugin is based on his 10x plugin https://github.com/slynch8/10x/blob/main/PythonScripts/RemedyBG/RemedyBG.py
"""

import subprocess
import os, io, ctypes

import sublime
import sublime_plugin

from Default.exec import ExecCommand

import win32pipe, win32file, pywintypes, win32api
from .remedy_api import *

class RemedyInstance:
    def __init__(self):
        self.cmd_pipe = None
        self.event_pipe = None
        self.process = None
        self.servername = ""
        self.breakpoints = {}

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
        if result_code == 1:
            bp_id = int.from_bytes(buff.read(4), 'little')
            key = filename + ":" + str(line)
            self.breakpoints[key] = {"id": bp_id, "view": view}
            view.add_regions(key, [region], scope="region.redish", icon="circle")

    def delete_breakpoint(self, filename, line):
        key = filename + ":" + str(line)
        id = self.breakpoints.get(key)
        if id:
            id = id
            buff = self.begin_command(COMMAND_DELETE_BREAKPOINT)
            buff.write(ctypes.c_uint32(id["id"]))
            buff, result_code = self.end_command(buff)
            self.breakpoints.pop(key)
            id["view"].erase_regions(key)

    def toggle_breakpoint(self, view, filename, line, region):
        key = filename + ":" + str(line)
        if key in self.breakpoints.keys():
            self.delete_breakpoint(filename, line)
        else:
            self.add_breakpoint_at_filename_line(view, filename, line, region)

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

    def get_breakpoint_locations(self, bp_id):
        if self.cmd_pipe is None:
            return 0
        cmd_buffer = io.BytesIO()
        cmd_buffer.write(ctypes.c_uint16(COMMAND_GET_BREAKPOINT_LOCATIONS))
        cmd_buffer.write(ctypes.c_uint32(bp_id))
        try:
            out_data = win32pipe.TransactNamedPipe(self.cmd_pipe, cmd_buffer.getvalue(), 8192, None)
        except pywintypes.error as pipe_error:
            print('RemedyBG', pipe_error)
            self.close()
            return ('', 0)

        out_buffer = io.BytesIO(out_data[1])
        result_code = int.from_bytes(out_buffer.read(2), 'little')
        if result_code == 1:
            num_locs = int.from_bytes(out_buffer.read(2), 'little')
            # TODO: do we have several locations for a single breakpoint ?
            if num_locs > 0:
                address = int.from_bytes(out_buffer.read(8), 'little')
                module_name = out_buffer.read(int.from_bytes(out_buffer.read(2), 'little')).decode('utf-8')
                filename = out_buffer.read(int.from_bytes(out_buffer.read(2), 'little')).decode('utf-8')
                line_num = int.from_bytes(out_buffer.read(4), 'little')
                return (filename, line_num)
            else:
                return ('', 0)
        else:
            return ('', 0)

    def send_command(self, cmd):
        buff = self.begin_command(cmd)
        if cmd == COMMAND_START_DEBUGGING:
            buff.write(ctypes.c_uint8(0))
        buff, result_code = self.end_command(buff)

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

        for k,v in self.breakpoints.items():
            v["view"].erase_region(k)
        self.breakpoints = {}

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

        remedy_target = None
        if remedy_target == None:
            project = self.window.project_data()
            if project and project.get("remedy_target"):
                remedy_target = project.get("remedy_target")
                remedy_target = sublime.expand_variables(remedy_target, self.window.extract_variables())

        if remedy_target:
            self.launch(remedy_target)
            return

        if remedy_target == None:
            vars = self.window.extract_variables()
            self.current_dir = vars.get("project_path")
            if self.current_dir == None:
                self.current_dir = vars.get("folder")
                if self.current_dir == None:
                    self.current_dir = vars.get("file_path")
                    if self.current_dir == None:
                        sublime.message_dialog("RemedyBG: Trying to launch but cant figure out starting directory, open a file or project")
                        return

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
            print('RemedyBG: Debugging terminated with exit code:', exit_code)
        elif event_type == EVENTTYPE_OUTPUT_DEBUG_STRING and self.settings.get("output_debug_strings_to_console", False):
            text = event_buffer.read(int.from_bytes(event_buffer.read(2), 'little')).decode('utf-8')
            print(text.strip())
            i = 0
            while i < 3000:
                i += 1
                event_buffer, event_type = self.get_event()
                if event_type == EVENTTYPE_OUTPUT_DEBUG_STRING:
                    text = event_buffer.read(int.from_bytes(event_buffer.read(2), 'little')).decode('utf-8')
                    print(text.strip())
                else:
                    self.process_event(event_buffer, event_type)
                    break
        elif event_type == EVENTTYPE_BREAKPOINT_ADDED: # @todo: The problem here is that we need to figure out a view to which the marker is going to be bound
            pass
            # bp_id = int.from_bytes(event_buffer.read(4), 'little')
            # filename, line = self.get_breakpoint_locations(bp_id)
            # if filename != "":
            #     key = filename + ":" + str(line) # @copy_paste
            #     self.breakpoints[key] = bp_id
            #     view.add_regions(key, [region], scope="region.redish", icon="circle")
        elif event_type == EVENTTYPE_BREAKPOINT_REMOVED:
            bp_id = int.from_bytes(event_buffer.read(4), 'little')
            key = None
            for k,v in self.breakpoints.items():
                if v["id"] == bp_id:
                    key = k
            if key:
                v = self.breakpoints[key]
                v["view"].erase_regions(key)
                self.breakpoints.pop(key)

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
        self.toggle_breakpoint(view, filename, line, sublime.Region(cursor))


remedy_instance = RemedyInstance()

def get_remedy_variable(var, default):
    settings = sublime.load_settings("Remedy.sublime-settings")
    result = settings.get(var)
    if result == None: result = default
    return result

def get_build_system(window):
    project = window.project_data()
    build = None
    if project:
        bs = project.get("build_systems")
        rbs = project.get("remedy_build_system")
        if bs:
            if len(bs) == 1:
                build = bs[0]
            elif rbs:
                for i in bs:
                    if rbs == i["name"]:
                        build = i
                        break

    # if build == None:
    #     settings = sublime.load_settings("Preferences.sublime-settings")
    #     bs = settings.get("remedy_chosen_build_system")
    #     if bs:
    #         sublime.


    return project, build

def should_build_before_debugging(window):
    build_before = get_remedy_variable("build_before_debugging", False)
    if build_before:
        project, build = get_build_system(window)
        if project == None or build == None:
            build_before = False

    return build_before

class RemedyBuildCommand(ExecCommand):
    def run(self, **kwargs):
        self.command = kwargs.get("command")
        if self.command == None:
            sublime.message_dialog("RemedyBG: remedy_build expects a command, one of [run_to_cursor, start_debugging, goto_cursor]\n\nexample :: \"args\":{\"command\": \"run_to_cursor\"}")

        project, build = get_build_system(self.window)
        if build == None:
            sublime.error_message("""
                 RemedyBG: You need a project and a build system inside that project to call this function,
                 Sublime API doesnt allow for querying the selected build system.
                 Look here to figure out the project format: https://www.sublimetext.com/docs/projects.html
                 Additionally you need a field called "remedy_build_system" to signal which
                 build system was chosen
            """)
            return

        if remedy_instance.try_launching():
            return

        self.window.run_command("save_all")

        kwargs = {
            "cmd": build.get("cmd", None),
            "shell_cmd": build.get("shell_cmd", None),
            "file_regex": build.get("file_regex", ""),
            "line_regex": build.get("line_regex", ""),
            "working_dir": build.get("working_dir", ""),
            "encoding": build.get("encoding", "utf-8"),
            "env": build.get("env", {}),
            "quiet": build.get("quiet", False),
            "kill": build.get("kill", False),
            "kill_previous": build.get("kill_previous", False),
            "update_annotations_only": build.get("update_annotations_only", False),
            "word_wrap": build.get("word_wrap", True),
            "syntax": build.get("syntax", "Packages/Text/Plain text.tmLanguage"),
        }

        variables = self.window.extract_variables()
        for key in ["cmd", "shell_cmd", "file_regex", "line_regex", "working_dir"]:
            if kwargs.get(key) != None:
                kwargs[key] = sublime.expand_variables(kwargs[key], variables)

        for key in os.environ.keys():
            if key not in kwargs["env"]:
                kwargs["env"][key] = os.environ[key]

        super().run(**kwargs)
    def on_finished(self, proc):
        super().on_finished(proc)

        if proc == self.proc and proc.killed == False and proc.exit_code() == 0:
            errs = self.output_view.find_all_results()
            if len(errs) == 0:
                if self.command == "run_to_cursor":
                    remedy_instance.run_to_cursor()
                elif self.command == "start_debugging":
                    remedy_instance.send_command(COMMAND_START_DEBUGGING)
                elif self.command == "goto_cursor":
                    remedy_instance.goto_cursor()
                else: # @warning: While adding here also need to change error message !!!!
                    sublime.message_dialog("RemedyBG: Unrecognized command =", self.command)



class RemedyLaunchCommand(sublime_plugin.WindowCommand):
    def run(self):
        remedy_instance.figure_out_target_and_launch()

class RemedyStartDebuggingCommand(sublime_plugin.WindowCommand):
    def run(self):
        if remedy_instance.try_launching(): return

        state = remedy_instance.get_target_state()
        if state == TARGETSTATE_NONE:
            if should_build_before_debugging(self.window):
                self.window.run_command("remedy_build", {"command": "start_debugging"})
            else:
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
        remedy_instance.send_command(COMMAND_RESTART_DEBUGGING)

class RemedyRunToCursorCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if remedy_instance.try_launching(): return
        window = sublime.active_window()
        if should_build_before_debugging(sublime.active_window()):
            window.run_command("remedy_build", {"command": "run_to_cursor"})
        else:
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

class RemedyOnBuildCommand(sublime_plugin.EventListener):
    def on_window_command(self, window, command_name, args):
        if remedy_instance.is_connected() == False:
            return
        if command_name in ["build", "remedy_build"]:
            if get_remedy_variable("stop_debugging_on_build_command", False):
                remedy_instance.stop_debugging()

def plugin_unloaded():
    remedy_instance.close()
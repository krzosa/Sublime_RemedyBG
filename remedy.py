import subprocess
import os, io, ctypes

import sublime
import sublime_plugin
from Default.exec import ExecCommand

import win32pipe, win32file, pywintypes
from .remedy_api import *

class RemedyInstance:
    def __init__(self):
        self.cmd_pipe = None
        self.event_pipe = None
        self.process = None
        self.servername = ""

    def send_command(self, cmd, **cmd_args):
        if self.cmd_pipe is None: return 0

        cmd_buffer = io.BytesIO()
        cmd_buffer.write(ctypes.c_uint16(cmd))

        if cmd == COMMAND_ADD_BREAKPOINT_AT_FILENAME_LINE:
            filepath = cmd_args['filename']
            cmd_buffer.write(ctypes.c_uint16(len(filepath)))
            cmd_buffer.write(bytes(filepath, 'utf-8'))
            cmd_buffer.write(ctypes.c_uint32(cmd_args['line']))
            cmd_buffer.write(ctypes.c_uint16(0))
        elif cmd == COMMAND_DELETE_BREAKPOINT:
            if cmd_args['id'] in self.breakpoints:
                rdbg_id = self.breakpoints[cmd_args['id']]
                cmd_buffer.write(ctypes.c_uint32(rdbg_id))
                self.breakpoints.pop(cmd_args['id'])
                if rdbg_id in self.breakpoints_rdbg:
                    self.breakpoints_rdbg.pop(rdbg_id)
            else:
                return 0
        elif cmd == COMMAND_GOTO_FILE_AT_LINE:
            filepath = cmd_args['filename']
            cmd_buffer.write(ctypes.c_uint16(len(filepath)))
            cmd_buffer.write(bytes(filepath, 'utf-8'))
            cmd_buffer.write(ctypes.c_uint32(cmd_args['line']))
        elif cmd == COMMAND_START_DEBUGGING:
            cmd_buffer.write(ctypes.c_uint8(0))
        elif cmd == COMMAND_STEP_INTO_BY_LINE:
            pass
        elif cmd == COMMAND_STEP_OVER_BY_LINE:
            pass
        elif cmd == COMMAND_STEP_OVER_BY_LINE:
            pass
        elif cmd == COMMAND_STOP_DEBUGGING:
            pass
        elif cmd == COMMAND_RESTART_DEBUGGING:
            pass
        elif cmd == COMMAND_CONTINUE_EXECUTION:
            pass
        elif cmd == COMMAND_RUN_TO_FILE_AT_LINE:
            filepath = cmd_args['filename']
            cmd_buffer.write(ctypes.c_uint16(len(filepath)))
            cmd_buffer.write(bytes(filepath, 'utf-8'))
            cmd_buffer.write(ctypes.c_uint32(cmd_args['line']))
        elif cmd == COMMAND_GET_TARGET_STATE:
            pass
        elif cmd == COMMAND_ADD_WATCH:
            print(cmd_args)
            expr = cmd_args['expr']
            cmd_buffer.write(ctypes.c_uint8(1))     # watch window 1
            cmd_buffer.write(ctypes.c_uint16(len(expr)))
            cmd_buffer.write(bytes(expr, 'utf-8'))
            cmd_buffer.write(ctypes.c_uint16(0))
        elif cmd == COMMAND_UPDATE_BREAKPOINT_LINE:
            if cmd_args['id'] in self.breakpoints:
                rdbg_id = self.breakpoints[cmd_args['id']]
                cmd_buffer.write(ctypes.c_uint32(rdbg_id))
                cmd_buffer.write(ctypes.c_uint32(cmd_args['line']))
        elif cmd == COMMAND_SET_WINDOW_POS:
            cmd_buffer.write(ctypes.c_int32(cmd_args['x']))
            cmd_buffer.write(ctypes.c_int32(cmd_args['y']))
            cmd_buffer.write(ctypes.c_int32(cmd_args['w']))
            cmd_buffer.write(ctypes.c_int32(cmd_args['h']))
        elif cmd == COMMAND_GET_WINDOW_POS:
            pass
        else:
            assert 0
            return 0        # not implemented


        try:
            out_data = win32pipe.TransactNamedPipe(self.cmd_pipe, cmd_buffer.getvalue(), 8192, None)
        except pywintypes.error as pipe_error:
            print('RDBG', pipe_error)
            self.close(stop=False)
            return 0

        out_buffer = io.BytesIO(out_data[1])
        result_code = int.from_bytes(out_buffer.read(2), 'little')
        if result_code == 1:
            if cmd == COMMAND_ADD_BREAKPOINT_AT_FILENAME_LINE:
                return 0
                # bp_id = int.from_bytes(out_buffer.read(4), 'little')
                # if bp_id not in self.breakpoints_rdbg:
                #     self.breakpoints[cmd_args['id']] = bp_id
                #     self.breakpoints_rdbg[bp_id] = (cmd_args['id'], cmd_args['filename'], cmd_args['line'])
                # else:
                #     print('RDBG: Breakpoint (%i) %s@%i skipped, because it will not get triggered' % (cmd_args['id'], cmd_args['filename'], cmd_args['line']))
                #     self.ignore_next_remove_breakpoint = True
                #     Editor.RemoveBreakpointById(cmd_args['id'])
                # return bp_id
            elif cmd == COMMAND_GET_TARGET_STATE:
                return int.from_bytes(out_buffer.read(2), 'little')
            elif cmd == COMMAND_ADD_WATCH:
                return int.from_bytes(out_buffer.read(4), 'little')
            elif cmd == COMMAND_GET_WINDOW_POS:
                x = int.from_bytes(out_buffer.read(4), 'little')
                y = int.from_bytes(out_buffer.read(4), 'little')
                w = int.from_bytes(out_buffer.read(4), 'little')
                h = int.from_bytes(out_buffer.read(4), 'little')
                return (x, y, w, h)
        else:
            sublime.message_dialog('RDBG: ' + str(cmd) + ' failed')
            return 0

        return 1

    def close(self, stop=True):
        if stop:
            self.stop()

        if self.cmd_pipe:
            win32file.CloseHandle(self.cmd_pipe)
            self.cmd_pipe = None

        if self.event_pipe is not None:
            win32file.CloseHandle(self.event_pipe)
            self.event_pipe = None

        if self.process is not None:
            self.process.kill()
            self.process = None

        print("RDBG: Connection closed")

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

        if remedy_target:
            self.launch(remedy_target)

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


            cmd = [get_remedy_executable(), "--servername", self.servername, target]
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
                if self.process is not None and self.process.poll() is not None:
                    print('RemedyBG: quit with code: %i' % (self.process.poll()))
                    self.process = None
                    self.close(stop=False)
                    return

                sublime.set_timeout(update, 1000)
            sublime.set_timeout(update, 1000)
        except FileNotFoundError as not_found:
            sublime.error_message("RemedyBG: " + str(not_found) + ': ' + target)
        except pywintypes.error as connection_error:
            sublime.error_message("RemedyBG: " + str(connection_error))
        except OSError as os_error:
            sublime.error_message("RemedyBG: " + str(os_error))

    def run_to_cursor(self):
        window = sublime.active_window()
        view = window.active_view()
        line = view.rowcol(view.sel()[0].b)[0] + 1
        file = view.file_name()
        self.send_command(COMMAND_RUN_TO_FILE_AT_LINE, filename=file, line=line)

    def goto_cursor(self):
        window = sublime.active_window()
        view = window.active_view()
        line = view.rowcol(view.sel()[0].b)[0] + 1
        file = view.file_name()
        self.send_command(COMMAND_GOTO_FILE_AT_LINE, filename=file, line=line)


remedy_instance = RemedyInstance()

def get_remedy_executable():
    window = sublime.active_window()
    settings = window.settings()
    result = settings.get("remedy_executable")
    if result == None:
        result = "remedybg"
    return result

def execute_process(view, cmd, offset = 1):
    line = view.rowcol(view.sel()[0].b)[0] + offset
    line = str(line)
    file = view.file_name()
    window = sublime.active_window()
    cmd = sublime.expand_variables(cmd, {"file": file, "line": line, "remedybg": get_remedy_executable()})
    print(cmd)
    subprocess.Popen(cmd)

class RemedyBuildCommand(ExecCommand):
    def run(self, **kwargs):
        self.command = kwargs.get("command")
        if self.command == None:
            sublime.message_dialog("RemedyBG: remedy_build expects a command, one of [run_to_cursor, start_debugging, goto_cursor]\n\nexample :: \"args\":{\"command\": \"run_to_cursor\"}")

        project = self.window.project_data()
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


        if project == None or build == None:
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
        super().run(**kwargs)
    def on_finished(self, proc):
        super().on_finished(proc)
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
        remedy_instance.send_command(COMMAND_START_DEBUGGING)

class RemedyStopDebuggingCommand(sublime_plugin.WindowCommand):
    def run(self):
        if remedy_instance.try_launching(): return
        remedy_instance.send_command(COMMAND_STOP_DEBUGGING)

class RemedyRestartDebuggingCommand(sublime_plugin.WindowCommand):
    def run(self):
        if remedy_instance.try_launching(): return
        remedy_instance.send_command(COMMAND_RESTART_DEBUGGING)

class RemedyRunToCursorCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if remedy_instance.try_launching(): return
        remedy_instance.run_to_cursor()

class RemedyGotoCursorCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if remedy_instance.try_launching(): return
        remedy_instance.goto_cursor()

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

        remedy_instance.send_command(COMMAND_ADD_WATCH, expr=self.view.substr(region_cursor))


class RemedyAllInOneCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if remedy_instance.try_launching():
            return

        sel = self.view.sel()
        if len(sel) > 1:
            return

        region_cursor = sel[0]
        settings = self.view.settings()
        old_boundaries = settings.get("word_separators")
        settings.set("word_separators"," ;,")
        region_word_on_cursor = self.view.word(region_cursor)
        settings.set("word_separators", old_boundaries)

        remedy_instance.goto_cursor()

        content = self.view.substr(region_word_on_cursor)
        if content == "r":
            remedy_instance.send_command(COMMAND_START_DEBUGGING)
            self.view.replace(edit, region_word_on_cursor, "")
        elif content == "rr":
            remedy_instance.send_command(COMMAND_STOP_DEBUGGING)
            self.view.replace(edit, region_word_on_cursor, "")
        elif content == "rrr":
            remedy_instance.send_command(COMMAND_RESTART_DEBUGGING)
            self.view.replace(edit, region_word_on_cursor, "")
        elif content == "rt":
            remedy_instance.run_to_cursor()
            self.view.replace(edit, region_word_on_cursor, "")
        else:
            remedy_instance.send_command(COMMAND_ADD_WATCH, expr=content)


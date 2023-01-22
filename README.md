
### RemedyBG debugger integration with Sublime Text

I frequently find that nothing beats the Visual Studio workflow.
You just click Ctrl+F10 and you are inspecting the code you have just written.
This package seeks to recreate that experience in Sublime Text but without
the buggy and slow Visual Studio, thanks to a much better debugger that is RemedyBG
and it's user API!

### Requirement

Obviously you need to have remedybg:

* https://remedybg.itch.io/remedybg

It needs to be available in the PATH with name ```remedybg.exe```. Alternatively you
can add ```"remedy_executable": "C:/path/to/remedy"``` to your settings.

### Remedy build system

Sadly Sublime doesn't allow for querying of currently chosen build system.
To make it so that you can build before starting to debug you need to have
a project / project file. That project file needs a build system, if there
is only one build system, everything is going to work. If there are more,
you will need to add a field called ```remedy_build_system```, here is an example:

```
{
	"folders":
	[
		{
			"path": "."
		}
	],
	"remedy_target": "this_is_optional/main.exe",
	"remedy_build_system": "first",
	"build_systems":
	[
		{
			"name": "first",
			"shell_cmd": "build.bat"
		}
	]
}
```

### All in one

Feature idea. By clicking using your middle mouse button you can issue most
of the available debugger commands.

	* Debugger goes to the place you clicked on
	* The word you clicked is going to get added to watch window
	* If the word you clicked on matches "rt"(run_to_cursor, "r"(run), "rr"(stop), "rrr"(restart) then it's going to delete that word in sublime and issue a debugger command. So far I have found it to be nice for code discovery kind of stuff with the mouse + keyboard workflow, you can bind this to the keyboard too though. The commands are easy to type using single hand.

### Credits

* septag - plugin is based on his 10x plugin https://github.com/slynch8/10x/blob/main/PythonScripts/RemedyBG/RemedyBG.py
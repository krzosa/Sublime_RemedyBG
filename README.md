
### RemedyBG debugger integration with Sublime Text

I frequently find that nothing beats the Visual Studio workflow.
You just click Ctrl+F10 and you are inspecting the code you have just written.
This package seeks to recreate that experience in Sublime Text but without
the buggy and slow Visual Studio, thanks to a much better debugger that is RemedyBG
and it's user API!

You can but the debugger here:

* https://remedybg.itch.io/remedybg

### Install

```
cd "%appdata%\Sublime Text\Packages"
git clone https://github.com/krzosa/Sublime_RemedyBG
```
Launch Sublime (maybe you will need Package Control + and call Package Control: Satisfy Dependencies?)

Optional:

* Add remedy_executable to your settings if remedybg is not on your path or has different name.
* Setup vcvarsall, Look at vcvarsall section in readme.

### Build before debugging

Sadly Sublime doesn't allow for querying of currently chosen build system.
Neither does it allow for effective hook into the builtin ```build``` command
with custom arguments as such this package needs to emulate the ```build``` command.

To make it so that you can build before debugging you need to firstly change
```Remedy.sublime-settings``` secondly, you need to have
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
### Setting up Microsoft compiler enviroment with vcvarsall.bat

If you are developing using remedybg it seems pretty obvious that you would want access to the Microsoft compiler so additionally the package is shipping with the ```setup_vsvars.py```. You need to update the path to your vcvarsall inside ```Remedy.sublime-settings``` or your global ```Preferences.sublime-settings```. THIS ONLY WORKS FOR REMEDY_BUILD!!! If you want to setup vcvarsall for the builtin ```build``` command, copy setup_vsvars.py to your ```User``` folder. You will have 2 copies one in remedy folder and the other in user folder. You need 2 copies because it seems that sublime heavily sandboxes packages from eachother so this package cannot influence the global enviroment. If anyone has any ideas how to make it global I would be happy to hear them.

Update these settings: (you can put them into global settings ```Preferences.sublime-settings``` or ```Remedy.sublime-settings```)
```
"vc_vars_cmd": "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat",
"vc_vars_arch": "amd64",
```

### All in one

Feature idea. By clicking using your middle mouse button you can issue most
of the available debugger commands.

* Debugger goes to the place you clicked on
* The word you clicked is going to get added to watch window
* If the word you clicked on matches "rt"(run_to_cursor), "r"(run), "rr"(stop), "rrr"(restart) then it's going to delete that word in sublime and issue a debugger command. So far I have found it to be nice for code discovery kind of stuff with the mouse + keyboard workflow, you can bind this to the keyboard too though. The commands are easy to type using single hand.

### Credits

* septag - plugin is based on his 10x plugin https://github.com/slynch8/10x/blob/main/PythonScripts/RemedyBG/RemedyBG.py
* OdatNurd - one of the sublime developers showed how to setup vsvarsall in sublime https://stackoverflow.com/questions/39881091/how-to-run-sublimetext-with-visual-studio-environment-enabled/
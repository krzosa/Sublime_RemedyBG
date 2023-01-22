
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

### Install

```
cd "%appdata%\Sublime Text\Packages"
git clone https://github.com/krzosa/Sublime_RemedyBG
```
Launch Sublime (maybe you will need Package Control + and call Package Control: Satisfy Dependencies?)

Optional:

* add remedy_executable to your settings if remedybg is not on your path or has different name.

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
### Setting up Microsoft compiler enviroment with vcvarsall.bat

If you are developing using remedybg it seems pretty obvious that you would want access to the Microsoft compiler so additionally the package is shipping with the ```setup_vsvars.py```. You can find it in the ```other``` folder. It sets up the vcvarsall paths for you, it was created by one of the sublime developers, I found it on Stack Overflow. You need to:

* Copy it into your User folder ```copy "%appdata%\Sublime Text\Packages\Sublime_RemedyBG\other\setup_vsvars.py" "%appdata%\Sublime Text\Packages\User\setup_vsvars.py"```
* Add to your sublime settings the path to vcvarsall, like this:

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
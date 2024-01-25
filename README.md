
### RemedyBG debugger integration with Sublime Text

I frequently find that nothing beats the Visual Studio workflow.
You just click Ctrl+F10 and you are inspecting the code you have just written.
This package seeks to recreate that experience in Sublime Text but without
the buggy and slow Visual Studio, thanks to a much better debugger that is RemedyBG
and it's user API!

You can buy the debugger here:

* https://remedybg.itch.io/remedybg

### Install

```
cd "%appdata%\Sublime Text\Packages"
git clone https://github.com/krzosa/Sublime_RemedyBG
```

- Make sure you have package control (Ctrl + Shift + P => Install Package Control)
- Ctrl + Shift + P => Satisfy Dependencies
- Restart Sublime

Optional:

- If remedybg is not on your path or has different name, change remedy_executable in your personal sublime settings, look at ```Remedy.sublime-settings``` for syntax reference.
- Setup visual studio developer's prompt or ```vcvarsall.bat```, look at vcvarsall section in readme.

### Usage

By default plugin binds to standard debugger hotkeys. You can edit them in your personal sublime keybindings, look at ```Default.sublime-keymap``` for syntax reference.
- Ctrl + F10: Run to cursor
- F5: Start debugging
- Shift + F5: Stop debugging
- F9: Set breakpoint
- Ctrl + Shift + F5 - Restart debugging

### Bonus: Build before debugging

Sadly Sublime doesn't allow for querying of currently chosen build system.
Neither does it allow for effective hook into the builtin ```build``` command
with custom arguments as such this package needs to emulate the ```build``` command.

To make it so that you can build before debugging you need to: firstly change
```Remedy.sublime-settings```, secondly you need to have
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
### Bonus: Setting up Microsoft compiler enviroment with ```vcvarsall.bat```

If you are developing using remedybg it seems pretty obvious that you would want access to the Microsoft compiler so additionally the package is shipping with the ```setup_vsvars.py```.

1. Copy content of ```setup_vcvarsall``` to your ```User``` folder for normal build commands or to ```Sublime_RemedyBG``` dir for build before debugging.
2. You need to update the path to your vcvarsall inside your global sublime settings/preferences, use ```Remedy.sublime-settings``` for reference.

If you want vcvars for both remedy_build and normal sublime build, you will need to have 2 copies, one in remedy folder and the other in user folder. You need 2 copies because it seems that sublime heavily sandboxes packages from eachother so this package cannot influence the global enviroment. If anyone has any ideas how to make it global I would be happy to hear them.

### Credits

* septag - plugin is based on his 10x plugin https://github.com/slynch8/10x/blob/main/PythonScripts/RemedyBG/RemedyBG.py
* OdatNurd - one of the sublime developers showed how to setup vsvarsall in sublime https://stackoverflow.com/questions/39881091/how-to-run-sublimetext-with-visual-studio-environment-enabled/

### RemedyBG debugger integration with Sublime Text

I frequently find that nothing at the present moment beats the Visual Studio workflow. You just click Ctrl+F10 and you are inspecting the code you have just written. This package seeks to recreate that experience in Sublime Text but without the buggy and slow Visual Studio, thanks to a much better debugger that is RemedyBG and it's user API!

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

- If remedybg is not on your path or has a different name, change remedy_executable in your personal sublime settings, look at ```Remedy.sublime-settings``` for syntax reference.
- Setup visual studio developer's prompt or ```vcvarsall.bat```, look at vcvarsall section in readme.

### Usage

By default plugin binds to standard debugger hotkeys. You can edit them in your personal sublime keybindings, look at ```Default.sublime-keymap``` for syntax reference.
- `Ctrl + F10`: Run to cursor
- `F5`: Start debugging
- `Shift + F5`: Stop debugging
- `F9`: Add breakpoint
- `Ctrl + F9`: Add conditional breakpoint
- `Ctrl + Shift + F5`: Restart debugging

### Bonus: Setting up Microsoft compiler enviroment with ```vcvarsall.bat```

If you are developing using remedybg it seems pretty obvious that you would want access to the Microsoft compiler so the package is shipping with ```setup_vsvars.py```.

1. Copy content of ```setup_vcvarsall``` to your ```User``` folder.
2. You need to provide path to your vcvarsall inside your global sublime settings/preferences, use ```Remedy.sublime-settings``` for reference.

### Credits

* septag - plugin is based on his 10x plugin https://github.com/slynch8/10x/blob/main/PythonScripts/RemedyBG/RemedyBG.py
* OdatNurd - one of the sublime developers showed how to setup vsvarsall in sublime https://stackoverflow.com/questions/39881091/how-to-run-sublimetext-with-visual-studio-environment-enabled/
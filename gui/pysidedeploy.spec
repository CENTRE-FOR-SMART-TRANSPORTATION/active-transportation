[app]
title = activetransportation
project_dir = .
input_file = main.py
project_file = gui.pyproject
exec_directory = releases/activetransportation/usr/bin
icon = assets/icon.png

[python]
python_path = venv/bin/python3.10
packages = Nuitka
android_packages = 

[qt]
qml_files = 
excluded_qml_plugins = 
modules = Core,Widgets,DBus,SerialPort,Gui,Network,Bluetooth
plugins = styles,iconengines,egldeviceintegrations,accessiblebridge,imageformats,platformthemes,platforminputcontexts,generic,xcbglintegrations,platforms

[android]
wheel_pyside = 
wheel_shiboken = 
plugins = 

[nuitka]
macos.permissions = 
extra_args = --quiet --noinclude-qt-translations

[buildozer]
mode = onefile
recipe_dir = 
jars_dir = 
ndk_path = 
sdk_path = 
local_libs = 
arch = 


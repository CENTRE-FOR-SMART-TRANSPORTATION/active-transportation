[app]
title = Active Transportation
project_dir = .
input_file = /home/krupal/Documents/projects/active_transportation/active-transportation/gui/main.py
project_file = gui.pyproject
exec_directory = release/activetransportation/usr/bin
icon = assets/icon.png

[python]
python_path = /home/krupal/Documents/projects/active_transportation/active-transportation/gui/venv/bin/python3.10
packages = Nuitka
android_packages = 

[qt]
qml_files = 
excluded_qml_plugins = 
modules = Core,Gui,Network,Bluetooth,Widgets,SerialPort,DBus
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


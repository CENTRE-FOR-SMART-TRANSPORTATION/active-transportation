[app]
title = activetransportation
project_dir = .
input_file = main.py
project_file = gui.pyproject
exec_directory = releases/activetransportation/usr/bin
icon = assets/icon.png

[python]
python_path = venv/bin/python
packages = Nuitka,numpy,scipy,pyserial,pyubx2,pysbf2,pygnssutils,mscl
android_packages = 

[qt]
qml_files = 
excluded_qml_plugins = 
modules = Bluetooth,Core,DBus,Gui,Network,SerialPort,Widgets
plugins = styles,iconengines,egldeviceintegrations,accessiblebridge,imageformats,platformthemes,platforminputcontexts,generic,xcbglintegrations,platforms

[android]
wheel_pyside = 
wheel_shiboken = 
plugins = 

[nuitka]
mode = onefile
macos.permissions = 
extra_args = --quiet --noinclude-qt-translations --static-libpython=no --include-package=mscl --include-module=mscl._mscl --jobs=2

[buildozer]
mode = onefile
recipe_dir = 
jars_dir = 
ndk_path = 
sdk_path = 
local_libs = 
arch = 


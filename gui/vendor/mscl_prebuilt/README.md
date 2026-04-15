# mscl (local prebuilt)

This folder packages a prebuilt MSCL Python extension (typically `_mscl.so`) so it can be installed into the project venv with `pip`, appear in `pip list`, and be bundled by `pyside6-deploy` / Nuitka.

It is intentionally minimal and assumes the compiled binary is compatible with the target platform and Python version.

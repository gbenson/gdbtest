Base image for GDB testing on Fedora 31
=======================================

* There's a GDB source RPM in `/gdbtest`, corresponding to whatever
  would have been installed by `dnf install gdb` at the time the
  image was created.
* All dependencies required to build it are installed.
* Also installed are Clang and Git.

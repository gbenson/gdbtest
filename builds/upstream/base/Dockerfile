FROM docker.io/gbenson/gdbtest-fedora31-base
LABEL maintainer="Gary Benson <gbenson@redhat.com>"

USER gdbtest
WORKDIR /gdbtest
RUN\
 rm -f gdb-*.src.rpm &&\
 git clone --quiet git://sourceware.org/git/binutils-gdb.git src

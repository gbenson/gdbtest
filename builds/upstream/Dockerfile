FROM docker.io/gbenson/gdbtest-fedora31-upstream-base
LABEL maintainer="Gary Benson <gbenson@redhat.com>"

RUN\
 mkdir build &&\
 cd build &&\
 CFLAGS="-g"\
 CXXFLAGS="-g"\
 ../src/configure\
 --with-system-readline\
 --with-separate-debug-dir=/usr/lib/debug\
 --with-gdb-datadir=/gdbtest/build/gdb/data-directory\
 --disable-binutils\
 --disable-gas\
 --disable-gold\
 --disable-gprof\
 --disable-intl\
 --disable-ld\
 --disable-sim &&\
 make $(rpmbuild --eval='%{?_smp_mflags}')

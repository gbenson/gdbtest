FROM docker.io/gbenson/gdbtest-fedora31-upstream
LABEL maintainer="Gary Benson <gbenson@redhat.com>"

RUN\
 make\
 -C /gdbtest/build\
 $(rpmbuild --eval='%{?_smp_mflags}')\
 -k\
 check\
 2>&1 | tee make-check.log\
 || true

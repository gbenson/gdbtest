FROM fedora:31
LABEL maintainer="Gary Benson <gbenson@redhat.com>"

RUN\
 dnf -y update &&\
 dnf -y install dnf-command'('{builddep,download}')' @buildsys-build\
 clang libomp-devel git &&\
 useradd -r --no-log-init -md/gdbtest gdbtest &&\
 cd /gdbtest &&\
 runuser -u gdbtest -- /usr/bin/dnf -y download --source gdb &&\
 runuser -u gdbtest -- /usr/bin/rpmbuild -rs --with testsuite gdb-*.src.rpm &&\
 dnf -y builddep rpmbuild/SRPMS/gdb-*.src.rpm &&\
 rm -rf rpmbuild &&\
 dnf clean all

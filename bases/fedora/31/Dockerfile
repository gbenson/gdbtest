FROM fedora:31
LABEL maintainer="Gary Benson <gbenson@redhat.com>"

RUN\
 dnf -y update &&\
 dnf -y install 'dnf-command(builddep)' 'dnf-command(download)' &&\
 dnf -y builddep gdb &&\
 dnf clean all&&\
 useradd -r --no-log-init -mb/ gdbtest

WORKDIR /gdbtest
USER gdbtest
RUN\
 dnf -y download --source gdb &&\
 rpm -ivh gdb-*-*.src.rpm &&\
 rm -f gdb-*-*.src.rpm&&\
 dnf clean all

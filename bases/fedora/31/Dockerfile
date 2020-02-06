FROM fedora:31
LABEL maintainer="Gary Benson <gbenson@redhat.com>"

RUN\
 dnf -y update &&\
 dnf -y install 'dnf-command(builddep)' 'dnf-command(download)' rpm-build &&\
 dnf -y builddep gdb &&\
 dnf clean all &&\
 useradd -r --no-log-init -md/gdbtest gdbtest

#XXX don't dnf clean before downloading srpm

WORKDIR /gdbtest
#USER gdbtest
#RUN\
# dnf -y download --source gdb &&\
# rpm -iv gdb-*-*.src.rpm &&\
# rm -f gdb-*-*.src.rpm&&\
# dnf clean all

FROM gbenson/p42-fedora-base

RUN dnf -y install 'dnf-command(builddep)'
                   'dnf-command(download)'
 && dnf -y builddep gdb
 && dnf -y download --source gdb
 && dnf clean all

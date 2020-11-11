#podman run -ti --privileged=true -v $PWD:$PWD -w $PWD docker.io/gbenson/lldb

FROM fedora:latest
LABEL maintainer="Gary Benson <gbenson@redhat.com>"

RUN\
 dnf -y update &&\
 dnf -y install clang lldb gdb &&\
 dnf clean all

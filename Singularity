Bootstrap: docker
From: ubuntu:20.04

%post
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
        build-essential ocaml ocamlbuild automake autoconf libtool \
        python-is-python3 libssl-dev git cmake perl libcurl4-openssl-dev \
        protobuf-compiler libprotobuf-dev debhelper reprepro unzip \
        lsb-release software-properties-common pkg-config libuv1-dev \
        python3-matplotlib emacs psmisc jq iproute2 wget iptables \
        libdevmapper1.02.1 apt-utils lsb-release software-properties-common \
        emacs psmisc jq iproute2

    # Install OpenSSL from source
    wget https://www.openssl.org/source/openssl-1.1.1i.tar.gz
    tar -xvzf openssl-1.1.1i.tar.gz
    cd openssl-1.1.1i
    ./config --prefix=/usr no-mdc2 no-idea
    make
    make install

    # Build salticidae
    cd /app/salticidae
    cmake . -DCMAKE_INSTALL_PREFIX=.
    make
    make install

    # Build server and client
    cd /app
    make server client keys

%files
    Makefile /app
    experiments.py /app
    App /app/App
    config /app/config
    salticidae /app/salticidae

%environment
    export DEBIAN_FRONTEND=noninteractive

%runscript
    /bin/bash
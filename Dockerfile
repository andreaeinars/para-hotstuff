# Use an official ocaml runtime as a parent image
# Install focal
FROM ubuntu:20.04

EXPOSE 80/tcp

# Set the working directory to /app
WORKDIR /app

# This is to avoid interactive questions from tzdata
ENV DEBIAN_FRONTEND=noninteractive

# install some requirements
RUN apt-get update \
    && apt-get install -y apt-utils git wget iptables libdevmapper1.02.1 \
    && apt-get install -y build-essential ocaml ocamlbuild automake autoconf libtool python-is-python3 libssl-dev git cmake perl \
    && apt-get install -y libcurl4-openssl-dev protobuf-compiler libprotobuf-dev debhelper reprepro unzip build-essential python \
    && apt-get install -y lsb-release software-properties-common \
    && apt-get install -y pkg-config libuv1-dev python3-matplotlib \
    && apt-get install -y emacs psmisc jq iproute2

# install a newer version of openssl
RUN wget https://www.openssl.org/source/openssl-1.1.1i.tar.gz \
    && tar -xvzf openssl-1.1.1i.tar.gz \
    && cd openssl-1.1.1i \
    && ./config --prefix=/usr no-mdc2 no-idea \
    && make \
    && make install

# Copy the current directory contents into the container at /app
COPY Makefile       /app
COPY experiments.py /app
#COPY enclave.token  /app
COPY App            /app/App
COPY salticidae     /app/salticidae

RUN mkdir -p /app/stats/

RUN cd /app/salticidae \
    && cmake . -DCMAKE_INSTALL_PREFIX=. \
    && make \
    && make install \
    && pwd
    
CMD ["/bin/bash"]

#### Once docker has been installed, run the following so that sudo won't be needed:
####     sudo groupadd docker
####     sudo gpasswd -a $USER docker
####     -> log out and back in, and then:
####     sudo service docker restart
#### build container: docker build -t para-hotstuff .
#### run container: docker run -td --expose=8000-9999 --network="host" --name damysus0 damysus
#### (alternatively) run container in interactive mode: docker container run -it damysus /bin/bash
#### docker exec -t damysus0 bash -c "source /opt/intel/sgxsdk/environment; make"

# Para-HotStuff

Base code and instructions from the thesis Enabling Parallel Voting in Streamlined Consensus Protocols 


## Installing

To tests our protocols, we provide a Python script, called
`experiments.py`, as well as a `Dockerfile` to create a Docker
container. We use the
[Salticidae](https://github.com/Determinant/salticidae) library, which
is added here as git submodule.

### Salticidae

You won't need to follow this step if you are using our Docker
container, as it is done when building the container, and can jump to
the next (Python) section.
If you decide to install Salticidae locally, you will need git and cmake.
In which case, after cloning the repository you need to type this to initialize the
Salticidae git submodule:

`git submodule init`

followed by:

`git submodule update`

Salticidea has the following dependencies:

* CMake >= 3.9
* C++14
* libuv >= 1.10.0
* openssl >= 1.1.0

`sudo apt install cmake libuv1-dev libssl-dev`

Then, to instance Salticidae, type:
`(cd salticidae; cmake . -DCMAKE_INSTALL_PREFIX=.; make; make install)`

### Python

We use python version 3.8.10.  You will need python3-pip to install
the required modules.

The Python script relies on the following modules:
- subprocess
- pathlib
- matplotlib
- time
- math
- os
- glob
- datetime
- argparse
- enum
- json
- multiprocessing
- random
- shutil
- re

If you haven't installed those modules yet, run:

`python3 -m pip install subprocess pathlib matplotlib time math os glob datetime argparse enum json multiprocessing random shutil re`

### Docker

To run the experiments within Docker containers, you need to have
installed Docker on your machine. This
[page](https://docs.docker.com/engine/install/) explains how to
install Docker. In particular follow the following
[instructions](https://docs.docker.com/engine/install/linux-postinstall/)
so that you can run Docker as a non-root user.

You then need to create the container by typing the following command at the root of the project:

`docker build -t para-hotstuff .`

This will create a container called `para-hotstuff`.

We use `jq` to extract the IP addresses of Docker containers, so make
sure to install that too.

## Usage

### Default command

We explain the various options our Python scripts provides. You will
run commands of the following form, followed by various options
explained below:

`python3 experiments.py --docker --pall`

### Options

In addition, you can use the following options to change some of the parameters:
- `--docker` to run the nodes within Docker containers
- `--pall` is to run all protocols, instead you can use `--p1` up to `--p3`
    - `--p1`: base protocol, i.e., HotStuff
    - `--p2`: chained base protocol, i.e., chained HotStuff
    - `--p3`: sets runPara to True (new protocol, i.e., Parallel HotStuff)
- `--repeats`: number of repeats per experiment (default: 0)
- `--netlat`: network latency in ms (default: 0)
- `--netvar`: variation of the network latency in ms (default: 0)
- `--views`: number of views to run per experiment (default: 0)
- `--faults`: the number of faults to test, separated by commas (e.g., 1,2,3,etc.) (default: "")
- `--payload`: size of payloads in Bytes (default: 0)
- `--maxBlocksInView`: maximum number of blocks in each view for Parallel HotStuff (default: "")
- `--numTrans`: number of transactions per client (default: 100)
- `--dir`: directory for stats (default: "stats")
- `--forceRecover`: force recovery threshold (default: 0)
- `--crash`: amount of crashes (default: 0)
- `--byzantine`: number of Byzantine nodes (default: -1)
- `--timeout`: timeout for leader change in seconds (default: 5)
- `--numclients`: number of clients for basic protocol (default: 1)
- `--numclientsch`: number of clients for chained protocol (default: 1)
- `--sleeptime`: sleep time between transactions for clients in ms (default: 0)
- `--numcltrans`: number of transactions per client (default: 0)    

### Examples

For example, if you run:

`python3 experiments.py --docker --pall`

then you will run the replicas within Docker containers (`--docker`),
test Basic HotStuff (`--p1`), Chained HotStuff (`--p2`) and Para HotStuff (`--p3`).

### Recommended experiments

There are multiple examples of experiments in the file experiments_script.py, including most of the ones that were run to get results in the thesis. 
You can simply define the ones you want to run there, e.g. either include them all or comment out which you don't want to run, and then run:

`python3 experiments_script.py`

### Cluster

It is also possible run the experiments on a cluster like DAS-5. In order to do so you first need to have Apptainer/Singularity installed. 
Make sure you have already built the docker image, and then you can run:

`apptainer build para-hotstuff.sif docker://para-hotstuff:latest`

You might need to execute that command locally, and then copy it to the remote cluster, if you don't have admin privileges. 

Then you can execute a command like the following to run on a cluster:

`python3 experiments_cluster.py --cluster --pall`


# Contact

Feel free to contact the author if you have questions:
[Andrea Einarsdóttir](andreaeinars@hotmail.com)
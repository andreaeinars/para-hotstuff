# Para-HotStuff

Base code and instructions from DAMYSUS: Streamlined BFT Consensus Leveraging Trusted Components


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
- `--pall` is to run all protocols, instead you can use `--p1` up to `--p2`
    - `--p1`: base protocol, i.e., HotStuff
    - `--p2`: chained base protocol, i.e., chained HotStuff

### Examples

For example, if you run:

`python3 experiments.py --docker --p1 --p2`

then you will run the replicas within Docker containers (`--docker`),
test Basic HotStuff (`--p1`) and Chained HotStuff (`--p2`).


# Acknowledgments

Jiangshan Yu was partially supported by the Australian Research Council
(ARC) under project DE210100019.


# Contact

Feel free to contact any of the authors if you have questions:
[Jeremie Decouchant](https://www.tudelft.nl/ewi/over-de-faculteit/afdelingen/software-technology/distributed-systems/people/jeremie-decouchant),
David Kozhaya,
[Vincent Rahli](https://www.cs.bham.ac.uk/~rahliv/),
and [Jiangshan Yu](https://research.monash.edu/en/persons/jiangshan-yu).

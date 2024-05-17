import multiprocessing
from datetime import datetime

## Parameters
faults       = [1,2,4,10] #[1,2,4,10] #[1,2,4,10,20,30,40] #[1,2,4,6,8,10,12,14,20,30] # list of numbers of faults
repeats      = 2 #10 #50 #5 #100 #2     # number of times to repeat each experiment
repeatsL2    = 1
#
numViews     = 10     # number of views in each run
cutOffBound  = 60     # stop experiment after some time
#
numClients   = 1     # number of clients
numNonChCls  = 1     # number of clients for the non-chained versions
numChCls     = 1     # number of clients for the chained versions
numClTrans   = 1     # number of transactions sent by each clients
sleepTime    = 0     # time clients sleep between 2 sends (in microseconds)
timeout      = 5     # timeout before changing changing leader (in seconds)
#
numTrans      = 400    # number of transactions
payloadSize   = 0 #256 #0 #256 #128      # total size of a transaction
useMultiCores = True
numMakeCores  = multiprocessing.cpu_count()  # number of cores to use to make
#
runBasic     = False #True
runChained   = False
runPara      = False
plotView     = True   # to plot the numbers of handling messages + network
plotHandle   = False  # to plot the numbers of just handling messages, without the network
plotCrypto   = False  # to plot the numbers of do crypto
debugPlot    = True #False  # to print debug info when plotting
showTitle    = True   # to print the title of the figure
plotThroughput = True
plotLatency  = True
showLegend1  = True
showLegend2  = False
plotBasic    = True
plotChained  = True
plotPara     = True
displayPlot  = True # to display a plot once it is generated
showYlabel   = True
displayApp   = "open"
logScale     = True
recompile = True # to recompile the code
deadNodes    = False # For some experiments we start with f nodes dead

# if deadNodes then we go with less views and give ourselves more time
if deadNodes:
    numViews = numViews // timeout
    cutOffBound = cutOffBound * 2

quantileSize = 20 # For some experiments we remove the outliers

# don't change, those are hard coded in the C++ code:
statsdir     = "stats"        # stats directory (don't change, hard coded in C++)
params       = "App/params.h" # (don't change, hard coded in C++)
config       = "App/config.h" # (don't change, hard coded in C++)
addresses    = "config"       # (don't change, hard coded in C++)
ipsOfNodes   = {}             # dictionnary mapping node ids to IPs

## Global variables
completeRuns  = 0     # number of runs that successfully completed
abortedRuns   = 0     # number of runs that got aborted
aborted       = []    # list of aborted runs
allLocalPorts = []    # list of all port numbers used in local experiments

dateTimeObj  = datetime.now()
timestampStr = dateTimeObj.strftime("%d-%b-%Y-%H:%M:%S.%f")
pointsFile   = statsdir + "/points-" + timestampStr
abortedFile  = statsdir + "/aborted-" + timestampStr
plotFile     = statsdir + "/plot-" + timestampStr + ".png"

# Names
basicHS   = "Basic HotStuff"
chainedHS = "Chained HotStuff"

# Markers
basicMRK   = "P"
chainedMRK = "d"

# Line styles
basicLS   = ":"
chainedLS = ":"

# Markers
basicCOL   = "black"
chainedCOL = "darkorange"

## Docker parameters
runDocker  = False      # to run the code within docker contrainers
docker     = "docker"
dockerBase = "para-hotstuff"  # name of the docker container
networkLat = 0          # network latency in ms
networkVar = 0          # variation of the network latency
dockerMem  = 0          # memory used by containers (0 means no constraints)
dockerCpu  = 0          # cpus used by containers (0 means no constraints)
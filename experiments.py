## Imports
from subprocess import Popen
import subprocess
from pathlib import Path
import matplotlib.pyplot as plt
import time
import math
import os
import glob
from datetime import datetime
import argparse
from enum import Enum
import multiprocessing
import re

## Parameters
faults       = [1] #[1,2,4,10] #[1,2,4,10,20,30,40] #[1,2,4,6,8,10,12,14,20,30] # list of numbers of faults

repeats      = 1 #10 #50 #5 #100 #2     # number of times to repeat each experiment
repeatsL2    = 1
#
numViews     = 30     # number of views in each run
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
runBase      = False #True
runChBase    = False #True
#
plotView     = True   # to plot the numbers of handling messages + network
plotHandle   = False  # to plot the numbers of just handling messages, without the network
plotCrypto   = False  # to plot the numbers of do crypto
debugPlot    = True #False  # to print debug info when plotting
showTitle    = True   # to print the title of the figure
plotThroughput = True
plotLatency    = True
showLegend1  = True
showLegend2  = False
plotBasic    = True
plotChained  = True
displayPlot  = True # to display a plot once it is generated
showYlabel   = True
displayApp   = "open"
logScale     = True

# to recompile the code
recompile = True

# For some experiments we start with f nodes dead
deadNodes    = False
# if deadNodes then we go with less views and give ourselves more time
if deadNodes:
    numViews = numViews // timeout
    cutOffBound = cutOffBound * 2

# For some experiments we remove the outliers
quantileSize = 20

# don't change, those are hard coded in the C++ code:
statsdir     = "stats"        # stats directory (don't change, hard coded in C++)
params       = "App/params.h" # (don't change, hard coded in C++)
config       = "App/config.h" # (don't change, hard coded in C++)
addresses    = "config"       # (don't change, hard coded in C++)
ipsOfNodes   = {}             # dictionnary mapping node ids to IPs

# to copy all files to AWS instances
copyAll = True

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
baseHS   = "Basic HotStuff"
baseChHS = "Chained HotStuff"

# Markers
baseMRK   = "P"
baseChMRK = "d"

# Line styles
baseLS   = ":"
baseChLS = ":"

# Markers
baseCOL   = "black"
baseChCOL = "darkorange"

## Docker parameters
runDocker  = False      # to run the code within docker contrainers
docker     = "docker"
dockerBase = "para-hotstuff"  # name of the docker container
networkLat = 0          # network latency in ms
networkVar = 0          # variation of the network latency
dockerMem  = 0          # memory used by containers (0 means no constraints)
dockerCpu  = 0          # cpus used by containers (0 means no constraints)


## Code
class Protocol(Enum):
    BASE      = "BASIC_BASELINE"           # basic baseline
    CHBASE    = "CHAINED_BASELINE"         # chained baseline

## generates a local config file
def genLocalConf(n,filename):
    open(filename, 'w').close()
    host = "127.0.0.1"

    global allLocalPorts

    print("ips:" , ipsOfNodes)

    f = open(filename,'a')
    for i in range(n):
        host  = ipsOfNodes.get(i,host)
        rport = 8760+i
        cport = 9760+i
        allLocalPorts.append(rport)
        allLocalPorts.append(cport)
        f.write("id:"+str(i)+" host:"+host+" port:"+str(rport)+" port:"+str(cport)+"\n")
    f.close()
# End of genLocalConf


def clearStatsDir():
    # Removing all (temporary) files in stats dir
    files0 = glob.glob(statsdir+"/vals*")
    files1 = glob.glob(statsdir+"/throughput-view*")
    files2 = glob.glob(statsdir+"/latency-view*")
    files3 = glob.glob(statsdir+"/handle*")
    files4 = glob.glob(statsdir+"/crypto*")
    files5 = glob.glob(statsdir+"/done*")
    files6 = glob.glob(statsdir+"/client-throughput-latency*")
    for f in files0 + files1 + files2 + files3 + files4 + files5 + files6:
        #print(f)
        os.remove(f)
# End of clearStatsDir


def mkParams(protocol,constFactor,numFaults,numTrans,payloadSize):
    f = open(params, 'w')
    f.write("#ifndef PARAMS_H\n")
    f.write("#define PARAMS_H\n")
    f.write("\n")
    f.write("#define " + protocol.value + "\n")
    f.write("#define MAX_NUM_NODES " + str((constFactor*numFaults)+1) + "\n")
    f.write("#define MAX_NUM_SIGNATURES " + str((constFactor*numFaults)+1-numFaults) + "\n")
    f.write("#define MAX_NUM_TRANSACTIONS " + str(numTrans) + "\n")
    f.write("#define PAYLOAD_SIZE " +str(payloadSize) + "\n")
    f.write("\n")
    f.write("#endif\n")
    f.close()
# End of mkParams


def mkApp(protocol,constFactor,numFaults,numTrans,payloadSize):
    ncores = 1
    if useMultiCores:
        ncores = numMakeCores
    print(">> making using",str(ncores),"core(s)")

    mkParams(protocol,constFactor,numFaults,numTrans,payloadSize)

    if runDocker:
        numReps = (constFactor * numFaults) + 1
        lr = list(map(lambda x: str(x), list(range(numReps))))           # replicas
        lc = list(map(lambda x: "c" + str(x), list(range(numClients))))  # clients
        for i in lr + lc:
            instance  = dockerBase + i
            instancex = instance + "x"
            instancey = instance
            # copying App
            adst  = instance + ":/app/App/"
            adstx = instancex + ":/app/App/"
            adsty = adst
            # if dockerCpu > 0 we're restricting the cpu, in which case we'll compile on the non-restricted instance and copy the files over
            if dockerCpu > 0 and dockerCpu < 1:
                instancey = instancex
                adsty = adstx
            subprocess.run([docker + " cp Makefile "  + instancey + ":/app/"], shell=True, check=True)
            subprocess.run([docker + " cp App/. "     + adsty], shell=True, check=True)
            subprocess.run([docker + " exec -t " + instancey + " bash -c \"make clean\""], shell=True, check=True)
            subprocess.run([docker + " exec -t " + instancey + " bash -c \"make -j " + str(ncores) + " server client\""], shell=True, check=True)
            if dockerCpu > 0 and dockerCpu < 1:
                print("copying files from " + instancex + " to " + instance)
                tmp = "docker_tmp"
                Path(tmp).mkdir(parents=True, exist_ok=True)
                subprocess.run([docker + " cp " + instancex + ":/app/." + " " + tmp + "/"], shell=True, check=True)
                subprocess.run([docker + " cp " + tmp + "/." + " " + instance + ":/app/"], shell=True, check=True)
        
    else:
        subprocess.call(["make","clean"])
        subprocess.call(["make","-j",str(ncores),"server","client"])
# End of mkApp


def execute(protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,instance):
    subsReps    = [] # list of replica subprocesses
    subsClients = [] # list of client subprocesses
    numReps = (constFactor * numFaults) + 1

    genLocalConf(numReps,addresses)

    print("initial number of nodes:", numReps)
    if deadNodes:
        numReps = numReps - numFaults
    print("number of nodes to actually run:", numReps)

    lr = list(map(lambda x: str(x), list(range(numReps))))           # replicas
    lc = list(map(lambda x: "c" + str(x), list(range(numClients))))  # clients
    lall = lr + lc

    # if running in docker mode, we copy the addresses to the containers
    if runDocker:
        for i in lall:
            dockerInstance = dockerBase + i
            dst = dockerInstance + ":/app/"
            subprocess.run([docker + " cp " + addresses + " " + dst], shell=True, check=True)

    server = "./server"
    client = "./client"

    newtimeout = int(math.ceil(timeout+math.log(numFaults,2)))
    # starting severs
    for i in range(numReps):
        # we give some time for the nodes to connect gradually
        if (i%10 == 5):
            time.sleep(2)
        cmd = " ".join([server, str(i), str(numFaults), str(constFactor), str(numViews), str(newtimeout)])
        if runDocker:
            dockerInstance = dockerBase + str(i)
            cmd = docker + " exec -t " + dockerInstance + " bash -c \"" + cmd + "\""
        p = Popen(cmd, shell=True)
        subsReps.append(("R",i,p))

    print("started", len(subsReps), "replicas")

    # starting client after a few seconds
    wait = 5 + int(math.ceil(math.log(numFaults,2)))

    time.sleep(wait)
    for cid in range(numClients):
        cmd = " ".join([client, str(cid), str(numFaults), str(constFactor), str(numClTrans), str(sleepTime), str(instance)])
        if runDocker:
            dockerInstance = dockerBase + "c" + str(cid)
            cmd = docker + " exec -t " + dockerInstance + " bash -c \"" + cmd + "\""
        c = Popen(cmd, shell=True)
        subsClients.append(("C",cid,c))

    print("started", len(subsClients), "clients")

    totalTime = 0

    remaining = subsReps.copy()
    # We wait here for all processes to complete
    # but we stop the execution if it takes too long (cutOffBound)
    while 0 < len(remaining) and totalTime < cutOffBound:
        print("remaining processes:", remaining)
        # We filter out the ones that are done. x is of the form (t,i,p)
        if runDocker:
            rem = remaining.copy()
            for (t,i,p) in rem:
                dockerInstance = dockerBase + str(i)
                cmd_check_dir = "if [ -d /app/stats ]; then find /app/stats -name 'done-*' | wc -l; else echo 0; fi"
                cmd = docker + " exec -t " + dockerInstance + " bash -c \"" + cmd_check_dir + "\""
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
                out = int(result)
                if 0 < int(out):
                    remaining.remove((t,i,p))
        else:
            remaining = list(filter(lambda x: 0 == len(glob.glob(statsdir+"/done-"+str(x[1])+"*")), remaining))
        time.sleep(1)
        totalTime += 1

    global completeRuns
    global abortedRuns
    global aborted

    if totalTime < cutOffBound:
        completeRuns += 1
        print("all", len(subsReps)+len(subsClients), "processes are done")
    else:
        abortedRuns += 1
        conf = (protocol,numFaults,instance)
        aborted.append(conf)
        f = open(abortedFile, 'a')
        f.write(str(conf)+"\n")
        f.close()
        print("------ reached cutoff bound ------")

    ## cleanup
    # kill python subprocesses
    for (t,i,p) in subsReps + subsClients:
        # we print the nodes that haven't finished yet
        if (p.poll() is None):
            print("still running:",(t,i,p.poll()))
            p.kill()

    ports = " ".join(list(map(lambda port: str(port) + "/tcp", allLocalPorts)))

    # kill processes
    if runDocker:
        # if running in docker mode, we kill the processes & copy+remove the stats file to this machine
        for i in lall:
            dockerInstance = dockerBase + i
            kcmd = "killall -q server client; fuser -k " + ports
            subprocess.run([docker + " exec -t " + dockerInstance + " bash -c \"" + kcmd + "\""], shell=True) #, check=True)
            src = dockerInstance + ":/app/" + statsdir + "/."
            dst = statsdir + "/"
            subprocess.run([docker + " cp " + src + " " + dst], shell=True, check=True)
            rcmd = "rm /app/" + statsdir + "/*"
            subprocess.run([docker + " exec -t " + dockerInstance + " bash -c \"" + rcmd + "\""], shell=True) #, check=True)
    else:
        subprocess.run(["killall -q server client; fuser -k " + ports], shell=True) #, check=True)
## End of execute


def printNodePoint(protocol,numFaults,tag,val):
    f = open(pointsFile, 'a')
    f.write("protocol="+protocol.value+" "+"faults="+str(numFaults)+" "+tag+"="+str(val)+"\n")
    f.close()
# End of printNodePoint


def printNodePointComment(protocol,numFaults,instance,repeats):
    f = open(pointsFile, 'a')
    f.write("# protocol="+protocol.value+" regions=local "+" payload="+str(payloadSize)+" faults="+str(numFaults)+" instance="+str(instance)+" repeats="+str(repeats)+"\n")
    f.close()
# End of printNodePointComment


def printNodePointParams():
    f = open(pointsFile, 'a')
    text = "##params"
    text += " cpus="+str(dockerCpu)
    text += " mem="+str(dockerMem)
    text += " lat="+str(networkLat)
    text += " payload="+str(payloadSize)
    text += " repeats1="+str(repeats)
    text += " repeats2="+str(repeatsL2)
    text += " views="+str(numViews)
    text += " regions=local"
    text += "\n"
    f.write(text)
    f.close()
# End of printNodePointParams


def computeStats(protocol,numFaults,instance,repeats):
    # Computing throughput and latency
    throughputViewVal=0.0
    throughputViewNum=0
    latencyViewVal=0.0
    latencyViewNum=0

    handleVal=0.0
    handleNum=0

    cryptoSignVal=0.0
    cryptoSignNum=0

    cryptoVerifVal=0.0
    cryptoVerifNum=0

    cryptoNumSignVal=0.0
    cryptoNumSignNum=0

    cryptoNumVerifVal=0.0
    cryptoNumVerifNum=0

    printNodePointComment(protocol,numFaults,instance,repeats)

    files = glob.glob(statsdir+"/*")
    for filename in files:
        if filename.startswith(statsdir+"/vals"):
            f = open(filename, "r")
            s = f.read()
            [thru,lat,hdl,signNum,signTime,verifNum,verifTime] = s.split(" ")

            valT = float(thru)
            throughputViewNum += 1
            throughputViewVal += valT
            printNodePoint(protocol,numFaults,"throughput-view",valT)

            valL = float(lat)
            latencyViewNum += 1
            latencyViewVal += valL
            printNodePoint(protocol,numFaults,"latency-view",valL)

            valH = float(hdl)
            handleNum += 1
            handleVal += valH
            printNodePoint(protocol,numFaults,"handle",valH)

            valST = float(signTime)
            cryptoSignNum += 1
            cryptoSignVal += valST
            printNodePoint(protocol,numFaults,"crypto-sign",valST)

            valVT = float(verifTime)
            cryptoVerifNum += 1
            cryptoVerifVal += valVT
            printNodePoint(protocol,numFaults,"crypto-verif",valVT)

            valSN = int(signNum)
            cryptoNumSignNum += 1
            cryptoNumSignVal += valSN
            printNodePoint(protocol,numFaults,"crypto-num-sign",valSN)

            valVN = int(verifNum)
            cryptoNumVerifNum += 1
            cryptoNumVerifVal += valVN
            printNodePoint(protocol,numFaults,"crypto-num-verif",valVN)

    throughputView = throughputViewVal/throughputViewNum if throughputViewNum > 0 else 0.0
    latencyView    = latencyViewVal/latencyViewNum       if latencyViewNum > 0    else 0.0
    handle         = handleVal/handleNum                 if handleNum > 0         else 0.0
    cryptoSign     = cryptoSignVal/cryptoSignNum         if cryptoSignNum > 0     else 0.0
    cryptoVerif    = cryptoVerifVal/cryptoVerifNum       if cryptoVerifNum > 0    else 0.0
    cryptoNumSign  = cryptoNumSignVal/cryptoNumSignNum   if cryptoNumSignNum > 0  else 0.0
    cryptoNumVerif = cryptoNumVerifVal/cryptoNumVerifNum if cryptoNumVerifNum > 0 else 0.0

    print("throughput-view:",  throughputView, "out of", throughputViewNum)
    print("latency-view:",     latencyView,    "out of", latencyViewNum)
    print("handle:",           handle,         "out of", handleNum)
    print("crypto-sign:",      cryptoSign,     "out of", cryptoSignNum)
    print("crypto-verif:",     cryptoVerif,    "out of", cryptoVerifNum)
    print("crypto-num-sign:",  cryptoNumSign,  "out of", cryptoNumSignNum)
    print("crypto-num-verif:", cryptoNumVerif, "out of", cryptoNumVerifNum)

    return (throughputView, latencyView, handle, cryptoSign, cryptoVerif, cryptoNumSign, cryptoNumVerif)
## End of computeStats


def startContainers(numReps,numClients):
    print("running in docker mode, starting" , numReps, "containers for the replicas and", numClients, "for the clients")

    global ipsOfNodes

    lr = list(map(lambda x: (True, str(x)), list(range(numReps))))            # replicas
    lc = list(map(lambda x: (False, "c" + str(x)), list(range(numClients))))  # clients
    lall = lr + lc

    # The 'x' containers are used in particular when we require less cpu so that we can compile in full-cpu
    # containers and copy over the code, from the x instance that does not have the restriction, which is
    # used to compile, to the non-x instance that has the restrictions
    for (isRep, i) in lall:
        instance  = dockerBase + i
        instancex = instance + "x"
        # We stop and remove the Doker instance if it is still exists
        subprocess.run([docker + " stop " + instance], shell=True) #, check=True)
        subprocess.run([docker + " stop " + instancex], shell=True) #, check=True)
        subprocess.run([docker + " rm " + instance], shell=True) #, check=True)
        subprocess.run([docker + " rm " + instancex], shell=True) #, check=True)
        # TODO: make sure to cover all the ports
        opt1  = "--expose=8000-9999"
        opt2  = "--network=\"bridge\""
        opt3  = "--cap-add=NET_ADMIN"
        opt4  = "--name " + instance
        opt4x = "--name " + instancex
        optm  = "--memory=" + str(dockerMem) + "m" if dockerMem > 0 else ""
        optc  = "--cpus=\"" + str(dockerCpu) + "\"" if dockerCpu > 0 else ""
        opts  = " ".join([opt1, opt2, opt3, opt4, optm, optc]) # with cpu/mem limitations
        optsx = " ".join([opt1, opt2, opt3, opt4x])            # without cpu/mem limitations
        # We start the Docker instance
        subprocess.run([docker + " run -td " + opts + " " + dockerBase], shell=True, check=True)
        if dockerCpu > 0 and dockerCpu < 1:
            subprocess.run([docker + " run -td " + optsx + " " + dockerBase], shell=True, check=True)
        # Set the network latency
        if 0 < networkLat:
            print("----changing network latency to " + str(networkLat) + "ms")
            latcmd = "tc qdisc add dev eth0 root netem delay " + str(networkLat) + "ms " + str(networkVar) + "ms distribution normal"
            #latcmd = "tc qdisc add dev eth0 root netem delay " + str(networkLat) + "ms"
            subprocess.run([docker + " exec -t " + instance + " bash -c \"" + latcmd + "\""], shell=True, check=True)
        # Extract the IP address of the container
        ipcmd = docker + " inspect " + instance + " | jq '.[].NetworkSettings.Networks.bridge.IPAddress'"
        srch = re.search('\"(.+?)\"', subprocess.run(ipcmd, shell=True, capture_output=True, text=True).stdout)
        if srch:
            out = srch.group(1)
            print("----container's address:" + out)
            if isRep:
                ipsOfNodes.update({int(i):out})
        else:
            print("----container's address: UNKNOWN")
## End of startContainers


def stopContainers(numReps,numClients):
    print("stopping and removing docker containers")

    lr = list(map(lambda x: (True, str(x)), list(range(numReps))))            # replicas
    lc = list(map(lambda x: (False, "c" + str(x)), list(range(numClients))))  # clients
    lall = lr + lc

    for (isRep, i) in lall:
        instance = dockerBase + i
        instancex = instance + "x"
        subprocess.run([docker + " stop " + instance], shell=True) #, check=True)
        subprocess.run([docker + " stop " + instancex], shell=True) #, check=True)
        subprocess.run([docker + " rm " + instance], shell=True) #, check=True)
        subprocess.run([docker + " rm " + instancex], shell=True) #, check=True)
## End of stopContainers

# if 'recompile' is true, the application will be recompiled (default=true)
def computeAvgStats(recompile,protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,numRepeats):
    print("<<<<<<<<<<<<<<<<<<<<",
          "protocol="+protocol.value,
          ";regions=local",
          ";payload="+str(payloadSize),
          "(factor="+str(constFactor)+")",
          "#faults="+str(numFaults),
          "[complete-runs="+str(completeRuns),"aborted-runs="+str(abortedRuns)+"]")
    print("aborted runs so far:", aborted)

    throughputViews=[]
    latencyViews=[]
    handles=[]
    cryptoSigns=[]
    cryptoVerifs=[]
    cryptoNumSigns=[]
    cryptoNumVerifs=[]

    numReps = (constFactor * numFaults) + 1

    if runDocker:
        startContainers(numReps,numClients)

    # building App with correct parameters
    if recompile:
        mkApp(protocol,constFactor,numFaults,numTrans,payloadSize)

    goodValues = 0

    # running 'numRepeats' time
    for i in range(numRepeats):
        print(">>>>>>>>>>>>>>>>>>>>",
              "protocol="+protocol.value,
              ";regions=local",
              ";payload="+str(payloadSize),
              "(factor="+str(constFactor)+")",
              "#faults="+str(numFaults),
              "repeat="+str(i),
              "[complete-runs="+str(completeRuns),"aborted-runs="+str(abortedRuns)+"]")
        print("aborted runs so far:", aborted)
        clearStatsDir()
        execute(protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,i)
        (throughputView,latencyView,handle,cryptoSign,cryptoVerif,cryptoNumSign,cryptoNumVerif) = computeStats(protocol,numFaults,i,numRepeats)
        if throughputView > 0 and latencyView > 0 and handle > 0 and cryptoSign > 0 and cryptoVerif > 0 and cryptoNumSign > 0 and cryptoNumVerif > 0:
            throughputViews.append(throughputView)
            latencyViews.append(latencyView)
            handles.append(handle)
            cryptoSigns.append(cryptoSign)
            cryptoVerifs.append(cryptoVerif)
            cryptoNumSigns.append(cryptoNumSign)
            cryptoNumVerifs.append(cryptoNumVerif)
            goodValues += 1

    if runDocker:
        stopContainers(numReps,numClients)

    throughputView = sum(throughputViews)/goodValues if goodValues > 0 else 0.0
    latencyView    = sum(latencyViews)/goodValues    if goodValues > 0 else 0.0
    handle         = sum(handles)/goodValues         if goodValues > 0 else 0.0
    cryptoSign     = sum(cryptoSigns)/goodValues     if goodValues > 0 else 0.0
    cryptoVerif    = sum(cryptoVerifs)/goodValues    if goodValues > 0 else 0.0
    cryptoNumSign  = sum(cryptoNumSigns)/goodValues  if goodValues > 0 else 0.0
    cryptoNumVerif = sum(cryptoNumVerifs)/goodValues if goodValues > 0 else 0.0

    print("avg throughput (view):",  throughputView)
    print("avg latency (view):",     latencyView)
    print("avg handle:",             handle)
    print("avg crypto (sign):",      cryptoSign)
    print("avg crypto (verif):",     cryptoVerif)
    print("avg crypto (sign-num):",  cryptoNumSign)
    print("avg crypto (verif-num):", cryptoNumVerif)

    return (throughputView, latencyView, handle, cryptoSign, cryptoVerif, cryptoNumSign, cryptoNumVerif)
# End of computeAvgStats


def dict2val(d,f):
    (v,n) = d.get(f)
    return sum(v)/n


def dict2lists(d,quantileSize,p):
    faults = []
    vals   = []
    nums   = []

    # We create the lists of points from the dictionaries
    # 'val' is a list of 'num' reals
    for f,(val,num) in d.items():
        faults.append(f)
        val  = sorted(val)           # we sort the values
        l    = len(val)              # this should be num, the number of values we have in val
        n    = int(l/(100/quantileSize)) if quantileSize > 0 else 0 # we'll remove n values from the top and bottom
        newval = val[n:l-n]           # we're removing them
        m    = len(newval)           # we're only keeping m values out of the l
        s    = sum(newval)           # we're summing up the values
        v    = s/m if m > 0 else 0.0 # and computing the average
        if p:
            print(l,quantileSize,n,v,m,"---------\n", val, "\n", newval,"\n")
        vals.append(v)
        nums.append(m)

    return (faults,vals,nums)
# End of dict2lists

# 'bo' should be False for throughput (increase) and True for latency (decrease)
def getPercentage(bo,nameBase,faultsBase,valsBase,nameNew,faultsNew,valsNew):
    newTot = 0.0
    newMin = 0.0
    newMax = 0.0
    newLst = []

    if faultsBase == faultsNew:
        for (n,baseVal,newVal) in zip(faultsBase,valsBase,valsNew):
            new = (baseVal - newVal) / baseVal * 100 if bo else (newVal - baseVal) / baseVal * 100
            newTot += new

            if new > newMax: newMax = new
            if (new < newMin or newMin == 0.0): newMin = new
            newLst.append((n,new))

    newAvg = newTot / len(faultsBase) if len(faultsBase) > 0 else 0

    print(nameNew + "/" + nameBase + "(#faults/value): " + str(newLst))
    print(nameNew + "/" + nameBase + "(avg/min/ax): " + "avg=" + str(newAvg) + ";min=" + str(newMin) + ";max=" + str(newMax))
# End of getPercentage


# From: https://stackoverflow.com/questions/7965743/how-can-i-set-the-aspect-ratio-in-matplotlib
def adjustFigAspect(fig,aspect=1):
    '''
    Adjust the subplot parameters so that the figure has the correct
    aspect ratio.
    '''
    xsize,ysize = fig.get_size_inches()
    minsize = min(xsize,ysize)
    xlim = .4*minsize/xsize
    ylim = .4*minsize/ysize
    if aspect < 1:
        xlim *= aspect
    else:
        ylim /= aspect
    fig.subplots_adjust(left=.5-xlim,
                        right=.5+xlim,
                        bottom=.5-ylim,
                        top=.5+ylim)
# End of adjustFigAspect


def createPlot(pFile):
    # throughput-view
    dictTVBase   = {}
    dictTVChBase = {}

    # latency-view
    dictLVBase   = {}
    dictLVChBase = {}
 
    # handle
    dictHBase   = {}
    dictHChBase = {}

    # crypto-sign
    dictCSBase   = {}
    dictCSChBase = {}

    # crypto-verif
    dictCVBase   = {}
    dictCVChBase = {}

    global dockerCpu, dockerMem, networkLat, payloadSize, repeats, repeatsL2, numViews

    # We accumulate all the points in dictionaries
    print("reading points from:", pFile)
    f = open(pFile,'r')
    for line in f.readlines():
        if line.startswith("##params"):
            [hdr,cpu,mem,lat,payload,rep1,rep2,views,regs] = line.split(" ")
            [cpuTag,cpuVal] = cpu.split("=")
            dockerCpu = float(cpuVal)
            [memTag,memVal] = mem.split("=")
            dockerMem = int(memVal)
            [latTag,latVal] = lat.split("=")
            networkLat = int(latVal)
            [payloadTag,payloadVal] = payload.split("=")
            payloadSize = int(payloadVal)
            [rep1Tag,rep1Val] = rep1.split("=")
            repeats = int(rep1Val)
            [rep2Tag,rep2Val] = rep2.split("=")
            repeatsL2 = int(rep2Val)
            [viewsTag,viewsVal] = views.split("=")
            numViews = int(viewsVal)
            [regsTag,regsVal] = regs.split("=")
            

        if line.startswith("protocol"):
            [prot,faults,point]   = line.split(" ")
            [protTag,protVal]     = prot.split("=")
            [faultsTag,faultsVal] = faults.split("=")
            [pointTag,pointVal]   = point.split("=")
            numFaults=int(faultsVal)
            if float(pointVal) < float('inf'):
                # Throughputs-view
                if pointTag == "throughput-view" and protVal == "BASIC_BASELINE":
                    (val,num) = dictTVBase.get(numFaults,([],0))
                    val.append(float(pointVal))
                    dictTVBase.update({numFaults:(val,num+1)})
                if pointTag == "throughput-view" and protVal == "CHAINED_BASELINE":
                    (val,num) = dictTVChBase.get(numFaults,([],0))
                    val.append(float(pointVal))
                    dictTVChBase.update({numFaults:(val,num+1)})
    
                # Latencies-view
                if pointTag == "latency-view" and protVal == "BASIC_BASELINE":
                    (val,num) = dictLVBase.get(numFaults,([],0))
                    val.append(float(pointVal))
                    dictLVBase.update({numFaults:(val,num+1)})
                if pointTag == "latency-view" and protVal == "CHAINED_BASELINE":
                    (val,num) = dictLVChBase.get(numFaults,([],0))
                    val.append(float(pointVal))
                    dictLVChBase.update({numFaults:(val,num+1)})
              
                # handle
                if (pointTag == "handle" or pointTag == "latency-handle") and protVal == "BASIC_BASELINE":
                    (val,num) = dictHBase.get(numFaults,([],0))
                    val.append(float(pointVal) / numViews)
                    dictHBase.update({numFaults:(val,num+1)})
                if (pointTag == "handle" or pointTag == "latency-handle") and protVal == "CHAINED_BASELINE":
                    (val,num) = dictHChBase.get(numFaults,([],0))
                    val.append(float(pointVal) / numViews)
                    dictHChBase.update({numFaults:(val,num+1)})
               
                # crypto-sign
                if pointTag == "crypto-sign" and protVal == "BASIC_BASELINE":
                    (val,num) = dictCSBase.get(numFaults,([],0))
                    val.append(float(pointVal) / numViews)
                    dictCSBase.update({numFaults:(val,num+1)})
                if pointTag == "crypto-sign" and protVal == "CHAINED_BASELINE":
                    (val,num) = dictCSChBase.get(numFaults,([],0))
                    val.append(float(pointVal) / numViews)
                    dictCSChBase.update({numFaults:(val,num+1)})
                
                # crypto-verif
                if pointTag == "crypto-verif" and protVal == "BASIC_BASELINE":
                    (val,num) = dictCVBase.get(numFaults,([],0))
                    val.append(float(pointVal) / numViews)
                    dictCVBase.update({numFaults:(val,num+1)})
                if pointTag == "crypto-verif" and protVal == "CHAINED_BASELINE":
                    (val,num) = dictCVChBase.get(numFaults,([],0))
                    val.append(float(pointVal) / numViews)
                    dictCVChBase.update({numFaults:(val,num+1)})
            
    f.close()

    quantileSize = 20
    quantileSize1 = 20
    quantileSize2 = 20

    # We convert the dictionaries to lists
    # throughput-view
    (faultsTVBase,   valsTVBase,   numsTVBase)   = dict2lists(dictTVBase,quantileSize,False)
    (faultsTVChBase, valsTVChBase, numsTVChBase) = dict2lists(dictTVChBase,quantileSize,False)

    # latency-view
    (faultsLVBase,   valsLVBase,   numsLVBase)   = dict2lists(dictLVBase,quantileSize,False)
    (faultsLVChBase, valsLVChBase, numsLVChBase) = dict2lists(dictLVChBase,quantileSize,False)

    # handle
    (faultsHBase,   valsHBase,   numsHBase)   = dict2lists(dictHBase,quantileSize1,False)
    (faultsHChBase, valsHChBase, numsHChBase) = dict2lists(dictHChBase,quantileSize1,False)

    # crypto-sign
    (faultsCSBase,   valsCSBase,   numsCSBase)   = dict2lists(dictCSBase,quantileSize2,False)
    (faultsCSChBase, valsCSChBase, numsCSChBase) = dict2lists(dictCSChBase,quantileSize2,False)

    # crypto-verif
    (faultsCVBase,   valsCVBase,   numsCVBase)   = dict2lists(dictCVBase,quantileSize2,False)
    (faultsCVChBase, valsCVChBase, numsCVChBase) = dict2lists(dictCVChBase,quantileSize2,False)
  

    print("faults/throughputs(val+num)/latencies(val+num)/cypto-verif(val+num)/cypto-sign(val+num) for (baseline/cheap/quick/combined/free/onep/chained-baseline/chained-combined)")
    print((faultsTVBase,   (valsTVBase,   numsTVBase),   (valsLVBase,   numsLVBase),   (valsCVBase,   numsCVBase),   (valsCSBase,   numsCSBase)))
    print((faultsTVChBase, (valsTVChBase, numsTVChBase), (valsLVChBase, numsLVChBase), (valsCVChBase, numsCVChBase), (valsCSChBase, numsCSChBase)))

    print("Throughput gain:")
    getPercentage(False,baseHS,faultsTVBase,valsTVBase,baseChHS,faultsTVChBase,valsTVChBase)

    print("Latency gain (basic versions):")
    getPercentage(True,baseHS,faultsLVBase,valsLVBase,baseChHS,faultsLVChBase,valsLVChBase)

    print("Handle gain (basic versions):")
    getPercentage(True,baseHS,faultsHBase,valsHBase,baseChHS,faultsHChBase,valsHChBase)

    LW = 1 # linewidth
    MS = 5 # markersize
    XYT = (0,5)

    global plotThroughput
    global plotLatency

    if (plotHandle or plotCrypto) and not plotView:
        plotThroughput = False
        plotLatency    = True

    numPlots=2
    if (plotThroughput and not plotLatency) or (not plotThroughput and plotLatency):
        numPlots=1

    ## Plotting
    print("plotting",numPlots,"plot(s)")
    fig, axs = plt.subplots(numPlots,1)
    if numPlots == 1:
        x = axs
        axs = [x]
    #,figsize=(4, 10)
    if showTitle:
        if debugPlot:
            info = "file="+pFile
            info += "; cpus="+str(dockerCpu)
            info += "; mem="+str(dockerMem)
            info += "; lat="+str(networkLat)
            info += "; payload="+str(payloadSize)
            info += "; repeats1="+str(repeats)
            info += "; repeats2="+str(repeatsL2)
            info += "; #views="+str(numViews)
            info += "; regions=local"
            if plotHandle and not plotView:
                fig.suptitle("Handling time\n("+info+")")
            else:
                fig.suptitle("Throughputs (top) & Latencies (bottom)\n("+info+")")
        else:
            if plotHandle and not plotView:
                fig.suptitle("Handling time")
            else:
                fig.suptitle("Throughputs (top) & Latencies (bottom)")

    adjustFigAspect(fig,aspect=0.9)
    if numPlots == 2:
        fig.set_figheight(6)
    else: # == 1
        fig.set_figheight(3)

    if plotThroughput:
        if showYlabel:
            axs[0].set(ylabel="throughput (Kops/s)")
        if logScale:
            axs[0].set_yscale('log')
        # plotting the points
        if plotView:
            if plotBasic:
                if len(faultsTVBase) > 0:
                    axs[0].plot(faultsTVBase,   valsTVBase,   color=baseCOL,   linewidth=LW, marker=baseMRK,   markersize=MS, linestyle=baseLS,   label=baseHS)
            
            if plotChained:
                if len(faultsTVChBase) > 0:
                    axs[0].plot(faultsTVChBase, valsTVChBase, color=baseChCOL, linewidth=LW, marker=baseChMRK, markersize=MS, linestyle=baseChLS, label=baseChHS)
        
            if debugPlot:
                if plotBasic:
                    for x,y,z in zip(faultsTVBase, valsTVBase, numsTVBase):
                        axs[0].annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
               
                if plotChained:
                    for x,y,z in zip(faultsTVChBase, valsTVChBase, numsTVChBase):
                        axs[0].annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')

        # legend
        if showLegend1:
            axs[0].legend(ncol=2,prop={'size': 9})

    if plotLatency:
        ax=axs[0]
        if plotThroughput:
            ax=axs[1]
        # naming the x/y axis
        if showYlabel:
            if plotHandle and not plotView:
                ax.set(xlabel="#faults", ylabel="handling time (ms)")
            else:
                ax.set(xlabel="#faults", ylabel="latency (ms)")
        else:
            ax.set(xlabel="#faults")
        if logScale:
            ax.set_yscale('log')
        # plotting the points
        if plotView:
            if plotBasic:
                if len(faultsLVBase) > 0:
                    ax.plot(faultsLVBase,   valsLVBase,   color=baseCOL,   linewidth=LW, marker=baseMRK,   markersize=MS, linestyle=baseLS,   label=baseHS)
            if plotChained:
                if len(faultsLVChBase) > 0:
                    ax.plot(faultsLVChBase, valsLVChBase, color=baseChCOL, linewidth=LW, marker=baseChMRK, markersize=MS, linestyle=baseChLS, label=baseChHS)
            if debugPlot:
                if plotBasic:
                    for x,y,z in zip(faultsLVBase, valsLVBase, numsLVBase):
                        ax.annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
                if plotChained:
                    for x,y,z in zip(faultsLVChBase, valsLVChBase, numsLVChBase):
                        ax.annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
        if plotHandle:
            if plotBasic:
                if len(faultsHBase) > 0:
                    ax.plot(faultsHBase,   valsHBase,   color=baseCOL,   linewidth=LW, marker="+", markersize=MS, linestyle=baseLS,   label=baseHS+"")
            if plotChained:
                if len(faultsHChBase) > 0:
                    ax.plot(faultsHChBase, valsHChBase, color=baseChCOL, linewidth=LW, marker="+", markersize=MS, linestyle=baseChLS, label=baseChHS+"")
            if debugPlot:
                if plotBasic:
                    for x,y,z in zip(faultsHBase, valsHBase, numsHBase):
                        ax.annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
                if plotChained:
                    for x,y,z in zip(faultsHChBase, valsHChBase, numsHChBase):
                        ax.annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
        if plotCrypto: # Sign
            if plotBasic:
                if len(faultsCSBase) > 0:
                    axs[0].plot(faultsCSBase,   valsCSBase,   color=baseCOL,   linewidth=LW, marker="1", markersize=MS, linestyle=baseLS,   label=baseHS+" (crypto-sign)")
            if plotChained:
                if len(faultsCSChBase) > 0:
                    axs[0].plot(faultsCSChBase, valsCSChBase, color=baseChCOL, linewidth=LW, marker="1", markersize=MS, linestyle=baseChLS, label=baseChHS+" (crypto-sign)")
            if debugPlot:
                if plotBasic:
                    for x,y,z in zip(faultsCSBase, valsCSBase, numsCSBase):
                        axs[0].annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
                if plotChained:
                    for x,y,z in zip(faultsCSChBase, valsCSChBase, numsCSChBase):
                        axs[0].annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
        if plotCrypto: # Verif
            if plotBasic:
                if len(faultsCVBase) > 0:
                    axs[0].plot(faultsCVBase,   valsCVBase,   color=baseCOL,   linewidth=LW, marker="2", markersize=MS, linestyle=baseLS,   label=baseHS+" (crypto-verif)")
            if plotChained:
                if len(faultsCVChBase) > 0:
                    axs[0].plot(faultsCVChBase, valsCVChBase, color=baseChCOL, linewidth=LW, marker="2", markersize=MS, linestyle=baseChLS, label=baseChHS+" (crypto-verif)")
            if debugPlot:
                if plotBasic:
                    for x,y,z in zip(faultsCVBase, valsCVBase, numsCVBase):
                        axs[0].annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
                if plotChained:
                    for x,y,z in zip(faultsCVChBase, valsCVChBase, numsCVChBase):
                        axs[0].annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
        # legend
        if showLegend2 or (showLegend1 and not plotThroughput):
            ax.legend(prop={'size': 9})

    fig.savefig(plotFile, bbox_inches='tight', pad_inches=0.05)
    print("points are in", pFile)
    print("plot is in", plotFile)
    if displayPlot:
        try:
            subprocess.call([displayApp, plotFile])
        except:
            print("couldn't display the plot using '" + displayApp + "'. Consider changing the 'displayApp' variable.")
    return (dictTVBase, dictTVChBase, dictLVBase, dictLVChBase)
# End of createPlot


def runExperiments():
    # Creating stats directory

    Path(statsdir).mkdir(parents=True, exist_ok=True)

    printNodePointParams()

    for numFaults in faults:
        # ------
        # HotStuff-like baseline
        if runBase:
            computeAvgStats(recompile,protocol=Protocol.BASE,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults,numRepeats=repeats)
        else:
            (0.0,0.0,0.0,0.0)
        
         # Chained HotStuff-like baseline
        if runChBase:
            computeAvgStats(recompile,protocol=Protocol.CHBASE,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults,numRepeats=repeats)
        else:
            (0.0,0.0,0.0,0.0)
        # ------

    print("num complete runs=", completeRuns)
    print("num aborted runs=", abortedRuns)
    print("aborted runs:", aborted)

    createPlot(pointsFile)
# End of runExperiments


parser = argparse.ArgumentParser(description='X-HotStuff evaluation')

parser.add_argument("--docker",     action="store_true",   help="runs nodes locally in Docker containers")
parser.add_argument("--p1",         action="store_true",   help="sets runBase to True (base protocol, i.e., HotStuff)")
parser.add_argument("--p2",         action="store_true",   help="sets runChBase to True (chained base protocol, i.e., chained HotStuff")
parser.add_argument("--pall",       action="store_true",   help="sets all runXXX to True, i.e., all protocols will be executed")
args = parser.parse_args()


if args.docker:
    runDocker = True
    print("SUCCESSFULLY PARSED ARGUMENT - running nodes in Docker containers")

if args.p1:
    runBase = True
    print("SUCCESSFULLY PARSED ARGUMENT - testing base protocol")

if args.p2:
    runChBase = True
    print("SUCCESSFULLY PARSED ARGUMENT - testing chained base protocol")


if args.pall:
    runBase   = True
    runChBase = True
    print("SUCCESSFULLY PARSED ARGUMENT - testing all protocols")


if __name__ == "__main__":
    print("Throughput and Latency")
    runExperiments()
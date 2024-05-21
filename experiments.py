## Imports
from subprocess import Popen
import subprocess
from pathlib import Path
import matplotlib.pyplot as plt
import time
import math
import os
import glob
import argparse
from enum import Enum
import re

from exp_params import *

## Code
class Protocol(Enum):
    BASIC      = "BASIC_BASELINE"           # basic baseline
    CHAINED    = "CHAINED_BASELINE"         # chained baseline
    PARA       = "PARALLEL_HOTSTUFF"        # parallel hotstuff

def genLocalConf(n,filename): ## generates a local config file
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
        os.remove(f)

def mkParams(protocol,constFactor,numFaults,numTrans,payloadSize,maxBlocksInView=0):
    f = open(params, 'w')
    f.write("#ifndef PARAMS_H\n")
    f.write("#define PARAMS_H\n")
    f.write("\n")
    f.write("#define " + protocol.value + "\n")
    f.write("#define MAX_NUM_NODES " + str((constFactor*numFaults)+1) + "\n")
    f.write("#define MAX_NUM_SIGNATURES " + str((constFactor*numFaults)+1-numFaults) + "\n")
    f.write("#define MAX_NUM_TRANSACTIONS " + str(numTrans) + "\n")
    f.write("#define PAYLOAD_SIZE " +str(payloadSize) + "\n")
    f.write("#define MAX_BLOCKS_IN_VIEW " + str(maxBlocksInView) + "\n")
    f.write("\n")
    f.write("#endif\n")
    f.close()

def mkApp(protocol,constFactor,numFaults,numTrans,payloadSize,maxBlocksInView=0):
    ncores = 1
    if useMultiCores:
        ncores = numMakeCores
    print(">> making using",str(ncores),"core(s)")

    mkParams(protocol,constFactor,numFaults,numTrans,payloadSize,maxBlocksInView)

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

def execute(protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,instance, maxBlocksInView=0):
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
        cmd = f"{server} {i} {numFaults} {constFactor} {numViews} {newtimeout} {maxBlocksInView}"
        #cmd = " ".join([server, str(i), str(numFaults), str(constFactor), str(numViews), str(newtimeout)])
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
        cmd = f"{client} {cid} {numFaults} {constFactor} {numClTrans} {sleepTime} {instance}"
        #cmd = " ".join([client, str(cid), str(numFaults), str(constFactor), str(numClTrans), str(sleepTime), str(instance)])
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

def printNodePoint(protocol,numFaults,tag,val, maxBlocksInView=0):
    protocol_name = f"{protocol.value}-{maxBlocksInView}BLOCKS" if 'PARALLEL_HOTSTUFF' in protocol.value and maxBlocksInView > 0 else protocol.value
    f = open(pointsFile, 'a')
    f.write("protocol="+protocol_name+" "+"faults="+str(numFaults)+" "+tag+"="+str(val)+"\n")
    f.close()

def printNodePointComment(protocol,numFaults,instance,repeats, maxBlocksInView=0):
    protocol_name = f"{protocol.value}-{maxBlocksInView}BLOCKS" if 'PARALLEL_HOTSTUFF' in protocol.value and maxBlocksInView > 0 else protocol.value
    f = open(pointsFile, 'a')
    f.write("# protocol="+protocol_name+" regions=local "+" payload="+str(payloadSize)+" faults="+str(numFaults)+" instance="+str(instance)+" repeats="+str(repeats)+"\n")
    f.close()

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

def computeStats(protocol, numFaults, instance, repeats, maxBlocksInView=0):
    # Dictionary to hold metric names and their corresponding accumulators and counters
    metrics = {
        "throughput-view": {"val": 0.0, "num": 0},
        "latency-view": {"val": 0.0, "num": 0},
        "handle": {"val": 0.0, "num": 0},
        "crypto-sign": {"val": 0.0, "num": 0},
        "crypto-verif": {"val": 0.0, "num": 0},
        "crypto-num-sign": {"val": 0.0, "num": 0},
        "crypto-num-verif": {"val": 0.0, "num": 0},
    }

    printNodePointComment(protocol, numFaults, instance, repeats, maxBlocksInView)

    files = glob.glob(statsdir + "/vals*")
    for filename in files:
        with open(filename, "r") as f:
            data = f.read().split()
            metric_values = {
                "throughput-view": float(data[0]),
                "latency-view": float(data[1]),
                "handle": float(data[2]),
                "crypto-sign": float(data[4]),
                "crypto-verif": float(data[6]),
                "crypto-num-sign": int(data[3]),
                "crypto-num-verif": int(data[5]),
            }
            for metric, value in metric_values.items():
                metrics[metric]["val"] += value
                metrics[metric]["num"] += 1
                printNodePoint(protocol, numFaults, metric, value, maxBlocksInView)

    # Calculate averages
    results = {metric: metrics[metric]["val"] / metrics[metric]["num"] if metrics[metric]["num"] > 0 else 0.0 for metric in metrics}

    # Print results
    for metric, result in results.items():
        print(f"{metric}: {result} out of {metrics[metric]['num']}")

    return (results["throughput-view"], results["latency-view"], results["handle"],
            results["crypto-sign"], results["crypto-verif"],
            results["crypto-num-sign"], results["crypto-num-verif"])

def stop_and_remove_container(instance):
    subprocess.run([docker + " stop " + instance], shell=True)
    subprocess.run([docker + " rm " + instance], shell=True) 

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
        stop_and_remove_container(instance)  # We stop and remove the Docker instance if it is still exists
        stop_and_remove_container(instancex)
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

def stopContainers(numReps,numClients):
    print("stopping and removing docker containers")

    lr = list(map(lambda x: (True, str(x)), list(range(numReps))))            # replicas
    lc = list(map(lambda x: (False, "c" + str(x)), list(range(numClients))))  # clients
    lall = lr + lc

    for (isRep, i) in lall:
        instance = dockerBase + i
        instancex = instance + "x"
        stop_and_remove_container(instance)
        stop_and_remove_container(instancex)

def computeAvgStats(recompile, protocol, constFactor, numClTrans, sleepTime, numViews, cutOffBound, numFaults, numRepeats, maxBlocksInView=0):
    def log_status(i = None):
        print("<<<<<<<<<<<<<<<<<<<<", end="")
        print("protocol=", protocol.value)
        print("regions=", "local")
        print("payload=", payloadSize)
        print("factor=", constFactor)
        print("#faults=", numFaults)
        if i:
            print("repeat=", i)
        print("[complete-runs=", completeRuns)
        print(f"aborted-runs={abortedRuns}]")
        print("aborted runs so far:", aborted)

    metrics = {
        "throughputViews": [],
        "latencyViews": [],
        "handles": [],
        "cryptoSigns": [],
        "cryptoVerifs": [],
        "cryptoNumSigns": [],
        "cryptoNumVerifs": [],
    }

    numReps = (constFactor * numFaults) + 1

    if runDocker:
        startContainers(numReps, numClients)

    if recompile:
        mkApp(protocol, constFactor, numFaults, numTrans, payloadSize, maxBlocksInView)

    goodValues = 0

    for i in range(numRepeats):
        log_status(i)

        clearStatsDir()
        execute(protocol, constFactor, numClTrans, sleepTime, numViews, cutOffBound, numFaults, i, maxBlocksInView)
        results = computeStats(protocol, numFaults, i, numRepeats, maxBlocksInView)

        if all(result > 0 for result in results):
            for key, result in zip(metrics.keys(), results):
                metrics[key].append(result)
            goodValues += 1

    if runDocker:
        stopContainers(numReps, numClients)

    averages = {key: sum(values)/goodValues if goodValues > 0 else 0.0 for key, values in metrics.items()}

    for key, avg in averages.items():
        print(f"avg {key.replace('Views', '')}: {avg}")

    return tuple(averages.values())

def getPercentage(bo,nameBase,faultsBase,valsBase,nameNew,faultsNew,valsNew):
    # 'bo' should be False for throughput (increase) and True for latency (decrease)
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

def createPlot(pFile):
    def init_dicts():  # Dictionary initialization
        #protocols = ["BASIC_BASELINE", "CHAINED_BASELINE", "PARALLEL_HOTSTUFF"]
        protocols = ["BASIC_BASELINE", "CHAINED_BASELINE"] + \
                    [f"PARALLEL_HOTSTUFF-{blocks}BLOCKS" for blocks in maxBlocksInView]
        metrics = ["throughput-view", "latency-view", "handle", "crypto-sign", "crypto-verif"]
        return {protocol: {metric: {} for metric in metrics} for protocol in protocols}

    data_dict = init_dicts()

    global dockerCpu, dockerMem, networkLat, payloadSize, repeats, repeatsL2, numViews

    # Read parameters
    def parse_params(line):
        parts = line.split(" ")
        params = {part.split("=")[0]: part.split("=")[1].strip() for part in parts[1:]}
        global dockerCpu, dockerMem, networkLat, payloadSize, repeats, repeatsL2, numViews
        dockerCpu = float(params["cpus"])
        dockerMem = int(params["mem"])
        networkLat = int(params["lat"])
        payloadSize = int(params["payload"])
        repeats = int(params["repeats1"])
        repeatsL2 = int(params["repeats2"])
        numViews = int(params["views"])

    def adjustFigAspect(fig, aspect=1):
        xsize, ysize = fig.get_size_inches()
        minsize = min(xsize, ysize)
        fig.set_size_inches(minsize * aspect, minsize * aspect, forward=True)

    # Update dictionaries with data points
    def update_dict(protocol, metric, numFaults, pointVal):
        if metric not in data_dict[protocol]:
            return
        val, num = data_dict[protocol][metric].get(numFaults, ([], 0))
        # Adjust scaling based on the original logic
        val.append(float(pointVal) if metric in ["throughput-view", "latency-view"] else float(pointVal) / numViews)

        data_dict[protocol][metric][numFaults] = (val, num + 1)

    # Reading points from the file
    print("reading points from:", pFile)
    with open(pFile, 'r') as f:
        for line in f.readlines():
            if line.startswith("##params"):
                parse_params(line)
            if line.startswith("protocol"):
                parts = line.split(" ")
                protocol = parts[0].split("=")[1]
                numFaults = int(parts[1].split("=")[1])
                pointTag = parts[2].split("=")[0]
                pointVal = float(parts[2].split("=")[1])
                #protocol = f"{protocol_base}-{numBlocks}BLOCKS" if numBlocks > 0 else protocol_base
                if pointVal < float('inf'):
                    update_dict(protocol, pointTag, numFaults, pointVal)
                

    # Function to convert dictionaries to lists
    def dict2lists(d, quantileSize, sort=True):
        faults, vals, nums = [], [], []
        for key, (val, num) in d.items():
            faults.append(key)
            val = sorted(val)
            l = len(val)
            n = int(l / (100 / quantileSize)) if quantileSize > 0 else 0
            newval = val[n:l-n]
            m = len(newval)
            s = sum(newval)
            v = s / m if m > 0 else 0.0
            vals.append(v)
            nums.append(m)
        if sort:
            sorted_tuples = sorted(zip(faults, vals, nums))
            #faults, vals, nums = zip(*sorted_tuples)
            faults, vals, nums = zip(*sorted_tuples) if sorted_tuples else (faults, vals, nums)
        return faults, vals, nums
    
    # Extracting data for plotting
    def extract_plot_data(metric):
        plot_data = {}
        for protocol in data_dict:
            faults, vals, nums = dict2lists(data_dict[protocol][metric], 20, True)
            plot_data[protocol] = (faults, vals, nums)
        return plot_data

    # Plotting data helper function
    def plot_data(ax, metric, ylabel, logScale, showYlabel):
        plot_data = extract_plot_data(metric)
        for protocol, data in plot_data.items():
            if data[0]:  # Only plot if there is data
                ax.plot(data[0], data[1], linewidth=LW, marker='o', markersize=MS, linestyle='-', label=protocol)
        if showYlabel:
            ax.set(ylabel=ylabel)
        if logScale:
            ax.set_yscale('log')
        ax.legend(fontsize='xx-small')

    # Plotting setup
    LW = 1  # linewidth
    MS = 5  # markersize
    XYT = (0, 5)
    numPlots = 2 if plotThroughput and plotLatency else 1
    #fig, axs = plt.subplots(numPlots, 1)
    fig, axs = plt.subplots(numPlots, 1, figsize=(10, 6))
    axs = [axs] if numPlots == 1 else axs

    if showTitle:
        title_info = "Throughputs (top) & Latencies (bottom)" if not plotHandle else "Handling time"
        if debugPlot:
            title_info += f"\n(file={pFile}; cpus={dockerCpu}; mem={dockerMem}; lat={networkLat}; payload={payloadSize}; repeats1={repeats}; repeats2={repeatsL2}; #views={numViews}; regions=local)"
        fig.suptitle(title_info)

    adjustFigAspect(fig, aspect=0.9)
    fig.set_figheight(6 if numPlots == 2 else 3)

    if plotThroughput:
        plot_data(axs[0], "throughput-view", "throughput (Kops/s)", logScale, showYlabel)

    if plotLatency:
        ax = axs[0] if numPlots == 1 else axs[1]
        ylabel = "latency (ms)" if not plotHandle else "handling time (ms)"
        plot_data(ax, "latency-view", ylabel, logScale, showYlabel)
        if plotHandle:
            plot_data(ax, "handle", "handling time (ms)", logScale, showYlabel)
        if plotCrypto:
            plot_data(ax, "crypto-sign", "crypto-sign (ms)", logScale, showYlabel)
            plot_data(ax, "crypto-verif", "crypto-verif (ms)", logScale, showYlabel)

    #fig.tight_layout(pad=3.0)  # Adjust layout to prevent overlap
    fig.savefig(plotFile, bbox_inches='tight', pad_inches=0.5)

    #fig.savefig(plotFile, bbox_inches='tight', pad_inches=0.05)
    print("points are in", pFile)
    print("plot is in", plotFile)
    if displayPlot:
        try:
            subprocess.call([displayApp, plotFile])
        except:
            print(f"couldn't display the plot using '{displayApp}'. Consider changing the 'displayApp' variable.")

    return {protocol: data_dict[protocol]["throughput-view"] for protocol in data_dict}


    # return data_dict["BASIC_BASELINE"]["throughput-view"], data_dict["CHAINED_BASELINE"]["throughput-view"], \
    #        data_dict["BASIC_BASELINE"]["latency-view"], data_dict["CHAINED_BASELINE"]["latency-view"]

def runExperiments():
    Path(statsdir).mkdir(parents=True, exist_ok=True) # Creating stats directory
    printNodePointParams()

    for numFaults in faults:
        if runBasic: # HotStuff-like baseline
            computeAvgStats(recompile,protocol=Protocol.BASIC,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults,numRepeats=repeats)
        else:
            (0.0,0.0,0.0,0.0)
         
        if runChained: # Chained HotStuff-like baseline
            computeAvgStats(recompile,protocol=Protocol.CHAINED,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults,numRepeats=repeats)
        else:
            (0.0,0.0,0.0,0.0)

        if runPara: # Chained HotStuff-like baseline
            for maxBlocks in maxBlocksInView:
                computeAvgStats(recompile,protocol=Protocol.PARA,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults,numRepeats=repeats, maxBlocksInView=maxBlocks)
        else:
            (0.0,0.0,0.0,0.0)

    print("num complete runs=", completeRuns)
    print("num aborted runs=", abortedRuns)
    print("aborted runs:", aborted)
    createPlot(pointsFile)

parser = argparse.ArgumentParser(description='X-HotStuff evaluation')
parser.add_argument("--docker",     action="store_true",   help="runs nodes locally in Docker containers")
parser.add_argument("--p1",         action="store_true",   help="sets runBasic to True (base protocol, i.e., HotStuff)")
parser.add_argument("--p2",         action="store_true",   help="sets runChained to True (chained base protocol, i.e., chained HotStuff")
parser.add_argument("--p3",         action="store_true",   help="sets runPara to True (new protocol, i.e., Parallel HotStuff")
parser.add_argument("--pall",       action="store_true",   help="sets all runXXX to True, i.e., all protocols will be executed")
parser.add_argument("--repeats",    type=int, default=0,   help="number of repeats per experiment")
parser.add_argument("--netlat",     type=int, default=0,   help="network latency in ms")
parser.add_argument("--netvar",     type=int, default=0,   help="variation of the network latency in ms")
parser.add_argument("--views",      type=int, default=0,   help="number of views to run per experiments")
parser.add_argument("--faults",     type=str, default="",  help="the number of faults to test, separated by commas: 1,2,3,etc.")
parser.add_argument("--payload",    type=int, default=0,   help="size of payloads in Bytes")
parser.add_argument("--maxBlocksInView", type=int, default=10, help="Maximum number of blocks in each view for Parallel HotStuff")

args = parser.parse_args()

if args.views > 0:
    numViews = args.views
    print("SUCCESSFULLY PARSED ARGUMENT - the number of views is now:", numViews)

if args.repeats > 0:
    repeats = args.repeats
    print("SUCCESSFULLY PARSED ARGUMENT - the number of repeats is now:", repeats)

if args.netlat >= 0:
    networkLat = args.netlat
    print("SUCCESSFULLY PARSED ARGUMENT - the network latency (in ms) will be changed using netem to:", networkLat)

if args.payload >= 0:
    payloadSize = args.payload
    print("SUCCESSFULLY PARSED ARGUMENT - the payload size will be:", payloadSize)

if args.netvar >= 0:
    networkVar = args.netvar
    print("SUCCESSFULLY PARSED ARGUMENT - the variation of the network latency (in ms) will be changed using netem to:", networkVar)

if args.docker:
    runDocker = True
    print("SUCCESSFULLY PARSED ARGUMENT - running nodes in Docker containers")

if args.p1:
    runBasic = True
    print("SUCCESSFULLY PARSED ARGUMENT - testing base protocol")

if args.p2:
    runChained = True
    print("SUCCESSFULLY PARSED ARGUMENT - testing chained base protocol")

if args.p3:
    runPara = True
    print("SUCCESSFULLY PARSED ARGUMENT - testing parallel HS protocol")

if args.pall:
    runBasic   = True
    runChained = True
    runPara    = True
    # TODO: Set runPara to True when ready
    print("SUCCESSFULLY PARSED ARGUMENT - testing all protocols")

if __name__ == "__main__":
    print("Throughput and Latency")
    runExperiments()
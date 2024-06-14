## Imports
from subprocess import Popen
import subprocess
from pathlib import Path
import time
import math
import os
import glob
import argparse
from enum import Enum
import re
# import json
import sys
import select

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
    # Removing all (temporary) f
    # files in stats dir
    files0 = glob.glob(statsdir+"/vals*")
    files1 = glob.glob(statsdir+"/throughput-view*")
    files2 = glob.glob(statsdir+"/latency-view*")
    files3 = glob.glob(statsdir+"/handle*")
    files4 = glob.glob(statsdir+"/crypto*")
    files5 = glob.glob(statsdir+"/done*")
    files6 = glob.glob(statsdir+"/client-throughput-latency*")
    #files7 = glob.glob(statsdir+"/client-stats/*")
    #for f in files0 + files1 + files2 + files3 + files4 + files5 + files6 + files7:
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

def printNodePoint(protocol,numFaults,tag,val, maxBlocksInView=0):
    protocol_name = f"{protocol.value}-{maxBlocksInView}BLOCKS" if 'PARALLEL_HOTSTUFF' in protocol.value and maxBlocksInView > 0 else protocol.value
    f = open(pointsFile, 'a')
    f.write("protocol="+protocol_name+" "+"faults="+str(numFaults)+" "+tag+"="+str(val)+"\n")
    f.close()

def printNodePointComment(protocol,numFaults,instance,repeats, maxBlocksInView=0):
    protocol_name = f"{protocol.value}-{maxBlocksInView}BLOCKS" if 'PARALLEL_HOTSTUFF' in protocol.value and maxBlocksInView > 0 else protocol.value
    #numViewsParaLoc = -(numViews // -maxBlocksInView)  
    f = open(pointsFile, 'a')
    f.write("# protocol="+protocol_name+" regions=local "+" payload="+str(payloadSize)+" faults="+str(numFaults)+" instance="+str(instance)+" repeats="+str(repeats) + "\n")
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
    text += " netvar="+str(networkVar)
    text += " numTrans="+str(numTrans)
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
        "client-throughput-view": {"val": 0.0, "num": 0},
        "client-latency-view": {"val": 0.0, "num": 0},
        "client-num-instances": {"val": 0.0, "num": 0},
        "recover-times": {"val": 0.0, "num": 0},
        "view-times": {"val": 0.0, "num": 0}
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
                "recover-times": int(data[7]),
                "view-times": int(data[8])
            }
            for metric, value in metric_values.items():
                metrics[metric]["val"] += value
                metrics[metric]["num"] += 1
                printNodePoint(protocol, numFaults, metric, value, maxBlocksInView)

    # Read client stats
    client_files = glob.glob(statsdir + "/client-stats/client-throughput-latency-*")
    for filename in client_files:
        with open(filename, "r") as f:
            data = f.read().split()
            throughput_view = float(data[0])
            latency_view = float(data[1])
            num_instances = int(data[2])

            metrics["client-throughput-view"]["val"] += throughput_view
            metrics["client-throughput-view"]["num"] += 1
            metrics["client-latency-view"]["val"] += latency_view
            metrics["client-latency-view"]["num"] += 1
            metrics["client-num-instances"]["val"] += num_instances
            metrics["client-num-instances"]["num"] += 1

            # Include client metrics into points
            printNodePoint(protocol, numFaults, "client-throughput-view", throughput_view, maxBlocksInView)
            printNodePoint(protocol, numFaults, "client-latency-view", latency_view, maxBlocksInView)
            printNodePoint(protocol, numFaults, "client-num-instances", num_instances, maxBlocksInView)

    # Calculate averages
    results = {metric: metrics[metric]["val"] / metrics[metric]["num"] if metrics[metric]["num"] > 0 else 0.0 for metric in metrics}

    # Print results
    for metric, result in results.items():
        print(f"{metric}: {result} out of {metrics[metric]['num']}")

    return (results["throughput-view"], results["latency-view"], results["handle"],
            results["crypto-sign"], results["crypto-verif"],
            results["crypto-num-sign"], results["crypto-num-verif"],results["client-throughput-view"], 
            results["client-latency-view"], results["client-num-instances"])

# def print_output(proc, name):
#     """ Helper function to check and print output from a non-blocking read """
#     readable, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0)
#     for r in readable:
#         line = r.readline()
#         if line:
#             print(f"Output from {name}: {line.decode().strip()}")

def print_output(proc, name):
    """ Continuously reads and prints output from a subprocess """
    try:
        for line in iter(proc.stdout.readline, b''):  # Continue reading until stream is empty
            if line:  # Only print if line is not empty
                print(f"Output from {name}: {line.decode().strip()}")
        for line in iter(proc.stderr.readline, b''):
            if line:
                print(f"Error from {name}: {line.decode().strip()}", file=sys.stderr)
    except Exception as e:
        print(f"Error reading output from {name}: {e}")

def executeClusterInstances(nodes, numReps,numClients,protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,instance,maxBlocksInView=0, forceRecover=0, byzantine=-1):
    totalInstances = numReps + numClients
    instanceRepIds = []
    instanceClIds = []

    global ipsOfNodes

    procsRep   = []
    procsCl    = []
    newtimeout = int(math.ceil(timeout+math.log(numFaults,2)))
    #newtimeout = 300

    currentInstance = 0
    for node in nodes:
        instancesPerNode = totalInstances // len(nodes) + (totalInstances % len(nodes) > 0)
        for i in range(instancesPerNode):
            if currentInstance >= totalInstances:
                break
            instanceType = "replica" if currentInstance < numReps else "client"
            instanceName = f"instance_{node['node']}_{i}"
            ip = node['host']
            if instanceType == "replica":
                ipsOfNodes[currentInstance] = ip  # Store IP only for replicas if that's all genLocalConf needs
            currentInstance += 1

    # Generate configuration now that all IPs are collected
    genLocalConf(numReps, addresses)  # Make sure to use the actual filename needed

    config_dir = "/home/aeinarsd/var/scratch/aeinarsd/para-hotstuff/config"
    stats_dir = "/home/aeinarsd/var/scratch/aeinarsd/para-hotstuff/stats"
    bind_config = f"--bind {config_dir}:/app/config"
    bind_stats = f"--bind {stats_dir}:/app/stats"
    bind_app = "--bind /home/aeinarsd/var/scratch/aeinarsd/para-hotstuff/App:/app/App"

    currentInstance = 0
    for node in nodes:
        instancesPerNode = totalInstances // len(nodes) + (totalInstances % len(nodes) > 0)
        for i in range(instancesPerNode):
            if currentInstance >= totalInstances:
                break
            instanceType = "replica" if currentInstance < numReps else "client"
            instanceName = f"instance_{node['node']}_{i}"
            if instanceType == "replica":
                server_command = f"singularity exec {bind_app} {bind_config} {bind_stats} {sing_file} /app/App/server {currentInstance} {numFaults} {constFactor} {numViews} {newtimeout} {maxBlocksInView} {forceRecover} {byzantine}"
                ssh_command = f"ssh {node['user']}@{node['host']} '{server_command}'"
                proc = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                procsRep.append((currentInstance, instanceName, node, proc))
                print(f"Replica {currentInstance} started on {node['host']}")
                instanceRepIds.append((currentInstance, instanceName, node))
            else:
                wait = 5 + int(math.ceil(math.log(numFaults,2)))
                time.sleep(wait)
                client_command = f"singularity exec {bind_app} {bind_config} {bind_stats} {sing_file} /app/App/client {currentInstance} {numFaults} {constFactor} {numClTrans} {sleepTime} {instance} {maxBlocksInView}"
                ssh_command = f"ssh {node['user']}@{node['host']} '{client_command}'"
                proc = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                procsCl.append((currentInstance, instanceName, node, proc))
                print(f"Client {currentInstance} started on {node['host']}")
                instanceClIds.append((currentInstance, instanceName, node))
            currentInstance += 1

    print("started", len(procsRep), "replicas")
    print("started", len(procsCl), "clients")

    totalTime = 0
    time.sleep(300); 
    remaining = procsRep + procsCl
    while remaining and totalTime < cutOffBound:
        print(f"Time elapsed: {totalTime} seconds")
        for p in remaining:
            n, i, node, proc = p
            print_output(proc, i)
            if proc.poll() is None:
                if totalTime >= cutOffBound:  # Custom logic to decide when to stop waiting
                    proc.terminate()  # Forcefully terminate if over timeout
                    print(f"Timeout reached: Terminated node {i}")
            else:
                # print(f"Node {node['host']} has completed")
                print(f"Node {i} has completed")
                remaining.remove(p)  # Process has completed
        time.sleep(1)
        totalTime += 1

    print("All processes completed.")

    for n, i, node, proc in procsRep + procsCl:
        if proc.poll() is None:
            print_output(proc, node['host'])
            proc.terminate()
            proc.wait()
            print(f"Cleanup: Forced termination at node {i}")

    return instanceRepIds, instanceClIds
# # End of executeClusterInstances

def executeCluster(nodes,protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,maxBlocksInView=0,forceRecover=0,byzantine=-1):
    print("<<<<<<<<<<<<<<<<<<<<",
          "protocol="+protocol.value,
          ";payload="+str(payloadSize),
          "(factor="+str(constFactor)+")",
          "#faults="+str(numFaults),
          "[complete-runs="+str(completeRuns),"aborted-runs="+str(abortedRuns)+"]")
    print("aborted runs so far:", aborted)

    numReps = (constFactor * numFaults) + 1

    mkParams(protocol,constFactor,numFaults,numTrans,payloadSize)

    params_dir = "/home/aeinarsd/var/scratch/aeinarsd/para-hotstuff/App/params.h"

    #compile_command = f"singularity exec {sing_file} make -C /app server client"
    print("NOW GOING TO MAKE")
    #compile_command = f"singularity exec --bind {params_dir}:/app/App/params.h {sing_file} make -C /app server client"
    #compile_command = f"singularity exec --bind /home/aeinarsd/var/scratch/aeinarsd/para-hotstuff/App:/app/App {sing_file} 'ls -la /app/App && make -C /app server client'"
    compile_command = f"singularity exec --bind /home/aeinarsd/var/scratch/aeinarsd/para-hotstuff/App:/app/App {sing_file} bash -c 'make -C /app server client'"

    subprocess.run(compile_command, shell=True)

    # The rest of your logic for setting up and executing the experiment
    for instance in range(repeats):
        clearStatsDir()  # Clear any existing data
        instanceRepIds, instanceClIds = executeClusterInstances(nodes, numReps, numClients, protocol, constFactor, numClTrans, sleepTime, numViews, cutOffBound, numFaults, instance, maxBlocksInView, forceRecover, byzantine)
        #executeClusterInstances(instanceRepIds, instanceClIds, protocol, constFactor, numClTrans, sleepTime, numViews, cutOffBound, numFaults, instance, maxBlocksInView, forceRecover, byzantine)
        results = computeStats(protocol, numFaults, instance, repeats, maxBlocksInView)
        print("Results:", results)

# End of executeCluster

def get_host_ips(hostnames):
    ips = {}
    for hostname in hostnames:
        ip = subprocess.getoutput(f"ssh {hostname} hostname -I").split()[0]  # Assumes default username and key are configured
        ips[hostname] = ip
    return ips

def runCluster():
    global numMakeCores
    nuMakeCores = 1
    # Creating stats directory
    Path(statsdir).mkdir(parents=True, exist_ok=True)

    printNodePointParams()

    hostnames = subprocess.check_output('scontrol show hostname $SLURM_JOB_NODELIST', shell=True).decode().strip().split()
    nodes = [{'node': hostname, 'user': os.getenv('USER'), 'host': hostname, 'dir': '/home/aeinarsd/var/scratch/aeinarsd/para-hotstuff'} for hostname in hostnames]

    for numFaults in faults:
        if runBasic:
            executeCluster(nodes,protocol=Protocol.BASIC,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults)
        if runChained:
            executeCluster(nodes,protocol=Protocol.CHAINED,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults)
        if runPara:
            for maxBlocks in maxBlocksInView:
                executeCluster(nodes,protocol=Protocol.PARA,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults,maxBlocksInView=maxBlocks,forceRecover=forceRecover,byzantine=byzantine)

    print("num complete runs=", completeRuns)
    print("num aborted runs=", abortedRuns)
    print("aborted runs:", aborted)

# End of runCluster


parser = argparse.ArgumentParser(description='X-HotStuff evaluation')
parser.add_argument("--docker",     action="store_true",   help="runs nodes locally in Docker containers")
parser.add_argument("--tvl",     action="store_true",   help="run TVL")
parser.add_argument("--prepare",     action="store_true",   help="run prepare for cluster")
parser.add_argument("--cluster",     action="store_true",   help="run on cluster")
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
parser.add_argument("--maxBlocksInView", type=str, default="", help="Maximum number of blocks in each view for Parallel HotStuff")
parser.add_argument("--numTrans", type=int, default=100, help="Maximum number of blocks in each view for Parallel HotStuff")
parser.add_argument("--dir", type=str, default="stats", help="Maximum number of blocks in each view for Parallel HotStuff")
parser.add_argument("--forceRecover", type=float, default=0, help="Maximum number of blocks in each view for Parallel HotStuff")
parser.add_argument("--crash", type=float, default=0, help="Amount of crashes")
parser.add_argument("--byzantine", type=int, default=-1, help="Byzantine nodes")
parser.add_argument("--timeout", type=int, default=5, help="Timeout for leader change")
parser.add_argument("--numclients", type=int, default=1, help="Number of clients for basic")
parser.add_argument("--numclientsch", type=int, default=1, help="Number of clients for chained")
parser.add_argument("--sleeptime", type=int, default=0, help="Sleep between transactions clients")
parser.add_argument("--numcltrans", type=int, default=0, help="Number of transactions per client")
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
if args.numTrans >= 0:
    numTrans = args.numTrans
    print("SUCCESSFULLY PARSED ARGUMENT - the number of transactions per block will be:", numTrans)
if args.dir:
    savedir = args.dir
    pointsFile   = savedir + "/points-" + timestampStr
    print("SUCCESSFULLY PARSED ARGUMENT - the save directory will be:", dir)
if args.forceRecover:
    forceRecover = args.forceRecover
    print("SUCCESSFULLY PARSED ARGUMENT - the forceRecover flag will be:", forceRecover)
if args.crash:
    crash = args.crash
    print("SUCCESSFULLY PARSED ARGUMENT - the crash flag will be:", crash)
if args.byzantine >= 0:
    byzantine = args.byzantine
    print("SUCCESSFULLY PARSED ARGUMENT - byzantine will be:", byzantine)
if args.timeout:
    timeout = args.timeout
    print("SUCCESSFULLY PARSED ARGUMENT - timeout will be:", timeout)
if args.numclients:
    numClients = args.numclients
    print("SUCCESSFULLY PARSED ARGUMENT - number of clients for basic will be:", numClients)
if args.numclientsch:
    numClientsCh = args.numclientsch
    print("SUCCESSFULLY PARSED ARGUMENT - number of clients for chained will be:", numClientsCh)
if args.sleeptime:
    sleepTime = args.sleeptime
    print("SUCCESSFULLY PARSED ARGUMENT - sleep time between transactions will be:", sleepTime)
if args.numcltrans:
    numClTrans = args.numcltrans
    print("SUCCESSFULLY PARSED ARGUMENT - number of transactions per client will be:", numClTrans)
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
if args.faults:
    l = list(map(lambda x: int(x), args.faults.split(",")))
    faults = l
    print("SUCCESSFULLY PARSED ARGUMENT - we will be testing for f in", l)
if args.maxBlocksInView:
    l = list(map(lambda x: int(x), args.maxBlocksInView.split(",")))
    maxBlocksInView = l
    print("SUCCESSFULLY PARSED ARGUMENT - we will be testing for f in", l)
if args.pall:
    runBasic   = True
    runChained = True
    runPara    = True
    # TODO: Set runPara to True when ready
    print("SUCCESSFULLY PARSED ARGUMENT - testing all protocols")

if args.cluster:
    print("lauching cluster experiment")
    runCluster()

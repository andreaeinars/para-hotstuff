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
import random 

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

def print_output(proc, name):
    """ Helper function to check and print output from a non-blocking read """
    try:
        fd_stdout = proc.stdout.fileno()
        fd_stderr = proc.stderr.fileno()
        os.set_blocking(fd_stdout, False)
        os.set_blocking(fd_stderr, False)

        try:
            while True:
                data = os.read(fd_stdout, 1024)
                if data:
                    print(f"Output from {name} (stdout): {data.decode().strip()}")
                    sys.stdout.flush()
                else:
                    break
        except BlockingIOError:
            pass  # No more data to read from stdout

        try:
            while True:
                data = os.read(fd_stderr, 1024)
                if data:
                    print(f"Output from {name} (stderr): {data.decode().strip()}")
                    sys.stdout.flush()
                else:
                    break
        except BlockingIOError:
            pass  # No more data to read from stderr
    except Exception as e:
        print(f"Print ERROR from {name}: {e}")
        sys.stdout.flush()

def get_singularity_pid(command):
    """Retrieve the PID of the main process started by the given Singularity command."""
    try:
        # Adjust the pattern to match the process running inside the Singularity container
        cmd = f"pgrep -f '{command}'"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pid = result.stdout.strip()
        print("FOUND PID: ", pid)
        return pid if pid else None
    except subprocess.CalledProcessError as e:
        print(f"Error getting PID for Singularity container started with command '{command}': {e}")
        return None

def send_signal_to_singularity_container(pid,node, instanceName, signal_type):
    """Send a signal to the main process within a Singularity container."""
    try:
        if pid:
            cmd = f"kill -{signal_type} {pid}"
            ssh_command = f"ssh {node['user']}@{node['host']} '{cmd}'"
            subprocess.run(ssh_command, shell=True, check=True)
            print(f"Signal {signal_type} sent to PID {pid} in Singularity container {instanceName}")
        else:
            print(f"No server process PID available for container {instanceName}")
    except Exception as e:
        print(f"Failed to send signal {signal_type} to Singularity container {instanceName}: {e}")

def crash_container(pid, node,instanceName):
    send_signal_to_singularity_container(pid, node,instanceName, 'USR1')  # Pause the application

def recover_container(pid,node, instanceName):
    send_signal_to_singularity_container(pid,node, instanceName, 'USR2')

def schedule_pauses_and_resumes(subReps, totalTime, numFaults, ratioFaults=1):
    events = []
    crashed_nodes = set()
    crash_interval = 3  # Interval between sets of crashes

    # Calculate the effective number of faults to introduce based on the ratio
    num_act_faults = max(1, int(numFaults * ratioFaults))
    print(num_act_faults)

    current_time = 0
    last_recovery_time = 0
    subReps_names = [rep[1] for rep in subReps]
    while current_time < totalTime:
        # Determine nodes to crash
        if current_time >= last_recovery_time + crash_interval:
            available_nodes = list(set(subReps_names) - crashed_nodes)
            if len(available_nodes) < num_act_faults:
                break  # Not enough nodes to crash

            nodes_to_crash = random.sample(available_nodes, num_act_faults)
            nodes_to_crash_full = [rep for rep in subReps if rep[1] in nodes_to_crash]

            # Schedule crashes and calculate the next earliest possible crash time
            for node in nodes_to_crash_full:
                crash_time = current_time
                recover_time = crash_time + random.randint(3, 5)
                events.append((crash_time, 'crash', node))
                events.append((recover_time, 'recover', node))

                # Update crashed nodes set
                crashed_nodes.add(node[1])
                last_recovery_time = max(last_recovery_time, recover_time)

            # Move time forward by the crash interval
            current_time += crash_interval
        else:
            current_time += 1  # Increment time to check again

        # Recover nodes that are scheduled to be recovered by current_time
        for event in events:
            if event[0] <= current_time and event[1] == 'recover':
                if event[2][1] in crashed_nodes:
                    crashed_nodes.remove(event[2][1])

    # Sort events by time to maintain a correct order in the final list
    events.sort(key=lambda x: x[0])
    return events


def executeClusterInstances(nodes, numReps,numClients,protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,instance,maxBlocksInView=0, forceRecover=0, byzantine=-1):
    totalInstances = numReps + numClients
    instanceRepIds = []
    instanceClIds = []

    global ipsOfNodes

    procsRep   = []
    procsCl    = []
    newtimeout = int(math.ceil(timeout+(math.log(numFaults,2))*500+((math.log(maxBlocksInView,2)))*200))
    #newtimeout = 

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
                pid = get_singularity_pid(server_command)
                pid = int(pid)
                procsRep.append((currentInstance, instanceName, node, proc, pid))
                print(f"Replica {currentInstance} started on {node['host']}")
                instanceRepIds.append((currentInstance, instanceName, node))
            else:
                wait = 5 + int(math.ceil(math.log(numFaults,2)))
                time.sleep(wait)
                client_command = f"singularity exec {bind_app} {bind_config} {bind_stats} {sing_file} /app/App/client {currentInstance} {numFaults} {constFactor} {numClTrans} {sleepTime} {instance} {maxBlocksInView}"
                ssh_command = f"ssh {node['user']}@{node['host']} '{client_command}'"
                proc = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                procsCl.append((currentInstance, instanceName, node, proc, 0))
                print(f"Client {currentInstance} started on {node['host']}")
                instanceClIds.append((currentInstance, instanceName, node))
            currentInstance += 1
            sys.stdout.flush()

    print("started", len(procsRep), "replicas")
    print("started", len(procsCl), "clients")

    events = None
    if crash > 0:
        events = schedule_pauses_and_resumes(procsRep, cutOffBound, numFaults, crash)

    totalTime = 0
    cutOffBound = 200
    remaining = procsRep.copy()
    #time.sleep(10)
    while remaining and totalTime < cutOffBound:
        print(f"Time elapsed: {totalTime} seconds")
        sys.stdout.flush()

        if len(remaining) < 3*numFaults:
            # If any replicas are crashed when its time to record stats, recover them
            if events:
                event_time, action, (n, instanceName, node_info, proc,pid) = events.pop(0)
                #event_time, action, (t, i, p) = events.pop(0)
                while action == "recover":
                    print("Recovering node: ",instanceName, " so it can record stats")
                    recover_container(pid,node_info, instanceName)
                    event_time, action, (n, instanceName, node_info, proc,pid) = events.pop(0)
                events.clear()
        
        if crash > 0 :
            while events and events[0][0] <= totalTime:
                event_time, action, (n, instanceName, node_info, proc,pid) = events.pop(0)
                if action == "crash":
                    crash_container(pid,node_info, instanceName)
                elif action == "recover":
                    recover_container(pid, node_info,instanceName)
        
                print(f"{action} node {i} at time {event_time}")
        

        for p in remaining.copy():
            n, i, node, proc, pid = p
            print_output(proc, i)
            if proc.poll() is not None:
                print(f"Node {i} has completed")
                sys.stdout.flush()
                remaining.remove(p)


        time.sleep(1)
        totalTime += 1

    if totalTime >= cutOffBound:
        print("Timeout reached. Terminating all processes.")

    print("All processes completed.")
    sys.stdout.flush()
    for n, i, node, proc,pid in procsRep.copy() + procsCl.copy():
        if proc.poll() is None:
            print_output(proc, i)
            proc.terminate()
            proc.wait()
            print(f"Cleanup: Forced termination at node {i}")
            sys.stdout.flush()

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
    print("NOW GOING TO MAKE")
    sys.stdout.flush()
    compile_command = f"singularity exec --bind /home/aeinarsd/var/scratch/aeinarsd/para-hotstuff/App:/app/App {sing_file} bash -c 'ls /app/App && make -C /app clean && make -C /app server client'"

    subprocess.run(compile_command, shell=True)

    if networkLat > 0:
        latcmd = f"tc qdisc add dev eth0 root netem delay {networkLat}ms {networkVar}ms distribution normal"
        latency_command = f"singularity exec {sing_file} bash -c \"{latcmd}\""
        subprocess.run(latency_command, shell=True, check=True)

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
parser.add_argument("--timeout", type=int, default=20, help="Timeout for leader change")
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

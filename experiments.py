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
import random 
import json

from exp_params import *

## Code
class Protocol(Enum):
    BASIC      = "BASIC_BASELINE"           # basic baseline
    CHAINED    = "CHAINED_BASELINE"         # chained baseline
    PARA       = "PARALLEL_HOTSTUFF"        # parallel hotstuff

def get_slurm_node_ips():
    """ Retrieves the IP addresses of nodes allocated by SLURM. """
    hostnames = subprocess.check_output(['scontrol', 'show', 'hostname', os.environ['SLURM_JOB_NODELIST']])
    hostnames = hostnames.decode().strip().split('\n')
    ips = []
    for hostname in hostnames:
        ip = subprocess.check_output(['getent', 'hosts', hostname]).split()[0].decode()
        ips.append(ip)
    return ips

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

def schedule_pauses_and_resumes(subReps, totalTime, numFaults, ratioFaults=1):
    events = []
    crashed_nodes = set()
    crash_interval = 2  # Interval between sets of crashes

    # Calculate the effective number of faults to introduce based on the ratio
    num_act_faults = max(1, int(numFaults * ratioFaults))
    print(num_act_faults)

    current_time = 0
    last_recovery_time = 0

    while current_time < totalTime:
        # Determine nodes to crash
        if current_time >= last_recovery_time + crash_interval:
            available_nodes = list(set(subReps) - crashed_nodes)
            if len(available_nodes) < num_act_faults:
                break  # Not enough nodes to crash

            nodes_to_crash = random.sample(available_nodes, num_act_faults)

            # Schedule crashes and calculate the next earliest possible crash time
            for node in nodes_to_crash:
                crash_time = current_time
                recover_time = crash_time + random.randint(3, 5)
                events.append((crash_time, 'crash', node))
                events.append((recover_time, 'recover', node))

                # Update crashed nodes set
                crashed_nodes.add(node)
                last_recovery_time = max(last_recovery_time, recover_time)

            # Move time forward by the crash interval
            current_time += crash_interval
        else:
            current_time += 1  # Increment time to check again

        # Recover nodes that are scheduled to be recovered by current_time
        for event in events:
            if event[0] <= current_time and event[1] == 'recover':
                if event[2] in crashed_nodes:
                    crashed_nodes.remove(event[2])

    # Sort events by time to maintain a correct order in the final list
    events.sort(key=lambda x: x[0])
    return events

def get_server_pid(container_name):
    """Retrieve the PID of the server process within the specified Docker container."""
    try:
        cmd = f"docker exec {container_name} ps aux | awk '$11==\"./server\" {{print $2}}'"
        pid = subprocess.check_output(cmd, shell=True).decode().strip()
        if pid:
            return pid
        else:
            print(f"No server process found in Docker container {container_name}")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Failed to find server PID in container {container_name}: {str(e)}")
        return None

def send_signal_to_docker_container(container_name, signal_type):
    """Send a signal to the main process within a Docker container."""
    try:
        pid = get_server_pid(container_name)
        if pid:
            cmd = f"docker exec {container_name} kill -{signal_type} {pid}"
            subprocess.run(cmd, shell=True, check=True)
            print(f"Signal {signal_type} sent to PID {pid} in Docker container {container_name and pid}")
        else:
            print(f"No server process PID available for container {container_name}")
    except:
        pass

def crash_container(dockerInstance):
   send_signal_to_docker_container(dockerInstance, 'USR1')  # Pause the application

def recover_container(dockerInstance):
   send_signal_to_docker_container(dockerInstance, 'USR2') 

def execute(protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,instance, maxBlocksInView=0, forceRecover=0, byzantine=-1):
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
        cmd = f"{server} {i} {numFaults} {constFactor} {numViews} {newtimeout} {maxBlocksInView} {forceRecover} {byzantine}"
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
        cmd = f"{client} {cid} {numFaults} {constFactor} {numClTrans} {sleepTime} {instance} {maxBlocksInView}"
        #cmd = " ".join([client, str(cid), str(numFaults), str(constFactor), str(numClTrans), str(sleepTime), str(instance)])
        if runDocker:
            dockerInstance = dockerBase + "c" + str(cid)
            cmd = docker + " exec -t " + dockerInstance + " bash -c \"" + cmd + "\""
        c = Popen(cmd, shell=True)
        subsClients.append(("C",cid,c))

    print("started", len(subsClients), "clients")

    totalTime = 0

    if expmode == "TVL":
        remaining = subsClients.copy()
        numTotClients = len(subsClients)
        while 0 < len(remaining) and totalTime < cutOffBound:
            print(str(len(remaining)) + " remaining clients out of " + str(numTotClients) + ":", remaining)
            cFileBase = "client-throughput-latency-" + str(instance)
            if runDocker:
                rem = remaining.copy()
                for (t,i,p) in rem:
                    cFile = cFileBase + "-" + str(i) + "*"
                    dockerInstance = dockerBase + "c" + str(i)
                    cmd = "find /app/" + statsdir + " -name " + cFile + " | wc -l"
                    out = int(subprocess.run(docker + " exec -t " + dockerInstance + " bash -c \"" + cmd + "\"", shell=True, capture_output=True, text=True).stdout)
                    if 0 < int(out):
                        print("found clients stats for client ", str(i))
                        remaining.remove((t,i,p))
            else:
                remaining = list(filter(lambda x: 0 == len(glob.glob(statsdir + "/" + cFileBase + "-" + str(x[1]) + "*")), remaining))
                #files = glob.glob(statsdir+"/client-throughput-latency-"+str(instance)+"*")
                #numFiles = len(files)
            time.sleep(1)
            totalTime += 1
        for (t,i,p) in subsReps + subsClients:
            p.kill()
    else:
        # print("SUBREPS: ", subsReps)
        events = None
        if crash == 0.5:
            events = schedule_pauses_and_resumes(subsReps, cutOffBound, numFaults, 0.5)
        elif crash == 1:
            events = schedule_pauses_and_resumes(subsReps, cutOffBound, numFaults, 1)
        # print("EVENTS:", events)

        remaining = subsReps.copy()
        # We wait here for all processes to complete
        # but we stop the execution if it takes too long (cutOffBound)
        while 0 < len(remaining) and totalTime < cutOffBound:
            # print("Current time: ", totalTime)
            #print("remaining processes:", remaining, " len events: ", len(events))
            # for event in events:
            #     print("EVENT: ", event)
            if len(remaining) < 3*numFaults: # Not enough nodes are running
                # Check if any node has crashed and recover it
                #for (t, i, p) in remaining:
                #if events and events[0][0] <= totalTime and events[0][1] == "recover":
                # We want to recover any chrashed nodes at this point cause we know that the remaining nodes are less than the number of faults
                # So we recover it, so it can record stats
                # TODO: Make sure it works for more than 1 fault
                if events and events[0][1] == "recover":
                    event_time, action, (t, i, p) = events.pop(0)
                    #crashed_node_index = events[0][2]  # Get the index of the node to be recovered
                    print("Recovering node: ",i, " so it can record stats")
                    dockerInstance = dockerBase + str(i)
                    recover_container(dockerInstance)
                    events.clear()
                    #events.pop(0)     
            
            if crash > 0 :
                while events and events[0][0] <= totalTime:
                    event_time, action, (t, i, p) = events.pop(0)
                    dockerInstance = dockerBase + str(i)

                    if action == "crash":
                        crash_container(dockerInstance)
                    elif action == "recover":
                        recover_container(dockerInstance)
            
                    print(f"{action} node {i} at time {event_time}")

            # We filter out the ones that are done. x is of the form (t,i,p)
            if runDocker:
                rem = remaining.copy()
                for (t,i,p) in rem:
                    dockerInstance = dockerBase + str(i)
                    cmd_check_dir = "if [ -d /app/stats ]; then find /app/stats -name 'done-*' | wc -l; else echo 0; fi"
                    cmd = docker + " exec -t " + dockerInstance + " bash -c \"" + cmd_check_dir + "\""
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
                    if result.isdigit() and int(result) > 0:
                        remaining.remove((t, i, p))
                    # out = int(result)
                    # if 0 < int(out):
                    #     remaining.remove((t,i,p))
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
            print("Now going to copy from: ", i)
            dockerInstance = dockerBase + i
            kcmd = "killall -q server client; fuser -k " + ports
            subprocess.run([docker + " exec -t " + dockerInstance + " bash -c \"" + kcmd + "\""], shell=True) #, check=True)
            src = dockerInstance + ":/app/" + statsdir + "/."
            dst = statsdir + "/"

            # if 'c' in i:
            #     dst = statsdir + "/client-stats/"
            # else:
            #     dst = statsdir + "/"
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

def computeAvgStats(recompile, protocol, constFactor, numClTrans, sleepTime, numViews, cutOffBound, numFaults, numRepeats, maxBlocksInView=0, forceRecover=0, byzantine=-1):
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
        "clientThroughputViews": [],
        "clientLatencyViews": [],
        "clientNumInstances": []
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
        execute(protocol, constFactor, numClTrans, sleepTime, numViews, cutOffBound, numFaults, i, maxBlocksInView, forceRecover, byzantine)
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
    #
    #         data_dict["BASIC_BASELINE"]["latency-view"], data_dict["CHAINED_BASELINE"]["latency-view"]

def printClientPoint(protocol,sleepTime,numFaults,throughput,latency,numPoints):
    f = open(clientsFile, 'a')
    f.write("protocol="+protocol.value+" "+"sleep="+str(sleepTime)+" "+"faults="+str(numFaults)+" throughput="+str(throughput)+" latency="+str(latency)+" numPoints="+str(numPoints)+"\n")
    f.close()

def computeClientStats(protocol,numClTrans,sleepTime,numFaults):
    throughputs = []
    latencies   = []
    numExecs  = []
    files       = glob.glob(statsdir+"/*")
    for filename in files:
        if filename.startswith(statsdir+"/client-throughput-latency"):
            f = open(filename, "r")
            s = f.read()
            [thr,lat,numExec] = s.split(" ")
            if (float(numExec) > 0.0):
                throughputs.append(float(thr))
                latencies.append(float(lat))
            numExecs.append(float(numExec))

    #printClientPoint(protocol,sleepTime,numFaults,throughput,latency,numPoints)

    print("LAT: ", latencies)
    #print("LAT2: ", latencies2)

    # we remove the top and bottom 10% quantiles
    l   = len(latencies)
    num = int(l/(100/quantileSize))

    throughputsSorted = sorted(throughputs)
    latenciesSorted   = sorted(latencies)

    newthroughputs = throughputsSorted[num:l-num]
    newlatencies   = latenciesSorted[num:l-num]

    throughput = 0.0
    for i in newthroughputs:
        throughput += i
    throughput = throughput/len(newthroughputs) if len(newthroughputs) > 0 else -1.0

    latency = 0.0
    for i in newlatencies:
        latency += i
    latency = latency/len(newlatencies) if len(newlatencies) > 0 else -1.0

    f = open(debugFile, 'a')
    f.write("------------------------------\n")
    f.write("Protocol: "+protocol.value+"\n")
    f.write("numClTrans="+str(numClTrans)+";sleepTime="+str(sleepTime)+";length="+str(l)+";remove="+str(num)+";throughput="+str(throughput)+";latency="+str(latency)+"\n")
    f.write("numExec="+str(numExecs)+"\n")
    f.write("Not sorted thr:" + str(throughputs) + "\n")
    f.write("Not sorted lats:" + str(latencies) + "\n")
    f.write("before:\n")
    f.write(str(throughputsSorted)+"\n")
    f.write(str(latenciesSorted)+"\n")
    f.write("after:\n")
    f.write(str(newthroughputs)+"\n")
    f.write(str(newlatencies)+"\n")
    f.close()
    print("numClTrans="+str(numClTrans)+";sleepTime="+str(sleepTime)+";length="+str(l)+";remove="+str(num)+";throughput="+str(throughput)+";latency="+str(latency))
    print("before:")
    print(throughputs)
    print(latencies)
    print("after:")
    print(newthroughputs)
    print(newlatencies)

    numPoints = l-(2*num)
    printClientPoint(protocol,sleepTime,numFaults,throughput,latency,numPoints)
# Enf of computeClientStats

def oneTVL(protocol,constFactor,numFaults,numTransPerBlock,payloadSize,numClTrans,numViews,cutOffBound,sleepTimes,repeats, maxBlocksInView=0):
    numReps = (constFactor * numFaults) + 1

    if runDocker:
        startContainers(numReps,numClients)

    mkApp(protocol,constFactor,numFaults,numTransPerBlock,payloadSize)
    for sleepTime in sleepTimes:
        clearStatsDir()
        for i in range(repeats):
            print(">>>>>>>>>>>>>>>>>>>>",
                  "protocol="+protocol.value,
                  ";payload="+str(payloadSize),
                  "(factor="+str(constFactor)+")",
                  "sleep="+str(sleepTime),
                  "#faults="+str(numFaults),
                  "repeat="+str(i))
            time.sleep(2)
            execute(protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,i, maxBlocksInView)
        computeClientStats(protocol,numClTrans,sleepTime,numFaults)

    if runDocker:
        stopContainers(numReps,numClients)
# End of oneTVL


def createTVLplot(cFile,instances):
    LBase = []
    TBase = []
    aBase = []

    LChBase = []
    TChBase = []
    aChBase = []

    LPara = []
    TPara = []
    aPara = []

    print("reading points from:", cFile)
    f = open(cFile,'r')
    for line in f.readlines():
        if not line.startswith("#"):
            [prot,slp,faults,thr,lat,np] = line.split(" ")
            [protTag,protVal]     = prot.split("=")
            [sleepTag,sleepVal]   = slp.split("=")
            [faultsTag,faultsVal] = faults.split("=")
            [thrTag,thrVal]       = thr.split("=")
            [latTag,latVal]       = lat.split("=")
            [npTag,npVal]         = np.split("=") # number of points
            throughput = float(thrVal)
            latency    = float(latVal)
            sleep      = float(sleepVal)
            if protVal == "BASIC_BASELINE":
                TBase.append(throughput)
                LBase.append(latency)
                aBase.append(sleep)
            if protVal == "CHAINED_BASELINE":
                TChBase.append(throughput)
                LChBase.append(latency)
                aChBase.append(sleep)
            if protVal == "PARALLEL_HOTSTUFF":
                TPara.append(throughput)
                LPara.append(latency)
                aPara.append(sleep)


    LW = 1 # linewidth
    MS = 5 # markersize
    XYT = (0,5)

    #fig, ax=plt.subplots()

    plt.cla()
    plt.clf()

    ## Plotting
    print("plotting")
    if debugPlot:
        plt.title("Throughput vs. Latency\n(file="+cFile+",instances="+str(instances)+")")
    # else:
    #     plt.title("Throughput vs. Latency")

    plt.xlabel("throughput (Kops/sec)", fontsize=12)
    plt.ylabel("latency (ms)", fontsize=12)
    if plotBasic:
        if len(TBase) > 0:
            plt.plot(TBase,   LBase,   color=basicCOL,   linewidth=LW, marker=basicMRK,   markersize=MS, linestyle=basicLS,   label=basicHS)
    if plotChained:
        if len(TChBase) > 0:
            plt.plot(TChBase, LChBase, color=chainedCOL, linewidth=LW, marker=chainedMRK, markersize=MS, linestyle=chainedLS, label=chainedHS)
    if plotPara:
        if len(TPara) > 0:
            plt.plot(TPara, LPara, linewidth=LW, marker=paraMRK, markersize=MS, linestyle=paraLS, label=paraHS)
    if debugPlot:
        if plotBasic:
            for x,y,z in zip(TBase, LBase, aBase):
                plt.annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
        if plotChained:
            for x,y,z in zip(TChBase, LChBase, aChBase):
                plt.annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')
        if plotPara:
            for x,y,z in zip(TPara, LPara, aPara):
                plt.annotate(z,(x,y),textcoords="offset points",xytext=XYT,ha='center')

    # Font
    plt.rcParams.update({'font.size': 12})

    # legend
    plt.legend()

    #ax.set_aspect(aspect=0.1)
    if logScale:
        plt.yscale('log')
    #plt.yscale('log',base=2)

    plt.savefig(tvlFile, bbox_inches='tight', pad_inches=0.05)
    print("plot is in", tvlFile)
    if displayPlot:
        subprocess.call([displayApp,tvlFile])
# Enf of createTVLplot

def TVL():
    # Creating stats directory
    Path(statsdir).mkdir(parents=True, exist_ok=True)

    global expmode
    expmode = "TVL"

    global debugPlot
    debugPlot = True

    # Values for the non-chained versions
    #numClTrans   = 110000
    numClTrans   = 100000 #250000 #260000 #500000 # - 100000 seems fine for basic versions
    #numClients   = 5 #2 #16 #1 # --- 1 seems fine for basic versions

    # Values for the chained version
    numClTransCh = 100000 #250000 #260000 #500000 # - 100000 seems fine for basic versions
    #numClientsCh = 6 #4 #16 #1 # --- 1 seems fine for basic versions

    numFaults        = 1
    numTransPerBlock = 400 #10
    payloadSize      = 0 #256
    numViews         = 0 # nodes don't stop
    cutOffBound      = 200


    ## For testing purposes, we use less repeats then
    test = True


    if test:
        #sleepTimes = [500,100,50,10,5,0]
        #sleepTimes = [900,500,100,50,10,5,0]
        sleepTimes = [900]
    else:
        sleepTimes = [900,700,500,100,50,10,5,0] #[500,50,0] #

    f = open(clientsFile, 'a')
    f.write("# transactions="+str(numClTrans)+" "+
            "faults="+str(numFaults)+" "+
            "transactions="+str(numTransPerBlock)+" "+
            "payload="+str(payloadSize)+" "+
            "cutoff="+str(cutOffBound)+" "+
            "repeats="+str(repeats)+" "+
            "rates="+str(sleepTimes)+"\n")
    f.close()

    ## TODO : make this a parameter instead
    global numClients
    numClients = numNonChCls

    # HotStuff-like baseline
    if runBasic:
        oneTVL(protocol=Protocol.BASIC,
               constFactor=3,
               numFaults=numFaults,
               numTransPerBlock=numTransPerBlock,
               payloadSize=payloadSize,
               numClTrans=numClTrans,
               numViews=numViews,
               cutOffBound=cutOffBound,
               sleepTimes=sleepTimes,
               repeats=repeats)


    numClients = numChCls

    # Chained HotStuff-like baseline
    if runChained:
        oneTVL(protocol=Protocol.CHAINED,
               constFactor=3,
               numFaults=numFaults,
               numTransPerBlock=numTransPerBlock,
               payloadSize=payloadSize,
               numClTrans=numClTransCh,
               numViews=numViews,
               cutOffBound=cutOffBound,
               sleepTimes=sleepTimes,
               repeats=repeats)
        
    # Parallel HotStuff-like baseline
    if runPara:
        for maxBlocks in maxBlocksInView:
            oneTVL(protocol=Protocol.PARA,
                    constFactor=3,
                    numFaults=numFaults,
                    numTransPerBlock=numTransPerBlock,
                    payloadSize=payloadSize,
                    numClTrans=numClTrans,
                    numViews=numViews,
                    cutOffBound=cutOffBound,
                    sleepTimes=sleepTimes,
                    repeats=repeats,
                    maxBlocksInView=maxBlocks)
                

    createTVLplot(clientsFile,numClTrans)
    print("debug info is in", debugFile)
# End of TVL

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
                #numViewsPara = -(numViews // -maxBlocks) # Want to ceil the division, and we want to process the same amount of blocks as in the other protocols instead of views
                computeAvgStats(recompile,protocol=Protocol.PARA,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults,numRepeats=repeats, maxBlocksInView=maxBlocks, forceRecover=forceRecover, byzantine=byzantine)
        else:
            (0.0,0.0,0.0,0.0)

    print("num complete runs=", completeRuns)
    print("num aborted runs=", abortedRuns)
    print("aborted runs:", aborted)
    createPlot(pointsFile)

def prepareCluster():
    f = open(clusterFile,'r')
    info = json.load(f)
    f.close()

    nodes = info["nodes"]
    procs = []
    for node in nodes:
        sshAdr = node["user"] + "@" + node["host"]
        prep_cmd = "cd " + node["dir"] + "; git clone https://github.com/andreaeinars/para-hotstuff.git; cd para-hotstuff; docker build -t para-hotstuff ."
        s = Popen(["ssh","-i",node["key"],"-o",sshOpt1,"-ntt",sshAdr,prep_cmd])
        procs.append((node,s))

    for (node,p) in procs:
        while (p.poll() is None):
            time.sleep(1)
        print("docker container built for node:",node["node"])

# nodes contains the nodes' information
def startRemoteContainers(nodes,numReps,numClients):
    print("running in docker mode, starting" , numReps, "containers for the replicas and", numClients, "for the clients")

    global ipsOfNodes

    totalInstances = numReps + numClients
    instancesPerNode = totalInstances // len(nodes) + (totalInstances % len(nodes) > 0)
    instanceRepIds = []
    instanceClIds = []

    currentInstance = 0
    for node in nodes:
        for i in range(instancesPerNode):
            if currentInstance >= totalInstances:
                break
            instanceType = "replica" if currentInstance < numReps else "client"
            instanceName = f"{dockerBase}_{node['node']}_{i}"

            # Setup the Docker command to run the container
            dockerCommand = (
                f"docker run -d --expose=8000-9999 --network={clusterNet} "
                f"--cap-add=NET_ADMIN --name {instanceName} {dockerBase}"
            )
            sshCommand = f"ssh -i {node['key']} {node['user']}@{node['host']} '{dockerCommand}'"
            subprocess.run(sshCommand, shell=True)

            # Fetch the IP address of the container
            ipCommand = f"docker inspect -f '{{{{.NetworkSettings.Networks.{clusterNet}.IPAddress}}}}' {instanceName}"
            ipSSHCommand = f"ssh -i {node['key']} {node['user']}@{node['host']} '{ipCommand}'"
            ipResult = subprocess.run(ipSSHCommand, shell=True, capture_output=True, text=True)
            ip = ipResult.stdout.strip()

            if ip:
                if instanceType == "replica":
                    ipsOfNodes[currentInstance] = ip
                    instanceRepIds.append((currentInstance, instanceName, node))
                else:
                    instanceClIds.append((currentInstance, instanceName, node))
                print(f"Started {instanceType} {instanceName} at IP {ip} on {node['host']}.")

            currentInstance += 1

    genLocalConf(numReps,addresses)

    return (instanceRepIds, instanceClIds)
## End of startRemoteContainers

def makeCluster(instanceIds):
    ncores = numMakeCores if useMultiCores else 1
    print(">> making",str(len(instanceIds)),"instance(s) using",str(ncores),"core(s)")

    procs  = []
    make0  = "make -j "+str(ncores)
    make   = make0 + " server client"

    for (n,i,node) in instanceIds:
        instanceName = dockerBase + f"_{node['node']}_{i}"
        sshAdr = f"{node['user']}@{node['host']}"
        keyPath = node['key']
        dirPath = node['dir']

        # Copy parameter files to node
        scp_cmd = f"scp -i {keyPath} -o {sshOpt1} params.h {sshAdr}:{dirPath}/params.h"
        subprocess.run(scp_cmd, shell=True)

        # Copy parameters into the Docker container
        docker_cp_cmd = f"docker cp {dirPath}/params.h {instanceName}:/app/App/"
        ssh_cp_cmd = f"ssh -i {keyPath} -o {sshOpt1} {sshAdr} '{docker_cp_cmd}'"
        subprocess.run(ssh_cp_cmd, shell=True)

        # Compile the application inside the Docker container
        docker_exec_cmd = f"docker exec -t {instanceName} bash -c 'make clean; {make}'"
        ssh_exec_cmd = f"ssh -i {keyPath} -o {sshOpt1} {sshAdr} '{docker_exec_cmd}'"
        proc = subprocess.Popen(ssh_exec_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procs.append((n, i, node, proc))

    for (n, i, node, p) in procs:
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            print(f"Error compiling on instance {i} at {node['host']}: {stderr.decode()}")
        else:
            print(f"Instance {i} at {node['host']} compiled successfully.")

    print("all instances are made")
# End of makeCluster

def executeClusterInstances(instanceRepIds,instanceClIds,protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,instance,maxBlocksInView=0, forceRecover=0, byzantine=-1):
    print(">> connecting to",str(len(instanceRepIds)),"replica instance(s)")
    print(">> connecting to",str(len(instanceClIds)),"client instance(s)")

    procsRep   = []
    procsCl    = []
    newtimeout = int(math.ceil(timeout+math.log(numFaults,2)))

    # FOR REPLICAS
    for (n, i, node) in instanceRepIds:
        instanceName = f"{dockerBase}_{node['host']}_{i}"
        sshAdr = f"{node['user']}@{node['host']}"
        server_cmd = f"{docker} exec -t {instanceName} ./server {n} {numFaults} {constFactor} {numViews} {newtimeout} {maxBlocksInView} {forceRecover} {byzantine}"
        ssh_cmd = f"ssh -i {node['key']} {sshAdr} '{server_cmd}'"
        proc = subprocess.Popen(ssh_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procsRep.append((n, i, node, proc))
        print(f"Replica {n} started on {node['host']}")

    print("started", len(procsRep), "replicas")

    # we give some time for the replicas to connect before starting the clients
    wait = 5 + int(math.ceil(math.log(numFaults,2)))
    time.sleep(wait)

    # FOR CLIENTS
    for (n, i, node) in instanceClIds:
        instanceName = f"{dockerBase}_{node['host']}_{i}"
        sshAdr = f"{node['user']}@{node['host']}"
        client_cmd = f"{docker} exec -t {instanceName} ./client {n} {numFaults} {constFactor} {numClTrans} {sleepTime} {instance} {maxBlocksInView}"
        ssh_cmd = f"ssh -i {node['key']} {sshAdr} '{client_cmd}'"
        proc = subprocess.Popen(ssh_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procsCl.append((n, i, node, proc))
        print(f"Client {n} started on {node['host']}")

    print("started", len(procsCl), "clients")

    totalTime = 0

    if expmode == "TVL":
        print("TO FIX: TVL option")
    else:
        remaining = procsRep
        # We wait here for all processes to complete
        # but we stop the execution if it takes too long (cutOffBound)
        while remaining and totalTime < cutOffBound:
            for p in remaining:
                tag, n, i, node, proc = p
                if proc.poll() is None:  # Process is still running
                    sshAdr = f"{node['user']}@{node['host']}"
                    dockerI = f"{dockerBase}_{node['host']}_{i}"
                    doneFile = f"done-{i}.txt"
                    find_cmd = f"ssh -i {node['key']} {sshAdr} \"{docker} exec -t {dockerI} sh -c 'test -e /app/{statsdir}/{doneFile} && echo 1 || echo 0'\""
                    result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
                    if result.stdout.strip() == '1':
                        remaining.remove(p)  # Process done, remove from list
                else:
                    remaining.remove(p)  # Process terminated, remove from list
            print("remaining processes:", remaining)
            # We filter out the ones that are done. x is of the form (t,i,p)
            time.sleep(1)
            totalTime += 1

    global completeRuns, abortedRuns, aborted

    if remaining:
        print("Time cutoff reached. Aborting remaining processes.")
        abortedRuns += len(remaining)
        conf = (protocol,numFaults,instance)
        aborted.append(conf)
        f = open(abortedFile, 'a')
        f.write(str(conf)+"\n")
        f.close()
        for tag, n, i, node, proc in remaining:
            proc.terminate()
            print(f"Aborted {tag} at node {n}")
    else:
        completeRuns += 1
        print("All processes completed within the time limit.")

    for tag, n, i, node, proc in procsRep + procsCl:
        if proc.poll() is None:  # Check if the process is still running
            print(f"Still running: {tag} at node {n}, terminating now.")
            proc.terminate()  # Forcefully terminate the process
            proc.wait()  # Wait for the process to terminate
        # Additional cleanup commands sent to each node
        sshAdr = f"{node['user']}@{node['host']}"
        dockerI = f"{dockerBase}_{node['host']}_{i}"
        cleanup_cmd = f"ssh -i {node['key']} {sshAdr} '{docker} stop {dockerI}; {docker} rm {dockerI}'"
        subprocess.run(cleanup_cmd, shell=True)
        print(f"Cleanup commands sent to {node['host']}")
# End of executeClusterInstances

def executeCluster(nodes,protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,maxBlocksInView=0,forceRecover=0,byzantine=-1):
    print("<<<<<<<<<<<<<<<<<<<<",
          "protocol="+protocol.value,
          ";payload="+str(payloadSize),
          "(factor="+str(constFactor)+")",
          "#faults="+str(numFaults),
          "[complete-runs="+str(completeRuns),"aborted-runs="+str(abortedRuns)+"]")
    print("aborted runs so far:", aborted)

    numReps = (constFactor * numFaults) + 1

    # starts the containers
    (instanceRepIds,instanceClIds) = startRemoteContainers(nodes,numReps,numClients)
    mkParams(protocol,constFactor,numFaults,numTrans,payloadSize)
    # make all nodes
    makeCluster(instanceRepIds+instanceClIds)

    for instance in range(repeats):
        clearStatsDir()
        # execute the experiment
        executeClusterInstances(instanceRepIds,instanceClIds,protocol,constFactor,numClTrans,sleepTime,numViews,cutOffBound,numFaults,instance, maxBlocksInView, forceRecover, byzantine)
        results = computeStats(protocol, numFaults, instance, repeats, maxBlocksInView)

        # (throughputView,latencyView,handle,cryptoSign,cryptoVerif,cryptoNumSign,cryptoNumVerif) = computeStats(protocol,numFaults,instance,repeats)

    for (n, i, node) in instanceRepIds + instanceClIds:
        sshCmd = f"ssh {node['user']}@{node['host']} '{docker} stop {dockerBase + i}; {docker} rm {dockerBase + i}'"
        subprocess.run(sshCmd, shell=True)
# End of executeCluster

def runCluster():
    global numMakeCores
    nuMakeCores = 1
    # Creating stats directory
    Path(statsdir).mkdir(parents=True, exist_ok=True)

    printNodePointParams()

    hostnames = subprocess.check_output('scontrol show hostname $SLURM_JOB_NODELIST', shell=True).decode().strip().split()
    #Create dummy hostnames for testing 
    #hostnames = ["node1", "node2", "node3"]
    #nodes = [{'node': hostname, 'user': os.getenv('USER'), 'host': hostname, 'dir': '/home/aeinarsd/parahs-test', 'key': '/home/aeinarsd/id_rsa.parahs'} for hostname in hostnames]
    nodes = [{'node': hostname, 'user': os.getenv('USER'), 'host': hostname, 'dir': '/home/aeinarsd/parahs-test', 'key': ''} for hostname in hostnames]

    #init_cmd  = docker + " swarm init"
    leave_cmd = docker + " swarm leave --force"
    join_cmd = None

    if hostnames:
        master_node = hostnames[0]
        try:
            # Try to initialize the swarm
            result = subprocess.check_output(f"{docker} -H {master_node} swarm init", shell=True).decode()
            join_cmd_match = re.search("docker swarm join --token .*", result)
            join_cmd = join_cmd_match.group(0) if join_cmd_match else None
        except subprocess.CalledProcessError as e:
            print("Swarm initialization failed:", e)

    # Join the swarm on other nodes
    if join_cmd:
        for node in hostnames[1:]:  # Skip the first node since it's the master
            subprocess.run(f"ssh {node['user']}@{node['host']} '{join_cmd}'", shell=True)

    # Create an overlay network
    if join_cmd:
        net_cmd = docker + " network create --driver=overlay --attachable " + clusterNet
        subprocess.run(net_cmd, shell=True)

    for numFaults in faults:
        if runBasic:
            executeCluster(nodes,protocol=Protocol.BASIC,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults)
        if runChained:
            executeCluster(nodes,protocol=Protocol.CHAINED,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults)
        if runPara:
            for maxBlocks in maxBlocksInView:
                executeCluster(nodes,protocol=Protocol.PARA,constFactor=3,numClTrans=numClTrans,sleepTime=sleepTime,numViews=numViews,cutOffBound=cutOffBound,numFaults=numFaults,maxBlocksInView=maxBlocks,forceRecover=forceRecover,byzantine=byzantine)

    for node in nodes:
        subprocess.run(f"ssh {node['user']}@{node['host']} '{leave_cmd}'", shell=True)
    subprocess.run([docker + " network rm " + clusterNet], shell=True)

    print("num complete runs=", completeRuns)
    print("num aborted runs=", abortedRuns)
    print("aborted runs:", aborted)

    createPlot(pointsFile)
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


if args.tvl:
    TVL()
elif args.prepare:
    print("preparing cluster")
    prepareCluster()
elif args.cluster:
    print("lauching cluster experiment")
    runCluster()
else:
    runExperiments()
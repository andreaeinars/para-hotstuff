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


# def prepareCluster():
#     f = open(clusterFile,'r')
#     info = json.load(f)
#     f.close()

#     nodes = info["nodes"]
#     procs = []
#     for node in nodes:
#         sshAdr = node["user"] + "@" + node["host"]
#         prep_cmd = "cd " + node["dir"] + "; git clone https://github.com/andreaeinars/para-hotstuff.git; cd para-hotstuff; docker build -t para-hotstuff ."
#         s = Popen(["ssh","-i",node["key"],"-o",sshOpt1,"-ntt",sshAdr,prep_cmd])
#         procs.append((node,s))

#     for (node,p) in procs:
#         while (p.poll() is None):
#             time.sleep(1)
#         print("docker container built for node:",node["node"])

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
            #ipResult = subprocess.run(ipSSHCommand, shell=True, capture_output=True, text=True)
            ipResult = subprocess.run(ipSSHCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
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
                    #result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
                    result = subprocess.run(find_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

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

        for metric, value in results.items():
            print(f"{metric}: {value}")

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



if args.prepare:
    print("preparing cluster")
    prepareCluster()
elif args.cluster:
    print("lauching cluster experiment")
    runCluster()

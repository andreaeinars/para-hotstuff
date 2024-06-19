import subprocess

# Define the base command and common parameters
base_local_command = "python3 expepriments.py --docker"
base_cluster_command = "python3 experiments_cluster.py --cluster"

# Define the experiments with their specific parameters
experiments_block_sizes = [
    {
        "description": "vs blocks 0pl 100tx",
        "protocol": "p3",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "1,4,8,16,32,64,128",
            "numTrans": "100",
            "payload": "0",
        }
    },
    {
        "description": "vs blocks 100 trans 128pl",
        "protocol": "p3",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "1,4,8,16,32,64,128",
            "numTrans": "100",
            "payload": "128",
        }
    },
        {
        "description": "vs blocks 0pl 400tx",
        "protocol": "p3",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "1,4,8,16,32,64,128",
            "numTrans": "400",
            "payload": "0",
        }
    },
    {
        "description": "vs blocks 400tx 128pl",
        "protocol": "p3",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "1,4,8,16,32,64,128",
            "numTrans": "400",
            "payload": "128",
        }
    },
]

experiments_faults_sizes = [
    {
        "description": "vs blocks 0pl 100tx",
        "protocol": "pall",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "8",
            "numTrans": "100",
            "payload": "0",
        }
    },
    {
        "description": "vs blocks 100 trans 128pl",
        "protocol": "pall",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "8",
            "numTrans": "100",
            "payload": "128",
        }
    },
        {
        "description": "vs blocks 256pl 100tx",
        "protocol": "pall",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "8",
            "numTrans": "100",
            "payload": "256",
        }
    },
]

experiments_byz = [
    {
        "description": "Normal",
        "protocol": "p3",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "payload":"128",
            "timeout": "5",
        }
    },
    {
        "description": "Byzantine smaller timeout", 
        "protocol": "p3",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "timeout": "1",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "byzantine":"1",
            "payload":"128",
        }
    },
    {
        "description": "Byzantine higher timeout",
        "protocol": "p3",
        "cmd": base_cluster_command,
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "timeout": "4",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "byzantine":"1",
            "payload":"128",
        }
    },

]

experiments_crash = [
    {
        "description": "xFaults",
        "protocol": "p3",
        "cmd": base_local_command,
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "5",
            "timeout": "5",
            "views": "100",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "30",
            "netvar": "30",
            "payload": "128",
            "crash":"0",
        }
    },
    {
        "description": "xFaults",
        "protocol": "p3",
        "cmd": base_local_command,
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "5",
            "timeout": "5",
            "views": "100",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "30",
            "netvar": "30",
            "payload": "128",
            "crash":"0.5",
        }
    },
    {
        "description": "SECOND",
        "protocol": "p3",
        "cmd": base_local_command,
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "5",
            "timeout": "5",
            "views": "100",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "30",
            "netvar": "30",
            "payload": "128",
            "crash":"1",
        }
    },
]

experiments_recover = [
      {
        "description": "RECOVER 0",
        "cmd": base_cluster_command,
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "payload": "128",
            "forceRecover": "0",
        }
    },
    {
        "description": "RECOVER 0.5",
        "cmd": base_cluster_command,
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "payload": "128",
            "forceRecover": "0.5",
        }
    },
    {
        "description": "RECOVER 1",
        "cmd": base_cluster_command,
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "payload": "128",
            "forceRecover": "1",
        }
    },
]

experiments_client = [
    {
        "description": "throughputxlat",
        "cmd": base_cluster_command,
        "protocol": "p2 --p3",
        "params": {
            "faults": "1",
            "repeats": "3",
            "numTrans": "100",
            "payload":"128",
            "maxBlocksInView": "8,16,32",
        }
    },
]

# Function to run an experiment
def run_experiment(description, protocol, params, cmd):
    command = cmd + f" --{protocol}"
    for param, value in params.items():
        command += f" --{param} {value}"
    print(f"Running {description} with command: {command}")
    subprocess.run(command, shell=True)

# Run all experiments sequentially
for experiment in experiments_block_sizes:
   run_experiment(experiment["description"], experiment["protocol"], experiment["params"], experiment["cmd"])

for experiment in experiments_faults_sizes:
    run_experiment(experiment["description"], experiment["protocol"], experiment["params"], experiment["cmd"])

for experiment in experiments_byz:
    run_experiment(experiment["description"], experiment["protocol"], experiment["params"], experiment["cmd"])

for experiment in experiments_crash:
    run_experiment(experiment["description"], experiment["protocol"], experiment["params"], experiment["cmd"])

for experiment in experiments_recover:
    run_experiment(experiment["description"], experiment["protocol"], experiment["params"], experiment["cmd"])

for experiment in experiments_client:
    run_experiment(experiment["description"], experiment["protocol"], experiment["params"], experiment["cmd"])

print("All experiments completed.")

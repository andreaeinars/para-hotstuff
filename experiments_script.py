# # # 3.
# maxBlocksInView = [1,2,4,8,16]
# repeats      = 3
# numViews     = 20
# payloadSize   = 0
# numTrans      = 400


# # # 4. 
# size_of_payload = [0,64,128, 256, 512]
# repeats      = 3
# numViews     = 20
# maxBlocksInView = [1,2,4,8]
# numTrans      = 400

import subprocess

# Define the base command and common parameters
base_command = "python3 exp_sing.py --cluster"

# Define the experiments with their specific parameters
experiments_control = [
    #  {
    #     "description": "100 trans",
    #     "protocol": "pall",
    #     "params": {
    #         "faults": "1,2,4,8,16",
    #         "repeats": "3",
    #         "views": "30",
    #         "maxBlocksInView": "1,4,8,16,32",
    #         "numTrans": "400",
    #         "netlat": "100",
    #         "netvar": "100",
    #         "dir": "usable_stats/exp-new/control-exp-faults",
    #     }
    # },
    {
        "description": "vs blocks 0pl 100tx",
        "protocol": "p3",
        "params": {
            "faults": "1",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "1,4,8,16,32,64,128",
            "numTrans": "100",
            "payload": "0",
            # "netlat": "100",
            # "netvar": "100",
            #"dir": "usable_stats/exp-new/control-exp-blocks-novar",
        }
    },
    {
        "description": "vs blocks 100 trans 128pl",
        "protocol": "p3",
        "params": {
            "faults": "1",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "1,4,8,16,32,64,128",
            "numTrans": "100",
            "payload": "128",
            # "netlat": "100",
            # "netvar": "100",
            #"numcltrans": "1",
            #"dir": "usable_stats/exp-new/control-exp-blocks-novar",
        }
    },
    #{
    #    "description": "vs blocks 255 payload 100tx",
    #    "protocol": "p3",
    #    "params": {
    #        "faults": "1",
    #        "repeats": "3",
    #        "views": "30",
    #        "maxBlocksInView": "1,4,8,16,32,64",
    #        "numTrans": "100",
            # "netlat": "100",
            # "netvar": "100",
     #       "payload": "256",
            #"numcltrans": "1",
            #"dir": "usable_stats/exp-new/control-exp-blocks-novar",
      #  }
    #},
        {
        "description": "vs blocks 0pl 400tx",
        "protocol": "p3",
        "params": {
            "faults": "1",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "1,4,8,16,32,64,128",
            "numTrans": "400",
            "payload": "0",
            # "netlat": "100",
            # "netvar": "100",
            #"dir": "usable_stats/exp-new/control-exp-blocks-novar",
        }
    },
    {
        "description": "vs blocks 400tx 128pl",
        "protocol": "p3",
        "params": {
            "faults": "1",
            "repeats": "5",
            "views": "30",
            "maxBlocksInView": "1,4,8,16,32,64,128",
            "numTrans": "400",
            "payload": "128",
            # "netlat": "100",
            # "netvar": "100",
            #"numcltrans": "1",
            #"dir": "usable_stats/exp-new/control-exp-blocks-novar",
        }
    },
]

experiments_sizes = [
    {
        "description": "vs blocks 0pl 100tx",
        "protocol": "p2 --p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "4",
            "views": "30",
            "maxBlocksInView": "8",
            "numTrans": "100",
            "payload": "0",
        }
    },
      {
        "description": "vs blocks 100 trans 64pl",
        "protocol": "p2 --p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "4",
            "views": "30",
            "maxBlocksInView": "8",
            "numTrans": "100",
            "payload": "64",
        }
    },
    {
        "description": "vs blocks 100 trans 128pl",
        "protocol": "p2 --p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "4",
            "views": "30",
            "maxBlocksInView": "8",
            "numTrans": "100",
            "payload": "128",
        }
    },
        {
        "description": "vs blocks 256pl 100tx",
        "protocol": "p2 --p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "4",
            "views": "30",
            "maxBlocksInView": "8",
            "numTrans": "100",
            "payload": "256",
        }
    },
]


experiments_delay = [
     {
        "description": "FIRST",
        "protocol": "pall",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "1,4,8,16,32",
            "numTrans": "400",
            "netlat": "100",
            "netvar": "400",
            "dir": "usable_stats/exp-new/delay-exp",
        }
    },
]
experiments_byz_2 = [
    {
        "description": "xBlocks",
        "protocol": "p3",
        "params": {
            "faults": "8,16",
            "repeats": "1",
            "views": "30",
            "maxBlocksInView": "4,16",
            "numTrans": "400",
            "byzantine":"1",
            "payload":"128",
            "timeout": "200",
        }
    },
]

experiments_byz = [
    {
        "description": "xBlocks",
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "4,16",
            "numTrans": "400",
            "byzantine":"1",
            "payload":"128",
            "timeout": "2",
        }
    },
    {
        "description": "xFaults",
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "timeout": "3",
            "maxBlocksInView": "4,16",
            "numTrans": "400",
            "byzantine":"1",
            "payload":"128",
        }
    },
    {
        "description": "xFaults",
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "3",
            "views": "30",
            "timeout": "4",
            "maxBlocksInView": "4,16",
            "numTrans": "400",
            "byzantine":"1",
            "payload":"128",
        }
    },

]

experiments_crash = [
    #  {
    #     "description": "xBlocks",
    #     "protocol": "p3",
    #     "params": {
    #         "faults": "1",
    #         "repeats": "3",
    #         "views": "30",
    #         "maxBlocksInView": "4,8,16,32,64",
    #         "numTrans": "400",
    #         "netlat": "100",
    #         "netvar": "100",
    #         "dir": "usable_stats/exp-new/crash-exp-blocks",
    #         "crash":"0.5",
    #     }
    # },
    {
        "description": "xFaults",
        "protocol": "p3",
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
            "dir": "usable_stats/exp-new/crash-exp-4",
            "crash":"0",
        }
    },
    {
        "description": "xFaults",
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "5",
            "views": "100",
            "timeout": "5",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "30",
            "netvar": "30",
            "payload": "128",
            "dir": "usable_stats/exp-new/crash-exp-4",
            "crash":"0.5",
        }
    },
    {
        "description": "SECOND",
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8,16",
            "repeats": "5",
            "views": "100",
            "timeout": "5",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "30",
            "netvar": "30",
            "payload": "128",
            "crash":"1",
            "dir": "usable_stats/exp-new/crash-exp-4",
        }
    }, # TODO: Finish crash experiments
]

experiments_recover = [
      {
        "description": "FIRST",
        "protocol": "p3",
        "params": {
            "faults": "4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "100",
            "netvar": "100",
            "forceRecover": "0",
            "dir": "usable_stats/exp-new/recover-exp",
        }
    },
    # {
    #     "description": "SECOND",
    #     "params": {
    #         "faults": "1,2,4,8",
    #         "repeats": "3",
    #         "views": "30",
    #         "maxBlocksInView": "16",
    #         "numTrans": "400",
    #         "netlat": "100",
    #         "netvar": "100",
    #         "forceRecover": "0.25",
    #         "dir": "usable_stats/recover-exp-lat-2",
    #     }
    # },
    {
        "description": "THIRD",
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "100",
            "netvar": "100",
            "forceRecover": "0.5",
            "dir": "usable_stats/exp-new/recover-exp",
        }
    },
    # {
    #     "description": "FOURTH",
    #     "params": {
    #         "faults": "1,2,4,8",
    #         "repeats": "3",
    #         "views": "30",
    #         "maxBlocksInView": "16",
    #         "numTrans": "400",
    #         "netlat": "100",
    #         "netvar": "100",
    #         "forceRecover": "0.75",
    #         "dir": "usable_stats/recover-exp-lat-2",
    #     }
    # },
    {
        "description": "FIFTH",
        "protocol": "p3",
        "params": {
            "faults": "1,2,4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "100",
            "netvar": "100",
            "forceRecover": "1",
            "dir": "usable_stats/exp-new/recover-exp",
        }
    },
]

experiments_client = [
    {
        "description": "throughputxlat",
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
def run_experiment(description, protocol, params):
    command = base_command + f" --{protocol}"
    for param, value in params.items():
        command += f" --{param} {value}"
    print(f"Running {description} with command: {command}")
    subprocess.run(command, shell=True)

# Run all experiments sequentially
#for experiment in experiments_control:
#    run_experiment(experiment["description"], experiment["protocol"], experiment["params"])
# for experiment in experiments_control:
#     run_experiment(experiment["description"], experiment["protocol"], experiment["params"])

# for experiment in experiments_delay:
#     run_experiment(experiment["description"], experiment["protocol"], experiment["params"])

for experiment in experiments_byz_2:
    run_experiment(experiment["description"], experiment["protocol"], experiment["params"])

for experiment in experiments_crash:
    run_experiment(experiment["description"], experiment["protocol"], experiment["params"])

# for experiment in experiments_recover:
#     run_experiment(experiment["description"], experiment["protocol"], experiment["params"])

# for experiment in experiments_client:
#     run_experiment(experiment["description"], experiment["protocol"], experiment["params"])

print("All experiments completed.")

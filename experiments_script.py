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
base_command = "python3 experiments.py --docker --p3"

# Define the experiments with their specific parameters
experiments_control = [
     {
        "description": "FIRST",
        "params": {
            "faults": "1,2,4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16,32",
            "numTrans": "400",
            "netlat": "100",
            "netvar": "100",
            "dir": "usable_stats/control-exp",
        }
    },
    {
        "description": "FIRST",
        "params": {
            "faults": "1,2,4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16,32",
            "numTrans": "400",
            "netlat": "100",
            "netvar": "100",
            "dir": "usable_stats/control-exp",
        }
    },
]

experiments_crash = [
     {
        "description": "FIRST",
        "params": {
            "faults": "1,2,4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "8,16",
            "numTrans": "400",
            # "netlat": "100",
            # "netvar": "100",
            "dir": "usable_stats/crash-exp",
            "crash":"0.5",
        }
    },
    {
        "description": "SECOND",
        "params": {
            "faults": "1,2,4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "8,16",
            "numTrans": "400",
            # "netlat": "100",
            # "netvar": "100",
            "dir": "usable_stats/crash-exp",
            "crash":"1",
        }
    },
    {
        "description": "SECOND",
        "params": {
            "faults": "1,2,4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "8,16",
            "numTrans": "400",
            # "netlat": "100",
            # "netvar": "100",
            "dir": "usable_stats/crash-exp",
        }
    },
]

experiments_recover = [
    #   {
    #     "description": "FIRST",
    #     "params": {
    #         "faults": "4,8",
    #         "repeats": "3",
    #         "views": "30",
    #         "maxBlocksInView": "16",
    #         "numTrans": "400",
    #         # "netlat": "100",
    #         # "netvar": "100",
    #         "forceRecover": "1",
    #         "dir": "usable_stats/recover-exp",
    #     }
    # },
    #  {
    #     "description": "FIRST",
    #     "params": {
    #         "faults": "1,2,4,8",
    #         "repeats": "3",
    #         "views": "30",
    #         "maxBlocksInView": "16",
    #         "numTrans": "400",
    #         "netlat": "100",
    #         "netvar": "100",
    #         "forceRecover": "0",
    #         "dir": "usable_stats/recover-exp-lat-2",
    #     }
    # },
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
        "params": {
            "faults": "1,2,4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "100",
            "netvar": "100",
            "forceRecover": "0.5",
            "dir": "usable_stats/recover-exp-lat-2",
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
        "params": {
            "faults": "1,2,4,8",
            "repeats": "3",
            "views": "30",
            "maxBlocksInView": "16",
            "numTrans": "400",
            "netlat": "100",
            "netvar": "100",
            "forceRecover": "1",
            "dir": "usable_stats/recover-exp-lat-2",
        }
    },
]

# Define the experiments with their specific parameters
experiments_vsblocks_lat = [
     {
        "description": "FIRST",
        "params": {
            "faults": "1",
            "repeats": "3",
            "views": "20",
            "maxBlocksInView": "1,2,5,10,15,20,25,30,40",
            "netlat": "100",
            "netvar": "250",
            "numTrans": "100",
            "dir": "usable_stats/vsblocks_lat_2",
        }
    },
    {
        "description": "SECOND",
        "params": {
            "faults": "1",
            "repeats": "3",
            "views": "20",
            "maxBlocksInView": "1,2,5,10,15,20,25,30,40",
            "numTrans": "100",
            "netlat": "100",
            "netvar": "250",
            "numTrans": "400",
            "dir": "usable_stats/vsblocks_lat_2",
        }
    },
    {
        "description": "THIRD",
        "params": {
            "faults": "1",
            "repeats": "3",
            "views": "20",
            "maxBlocksInView": "1,2,5,10,15,20,25,30,40",
            "numTrans": "100",
            "netlat": "100",
            "netvar": "250",
            "payload": "128",
            "dir": "usable_stats/vsblocks_lat_2",
        }
    },
    {
        "description": "FOURTH",
        "params": {
            "faults": "1",
            "repeats": "3",
            "views": "20",
            "maxBlocksInView": "1,2,5,10,15,20,25,30,40",
            "numTrans": "100",
            "netlat": "100",
            "netvar": "250",
            "payload": "256",
            "dir": "usable_stats/vsblocks_lat_2",
        }
    },
]
# Define the experiments with their specific parameters
experiments_vsblocks = [
    #  {
    #     "description": "FIRST",
    #     "params": {
    #         "faults": "1",
    #         "repeats": "6",
    #         "views": "20",
    #         "maxBlocksInView": "1,2,5,10,15,20,25,30,40",
    #         "numTrans": "100",
    #         "dir": "usable_stats/vsblocks",
    #     }
    # },
    # {
    #     "description": "SECOND",
    #     "params": {
    #         "faults": "1",
    #         "repeats": "6",
    #         "views": "20",
    #         "maxBlocksInView": "1,2,5,10,15,20,25,30,40",
    #         "numTrans": "100",
    #         "netlat": "10",
    #         "netvar": "150",
    #         "dir": "usable_stats/vsblocks",
    #     }
    # },
    # {
    #     "description": "THIRD",
    #     "params": {
    #         "faults": "1",
    #         "repeats": "6",
    #         "views": "20",
    #         "maxBlocksInView": "1,2,5,10,15,20,25,30,40",
    #         "numTrans": "400",
    #         "dir": "usable_stats/vsblocks",
    #     }
    # },
    {
        "description": "FOURTH",
        "params": {
            "faults": "1",
            "repeats": "6",
            "views": "20",
            "maxBlocksInView": "1,2,5,10,15,20,25,30,40",
            "numTrans": "100",
            "payload": "128",
            "dir": "usable_stats/vsblocks",
        }
    }
]


# Define the experiments with their specific parameters
# experiments_recover = [
#      {
#         "description": "FIRST",
#         "params": {
#             "faults": "1,2,4,8,16",
#             "repeats": "3",
#             "views": "30",
#             "netlat": "100",
#             "netvar": "100",
#             "maxBlocksInView": "16",
#             "numTrans": "400",
#             "dir": "usable_stats/control-exp",
#         }
#     },
# ]


# Function to run an experiment
def run_experiment(description, params):
    command = base_command
    for param, value in params.items():
        command += f" --{param} {value}"
    print(f"Running {description} with command: {command}")
    subprocess.run(command, shell=True)

# Run all experiments sequentially
for experiment in experiments_crash:
    run_experiment(experiment["description"], experiment["params"])

print("All experiments completed.")

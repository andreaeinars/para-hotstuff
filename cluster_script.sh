#!/bin/bash
#SBATCH --job-name=para-hs
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --time=00:15:00

module load python/3.6.0 docker/1.13.1 git/1.8.3.1

# Navigate to your script's directory
cd /home/aeinarsd/

# Execute 
srun  python3 experiments.py --cluster --p1 --repeats 1 --faults 1 --views 5
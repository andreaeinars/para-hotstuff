#!/bin/bash
#SBATCH --job-name=para-hs
#SBATCH --nodes=5
#SBATCH --ntasks-per-node=1
#SBATCH --time=00:15:00

module load python/3.6.0

# Navigate to your script's directory
cd /home/aeinarsd/var/scratch/aeinarsd/para-hotstuff/

# Execute 
python3 exp_sing.py --cluster --p1 --repeats 1 --faults 1 --views 5

#!/usr/bin/env python2

#$ -S /usr/bin/python
#$ -l mem_free=1G
#$ -l arch=linux-x64
#$ -l netapp=1G
#$ -l h_core=0
#$ -cwd

import os, sys; sys.path.append(sys.argv[1])
import subprocess
from libraries import big_job

workspace, job_id, task_id, parameters = big_job.initiate()

bb_models = parameters['inputs']
bb_model = bb_models[task_id % len(bb_models)]
design_id = task_id // len(bb_models)

rosetta_command = [
        workspace.rosetta_scripts_path,
        '-database', workspace.rosetta_database_path,
        '-in:file:s', bb_model,
        '-in:file:native', workspace.input_pdb_path,
        '-out:prefix', workspace.output_dir + '/',
        '-out:suffix', '_{0:03}'.format(design_id),
        '-out:no_nstruct_label',
        '-out:overwrite',
        '-out:pdb_gz', 
        '-parser:protocol', workspace.design_script_path,
        '-parser:script_vars',
            'shared_defs=' + big_job.shared_defs_path,
            'wts_file=' + workspace.scorefxn_path,
            'cst_file=' + workspace.restraints_path,
        '-packing:resfile', workspace.resfile_path,
        '@', workspace.flags_path,
]
print ' '.join(rosetta_command)
subprocess.call(rosetta_command)

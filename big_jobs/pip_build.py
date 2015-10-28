#!/usr/bin/env python2

#$ -S /usr/bin/python
#$ -l mem_free=1G
#$ -l arch=linux-x64
#$ -l netapp=1G
#$ -cwd

import os, sys; sys.path.append(os.getcwd())
import subprocess
from libraries import big_job

workspace, job_id, task_id, parameters = big_job.initiate()
output_prefix = '{0}/{1}_{2:06d}_'.format(workspace.output_dir, job_id, task_id)
test_run = parameters.get('test_run', False)

rosetta_command = [
        workspace.rosetta_scripts_path,
        '-database', workspace.rosetta_database_path,
        '-in:file:s', workspace.input_pdb_path,
        '-in:file:native', workspace.input_pdb_path,
        '-out:prefix', output_prefix,
        '-out:no_nstruct_label',
        '-out:overwrite',
        '-out:pdb_gz', 
        '-out:mute', 'protocols.loops.loops_main',
        '-parser:protocol', workspace.build_script_path,
        '-parser:script_vars',
            'shared_defs=' + big_jobs.shared_defs_path,
            'wts_file=' + workspace.scorefxn_path,
            'cst_file=' + workspace.restraints_path,
            'loop_file=' + workspace.loops_path,
            'fast=' + ('yes' if test_run else 'no'),
        '-packing:resfile', workspace.resfile_path,
] +     workspace.fragments_flags(workspace.input_pdb_path) + [
        '@', workspace.flags_path,
]

subprocess.call(rosetta_command)

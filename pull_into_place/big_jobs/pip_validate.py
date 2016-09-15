#!/usr/bin/env python2

#$ -S /usr/bin/python
#$ -l mem_free=1G
#$ -l arch=linux-x64
#$ -l netapp=1G
#$ -cwd

import os, sys, subprocess
from pull_into_place import big_jobs

workspace, job_id, task_id, parameters = big_jobs.initiate()

designs = parameters['inputs']
input_path = designs[task_id % len(designs)]
output_subdir = workspace.output_subdir(input_path)
test_run = parameters.get('test_run', False)

big_jobs.print_debug_info()
big_jobs.run_command([
        workspace.rosetta_scripts_path,
        '-database', workspace.rosetta_database_path,
        '-in:file:s', input_path,
        '-in:file:native', workspace.input_pdb_path,
        '-out:prefix', output_subdir + '/',
        '-out:suffix', '_{0:03d}'.format(task_id / len(designs)),
        '-out:no_nstruct_label',
        '-out:overwrite',
        '-out:pdb_gz', 
        '-out:mute', 'protocols.loops.loops_main',
        '-parser:protocol', workspace.validate_script_path,
        '-parser:script_vars',
            'shared_defs=' + big_jobs.shared_defs_path,
            'wts_file=' + workspace.scorefxn_path,
            'loop_file=' + workspace.loops_path,
            'fast=' + ('yes' if test_run else 'no')
] +     workspace.fragments_flags(input_path) + [
        '@', workspace.flags_path,
])
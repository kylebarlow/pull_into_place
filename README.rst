Introduction
============
Pull Into Place (PIP) is a protocol to design protein functional groups with 
sub-angstrom accuracy.  The protocol is based on two ideas: 1) using restraints 
to define the geometry you're trying to design and 2) using an unrestrained 
simulations to test designs.  In particular, the design pipeline used by PIP
has the following steps:

0. Define your project.  This entails creating an input PDB file and preparing 
   it for use with rosetta, creating a restraints file that specifies your 
   desired geometry, creating a resfile that specifies which residues are 
   allowed to design, and creating a loop file that specifies where backbone 
   flexibility will be considered.

   $ pull_into_place 01_setup_workspace ...
   $ pull_into_place 02_setup_model_fragments ...

1. Build a large number of models that plausibly support your desired geometry 
   by running flexible backbone Monte Carlo simulations restrained to stay near 
   said geometry.  The goal is to find a balance between finding models that 
   are realistic and that satisfy your restraints.

   $ pull_into_place 03_build_models ...

2. Filter out models that don't meet your quality criteria.

   $ pull_into_place 04_pick_models_to_design ...

3. Generate a number of designs for each model remaining.

   $ pull_into_place 05_design_models ...

4. Pick a small number of designs to validate.  Typically I generate 100,000 
   designs and can only validate 50-100.  I've found that randomly picking 
   designs according to the Boltzmann weight of their rosetta score gives a 
   nice mix of designs that are good but not too homogeneous.

   $ pull_into_place 06_pick_designs_to_validate ...

5. Validate the designs using unrestrained Monte Carlo simulations.  Designs 
   that are "successful" will have a funnel on the left side of their score vs 
   rmsd plots.

   $ pull_into_place 07_setup_design_fragments ...
   $ pull_into_place 08_validate_designs ...

6. Optionally take the decoys with the best geometry from the validation run 
   (even if they didn't score well) and feed them back into step 3.  Second and 
   third rounds of simulation usually produce much better results than the 
   first, because the models being designed are more realistic.  Additional 
   rounds of simulation give diminishing returns, and may be more effected by 
   some of rosetta's pathologies (i.e. it's preference for aromatic residues).

   $ pull_into_place 04_pick_models_to_design ...
   $ pull_into_place 05_design_models ...
   $ pull_into_place 06_pick_designs_to_validate ...
   $ pull_into_place 07_setup_design_fragments ...
   $ pull_into_place 08_validate_designs ...

7. Generate a report summarizing a variety of quality metrics for each design.  
   This report is meant to help you pick designs to test experimentally.

   $ pull_into_place 09_compare_best_designs ...

Usage
=====
This repository contains a set of scripts that make it easy to perform each of 
these steps described above.  The core scripts responsible for carrying out the 
pipeline are all stored in the root of the repository and are numbered in the 
order they're meant to be run in.  Note that some of these scripts must be run 
on the cluster.  Also in the root directory is the view_models.py script, which 
is useful for visualizing results at almost every stage of the pipeline.

The scripts/ subdirectory contains other assorted scripts that are useful, but 
not central to the pipeline.  For example, this includes scripts to send data 
to and from the cluster, to work with some of the intermediate file formats 
used by the core scripts, and other things like that.

Each script will give a description of what it does and how it is supposed to 
be used if you pass it the '-h' or '--help' flags.  In general, the first 
argument to each script is the path to the directory containing all of the data 
for a particular design.  This directory is created by 01_setup_pipeline.py and 
is referred to as the "name" of the design.  Several of the scripts also take a 
round number as a second argument.

There is limited support for running several jobs on the cluster at once.  For 
eaxmple, while one job is running you can launch another job of the same type 
on new input files.  This works because running jobs will ignore any new files 
you add to a job's input directory, and newly launched jobs will ignore input 
file that have already been used by other jobs (running or not).

Trouble-shooting
================
In the event that something doesn't work or you need to add a feature, it's 
good to have a general sense for how the code is organized.  Code that is 
general to any project being developed by the lab is stored in the tools/ 
subdirectory.  Code that is general within this project but not useful outside 
of it is stored in the libraries/ directory.  Below are brief descriptions of 
the modules used the most in this pipeline:

libraries.pipeline:
    This module defines the Workspace classes that are central to every script.  
    The role of these classes is to provide paths to all the data files used in 
    any part of the pipeline and to hide the organization of the directories 
    containing those files.  The base Workspace class deals with files in the 
    root directory of a design.  It subclasses deal with file in the different 
    subdirectories of the design, each of which is related to a cluster job.

libraries.structures:
    This module provides a function that will read a directory of PDB files and 
    return a pandas.DataFrame containing a number of score, distance, and 
    sequence metrics for each structure.  This information is also cached, 
    because it takes a while to calculate up front.  Note that the cache files 
    are pickles and seem to depend very closely on the version of pandas used 
    to generate them.  For example, caches generated with pandas 0.15 can't be 
    read by pandas 0.14.

libraries.big_jobs:
    This module provides a simple wrapper around the cluster submission 
    process.  This makes it easy to both submit jobs to the queue and to 
    configure jobs once they come off the queue and onto a node.

tools.scripting:
    This module provides a handful of simple functions that just make scripting 
    more convenient.  Many of these are basically just implementations of the  
    standard shell commands.

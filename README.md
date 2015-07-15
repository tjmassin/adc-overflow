# adc-overflow
This code base is used to search for ADC/DAC overflows in LIGO instruments.
Developed by TJ Massinger for use in the LVC.

The purpose of this code is to generate an appropriate set of condor dag and sub files to search for ADC/DAC overflows and generate sngl_burst XML files containing triggers. The generated DAG will call the executable <b>gen_overflow_trigs.sh</b>, which is a wrapper around the python script <b>gen_single_channel_trigs.py</b>.

Instructions for running on an LDAS cluster:

##### 1. Source GWpy user environment

##### 2. Update (or checkout) the cds_user_apps SVN that contains the simulink models that run in the front end and monitor saturation events.

##### 3. Run find_models.sh 

This script will generate an annotated list of models running on the current system. 

This will parse the .adl file for each model, extract its ndcuid, and annotate the model as either a cumulative overflow channel or a non-cumulative overflow channel.

Syntax: 
> ./find_models.sh {user_apps directory} {output directory} {H1,L1}

Example call: 
> ./find_models.sh /home/tjmassin/svn/cds_user_apps/ /home/tjmassin/adc_overflow/test/model_info/ H1

##### 4. Run gen_overflows_condor.sh 

This script will go through the entire process of generating an appropriate condor DAG that should be submit-ready. It will generate a directory structure containing log files and executables in the designated output directory.

Syntax:
> ./gen_overflows_condor.sh {start_gps} {end_gps} {L,H} {output directory}

Example call:

> ./gen_overflows_condor.sh 1118019595 1118019795 H /home/tjmassin/adc_overflow/test


The process is as follows:

a. Set up a directory structure to store all information regarding models and overflow channels, as well as condor log files.

b. Grab model-wide cumulative overflow channels to see if any channel in a given model has overflowed during the time period of interest. This is done using <b>plot_overflow_accum.py</b>.

c. Generate a list of models that have at least one overflow.

d. Generate a list of channels contained in those models and mark them for further follow-up.

e. Generate condor DAG and sub files that allow the search code to farm the computation out channel-by-channel.

f. Copy over the search executables to the condor run directory and create log file directory.







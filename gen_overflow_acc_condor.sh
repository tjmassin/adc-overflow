#!/bin/bash

start_time=$1
end_time=$2
ifo=$3
outdir=$4
trigger_dir=$5
seg_list=$6
padding=$7

basedir="${outdir}/${start_time}_${end_time}"

echo "Building directory structure at ${basedir}"

mkdir -p ${basedir}
mkdir -p ${basedir}/condor_dag
mkdir -p ${basedir}/condor_dag/log_${start_time}_ADC

source /home/detchar/opt/gwpysoft/etc/gwpy-user-env.sh

# find minute-trend frames and generate list of model-wide overflow channels
frame=`gw_data_find -n -o ${ifo} -t ${ifo}1_M -s ${start_time} -e ${start_time} |grep 'archive' | head -n 1`
chan_list="all_model_overflow_chans_${start_time}_${end_time}.txt"

FECchannels="all_FEC_channels_minute_trend_${start_time}_${end_time}.txt"

FrChannels ${frame} | grep 'FEC' > ${basedir}/${FECchannels}

cat ${basedir}/${FECchannels} | grep 'ACCUM_OVERFLOW' | grep 'max' | cut -d ' ' -f 1 > ${basedir}/${chan_list}

echo "Wrote channel list to file ${chan_list}"



# find list of models that have an overflowing channel in them
overflow_chans="overflowing_model_chans_${start_time}_${end_time}.txt"

echo "Calculating which models have at least one overflow channel"

python plot_overflow_accum.py -s ${start_time} -e ${end_time} -c ${basedir}/${chan_list} -o ${basedir}/${overflow_chans} -i ${ifo} -l ${seg_list} -p ${padding}

if [ ! -s ${basedir}/${overflow_chans} ]; then
	echo "No overflowing models found! Exiting script"
	exit 0
fi

echo "Wrote list of model overflow channels to file ${overflow_chans}"



# generate list of overflowing models by ndcuid
overflow_ndcuid="overflowing_ndcuid_${start_time}_${end_time}.txt"

while read line; do
	ndcuid_tag=`echo ${line:2} | grep -Eo '[0-9]{1,3}'`
	echo ${ndcuid_tag}
	unset ndcuid_tag
done < ${basedir}/${overflow_chans} > ${basedir}/${overflow_ndcuid}

echo "Wrote ndcuid values of overflowing models to file ${overflow_ndcuid} "



# generate list of individual ADC/DAC channels included in overflowing models
followup_list="individual_overflow_chans_${start_time}_${end_time}.txt"

rawframe=`gw_data_find -n -o ${ifo} -t ${ifo}1_R -s ${start_time} -e ${start_time} | head -n 1`

rawFECchans="all_FEC_channels_raw_${start_time}_${end_time}.txt"

FrChannels ${rawframe} | grep 'FEC' > ${basedir}/${rawFECchans}

while read i; do
	cat ${basedir}/${rawFECchans} | grep -E 'ADC_OVERFLOW_ACC_[0-9]' | grep "C-${i}_"
	cat ${basedir}/${rawFECchans} | grep -E 'DAC_OVERFLOW_ACC_[0-9]' | grep "C-${i}_"
done < ${basedir}/${overflow_ndcuid} | cut -d ' ' -f 1 > ${basedir}/${followup_list}



# generate condor DAG and submit files
numchans=`wc -l ${basedir}/${followup_list} | cut -d ' ' -f 1`

python make_dag_ADC.py ${numchans} ${start_time} ${end_time} ${basedir}

python make_sub_ADC.py ${basedir} ${basedir}/${followup_list} ${ifo} ${trigger_dir} ${seg_list} ${padding} ${start_time} ${end_time}

cp gen_overflow_acc_trigs.sh ${basedir}/condor_dag/gen_overflow_acc_trigs.sh
cp gen_single_channel_acc_trigs.py ${basedir}/condor_dag/gen_single_channel_acc_trigs.py

echo "Created DAG and submit files in condor_dag directory"

#condor_submit_dag ${basedir}/condor_dag/ADC_${start_time}_${end_time}.dag

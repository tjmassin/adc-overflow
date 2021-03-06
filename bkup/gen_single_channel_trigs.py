from numpy import *
from glue.ligolw import utils, ligolw, lsctables
from glue.lal import LIGOTimeGPS
from glue import lal
from glue import segments as seg
import os
from optparse import OptionParser
from gwpy.timeseries import TimeSeries
from glue import datafind

parser = OptionParser(
	version = "Name: Overflow Trigger Generator",
	usage       = "%prog --gps-start-time --gps-end-time --channel ",
	description = "Makes triggers for overflows from a single channel"
        )

parser.add_option("-s", "--gps-start-time", metavar = "gps_start_time", help = "Start of GPS time range")

parser.add_option("-e", "--gps-end-time",   metavar = "gps_end_time", help = "End of GPS time range")

parser.add_option("-c", "--channel", metavar = "channel", help="Channel name.")

args, others = parser.parse_args()

channel = args.channel
gps_start = int(args.gps_start_time)
gps_end   = int(args.gps_end_time)
ifo = 'H'
frames = 'H1_R'

# generate frame cache and connection
connection = datafind.GWDataFindHTTPConnection()
cache = connection.find_frame_urls(ifo, frames, gps_start, gps_end, urltype='file')

# read in master list that contains ADC model numbers, names, and cumulative status
model_list = []
model_read = open("/home/tjmassin/adc_overflow_condor/master/h1_model_info.txt")
for line in model_read.readlines():
	model_list.append(map(str,line.split()))
	
# pick off ndcuid list to enable direct searching of channels for overflow status
ndcuid_list = []
for item in model_list:
	ndcuid_list.append(item[2])

# functions to find the start of overflow segments
# if x and y are equal in value and z jumps, we'll pull off the timestamp attached to z
# and record that as the beginning of a segment
def startCumuSegTest(x,y,z):
	if (x == y < z):
		return True
	else:
		return False

# for non-cumulative overflows, we mark every time we see a change in channel value
# from here we will create one-second segments every time we see a change and then perform
# a coalesce at the end to find the overall start/end points of overflowing times
def startSegTest(x,y,z):
	if (x == y != z) and (z != 0):
		return True
	else:
		return False

# check if an overflow channel is cumulative by crosschecking ndcuid_list and model_list
# model list lines are recorded as <model_name.mdl> <cumulative status> <ndcuid=num>
def checkCumulative(chan_name,model_list,ndcuid_list):
	ID = 'ndcuid=' + str(chan_name)[str(chan_name).find('-')+1:str(chan_name).find('_')]
	if (model_list[ndcuid_list.index(ID)][1] == 'cumulative'):
		return True
	else:
		return False
		

data=TimeSeries.read(cache, channel, start=gps_start, end=gps_end)

time_vec = linspace(gps_start,gps_end,(gps_end - gps_start)*16,endpoint=False)


'''

We are interested in times when the channels switch from a normal state to an overflowing
state or vice versa. We're not checking the first and last data point of each set because it's not 
possible to tell whether or not a channel has just started overflowing at our first data
point or if it had been overflowing beforehand. 

This big loop will test every data point (that isn't an endpoint) and record it in the
trigger vector  if it's an overflow transition.

'''

trig_segs = seg.segmentlist()

if checkCumulative(channel,model_list,ndcuid_list):
	for j in arange(size(data,0)):
		if (0 < j < (size(data,0) - 1)):
			if startCumuSegTest(data[j-1],data[j],data[j+1]):
				trig_segs |= seg.segmentlist([seg.segment(time_vec[j+1],time_vec[j+1]+1)])
else:
	for j in arange(size(data,0)):
		if (0 < j < (size(data,0) - 1)):
			if startSegTest(data[j-1],data[j],data[j+1]):
				trig_segs |= seg.segmentlist([seg.segment(time_vec[j+1],time_vec[j+1]+1)])
						

trig_segs = trig_segs.coalesce()

if (size(trig_segs) == 0):
	print "No triggers found for " + str(channel)
	exit()	
else:
	print "Found triggers for " + str(channel)
	
	
# make vectors of up and down transitions and feed into XML output
up_trigger_vec = []	
for i in arange(size(trig_segs,0)):
	up_trigger_vec.append(trig_segs[i][0] - 0.5)
	
down_trigger_vec = []
for i in arange(size(trig_segs,0)):
	down_trigger_vec.append(trig_segs[i][1] - 0.5)


# map triggers into float type and then convert them all into LIGOTimeGPS notation
up_trig_times = map(LIGOTimeGPS,map(float,up_trigger_vec))
down_trig_times = map(LIGOTimeGPS,map(float,down_trigger_vec))

# create mocked up frequency and SNR vectors to fill in XML tables
freqs = empty(size(up_trigger_vec))
freqs.fill(100)
snrs = empty(size(up_trigger_vec))
snrs.fill(10)


sngl_burst_table_up = lsctables.New(lsctables.SnglBurstTable, ["peak_time", "peak_time_ns","peak_frequency","snr"])
sngl_burst_table_down = lsctables.New(lsctables.SnglBurstTable, ["peak_time", "peak_time_ns","peak_frequency","snr"])


for t,f,s in zip(up_trig_times, freqs, snrs):
	row = sngl_burst_table_up.RowType()
	row.set_peak(t)
	row.peak_frequency = f
	row.snr = s
	sngl_burst_table_up.append(row)
	
for t,f,s in zip(down_trig_times, freqs, snrs):
	row = sngl_burst_table_down.RowType()
	row.set_peak(t)
	row.peak_frequency = f
	row.snr = s
	sngl_burst_table_down.append(row)


xmldoc_up = ligolw.Document()
xmldoc_up.appendChild(ligolw.LIGO_LW())
xmldoc_up.childNodes[0].appendChild(sngl_burst_table_up)

xmldoc_down = ligolw.Document()
xmldoc_down.appendChild(ligolw.LIGO_LW())
xmldoc_down.childNodes[0].appendChild(sngl_burst_table_down)

directory_up = ("/home/tjmassin/triggers/POSTER5/" + channel[:2] + "/" + 
channel[3:] + "_UP/" + str(gps_start)[:5] + "/")

directory_down = ("/home/tjmassin/triggers/POSTER5/" + channel[:2] + "/" + 
channel[3:] + "_DOWN/" + str(gps_start)[:5] + "/")

if not os.path.exists(directory_up):
	os.makedirs(directory_up)
	
if not os.path.exists(directory_down):
	os.makedirs(directory_down)

utils.write_filename(xmldoc_up, directory_up + channel[:2] + "-" + channel[3:6] +
"_" + channel[7:] + "_UP_ADC-" + str(gps_start) + "-" + str(gps_end - gps_start) + 
".xml.gz", gz=True)

utils.write_filename(xmldoc_down, directory_down + channel[:2] + "-" + channel[3:6] +
"_" + channel[7:] + "_DOWN_ADC-" + str(gps_start) + "-" + str(gps_end - gps_start) + 
".xml.gz", gz=True)

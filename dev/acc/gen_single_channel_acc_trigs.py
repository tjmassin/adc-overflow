import numpy as np
from glue.ligolw import utils, ligolw, lsctables
from glue.lal import LIGOTimeGPS
from glue import lal
from glue import segments as seg
import os
from optparse import OptionParser
from gwpy.timeseries import TimeSeries
from glue import datafind

def read_command_line():
    parser = OptionParser(
        version = "Name: Overflow Trigger Generator",
        usage       = "%prog --gps-start-time --gps-end-time --channel --ifo --outdir --seg-list",
        description = "Makes triggers for overflows from a single channel"
            )

    parser.add_option("-s", "--gps-start-time", metavar = "gps_start_time", help = "Start of GPS time range")

    parser.add_option("-e", "--gps-end-time",   metavar = "gps_end_time", help = "End of GPS time range")

    parser.add_option("-c", "--channel", metavar = "channel", help="Channel name.")

    parser.add_option("-i", "--ifo", metavar = "ifo", help="IFO, L or H")

    parser.add_option("-o", "--outdir", metavar = "outdir", help = "base output directory")

    parser.add_option("-l", "--seg-list", metavar = "seg_list", help = "list of segments")

    args, others = parser.parse_args()

    channel = args.channel
    gps_start = int(args.gps_start_time)
    gps_end   = int(args.gps_end_time)
    ifo = args.ifo
    outdir = args.outdir
    seg_list = args.seg_list
    #sanitize IFO input

    if ifo == 'L1':
        ifo = 'L'

    if ifo == 'H1':
        ifo = 'H'

    if ifo == 'L':
        frames = 'L1_R'
    else:
        frames = 'H1_R'

    segments = np.loadtxt(seg_list,dtype=str)

    return channel, gps_start, gps_end, ifo, frames, outdir, segments


# functions to find the start of overflow segments
# if x and y are equal in value and z jumps, we'll pull off the timestamp attached to z
# and record that as the beginning of a segment
def cumu_seg_test(x,y,z):
    if (x == y < z):
        return True
    else:
        return False


def generate_triggers(channel,gps_start,gps_end,ifo,frames,outdir,segments):
    print "Processing segment: " + str(gps_start) + " - " + str(gps_end)
    # generate frame cache and connection
    connection = datafind.GWDataFindHTTPConnection()
    cache = connection.find_frame_urls(ifo, frames, int(gps_start), int(gps_end), urltype='file')
    data=TimeSeries.read(cache, channel, start=int(gps_start), end=int(gps_end))

    time_vec=data.times.value


    '''

    We are interested in times when the channels switch from a normal state to an overflowing
    state or vice versa. We're not checking the first and last data point of each set because it's not 
    possible to tell whether or not a channel has just started overflowing at our first data
    point or if it had been overflowing beforehand. 

    This big loop will test every data point (that isn't an endpoint) and record it in the
    trigger vector  if it's an overflow transition.

    '''

#    trig_segs = seg.segmentlist()
#
#    for j in np.arange(np.size(data,0)):
#        if (0 < j < (np.size(data,0) - 1)):
#            if cumu_seg_test(data[j-1],data[j],data[j+1]):
#                trig_segs |= seg.segmentlist([seg.segment(time_vec[j+1],time_vec[j+1]+1)])
#
#    trig_segs = trig_segs.coalesce()

    trigger_vec = []
    for j in np.arange(np.size(data,0)):
        if (0 < j < (np.size(data,0) - 1)):
            if cumu_seg_test(data[j-1],data[j],data[j+1]):
                trigger_vec.append(time_vec[j+1])


    if (np.size(trig_segs) == 0):
        print "No triggers found for " + str(channel)
        return
    else:
        print "Found triggers for " + str(channel)
        
    # map triggers into float type and then convert them all into LIGOTimeGPS notation
    trig_times = map(LIGOTimeGPS,map(float,trigger_vec))

    # create mocked up frequency and SNR vectors to fill in XML tables
    freqs = np.empty(np.size(trigger_vec))
    freqs.fill(100)
    snrs = np.empty(np.size(trigger_vec))
    snrs.fill(10)


    sngl_burst_table_up = lsctables.New(lsctables.SnglBurstTable, ["peak_time", "peak_time_ns","peak_frequency","snr"])

    for t,f,s in zip(trig_times, freqs, snrs):
        row = sngl_burst_table_up.RowType()
        row.set_peak(t)
        row.peak_frequency = f
        row.snr = s
        sngl_burst_table_up.append(row)
        

    xmldoc_up = ligolw.Document()
    xmldoc_up.appendChild(ligolw.LIGO_LW())
    xmldoc_up.childNodes[0].appendChild(sngl_burst_table_up)

    directory_up = (outdir + '/' + channel[:2] + "/" + 
    channel[3:] + "_UP/" + str(gps_start)[:5] + "/")

    if not os.path.exists(directory_up):
        os.makedirs(directory_up)
        
    utils.write_filename(xmldoc_up, directory_up + channel[:2] + "-" + channel[3:6] +
    "_" + channel[7:] + "_UP_ADC-" + str(gps_start) + "-" + str(gps_end - gps_start) + 
    ".xml.gz", gz=True)


if __name__=="__main__":
    read_command_line()
    channel,gps_start,gps_end,ifo,frames,outdir,segments = read_command_line()
    for entry in segments:
        generate_triggers(channel,entry[0],entry[1],ifo,frames,outdir,segments)

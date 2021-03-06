import sys

basedir=str(sys.argv[1])
st=str(sys.argv[2])
et=str(sys.argv[3])
chan_list=str(sys.argv[4])

subname = basedir + "/condor_dag/ADC_" + st + "_" + et + ".sub"

fP=open(subname,'w')

print >> fP,"Executable = gen_overflow_trigs.sh"
print >> fP,"Universe = vanilla"
print >> fP,"Arguments = $(macrojobnumber) %s %s %s" % (st,et,chan_list)
print >> fP,"Error = log_%s_ADC/err.$(macrojobnumber)" %(st)
print >> fP,"Output = log_%s_ADC/out.$(macrojobnumber)" %(st)
print >> fP,"Log = log_%s_ADC/log.$(macrojobnumber)" %(st)
print >> fP,"Notification = never"
print >> fP,"getenv=true"
print >> fP,"Queue 1"

fP.close()



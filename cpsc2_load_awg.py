import epics
import numpy as np
import argparse
import time

"""
awg04 = epics.PV('cpsc2_003:AO:AWG:04:V')
tt = np.arange(0,2048,dtype=float)
sin=1*np.sin(tt/2048*2*np.pi)
awg04.put(sin)
"""


def stop_awg(args):
    print("prepare_awg() {}".format(args.uut))
    active = epics.PV('{}:2:AWG:ACTIVE'.format(args.uut))
    if active.get():
        abort = epics.PV('{}:2:AWG:MODE:ABO'.format(args.uut))
	abort.put(1)
	while active.get():
            print("polling for complete")
	    time.sleep(0.1)

        abort.put(0)

def prepare_awg(args):
    stop_awg(args)
    for ch in ( 'A', 'B' ):
        epics.PV('{}:2:CPSC_DAC_SRC:{}'.format(args.uut, ch)).put('AWG')


def load_ch(args, ch):
    print("load_ch {} amplitude {}".format(ch, args.mask[ch-1]))
    amp = args.mask[ch-1]
    chpv = epics.PV('{}:AO:AWG:{:02}:V'.format(args.uut, ch))
    chpv.put(amp*args.wf)

def load_awg(args):
    print("load_awg()")
    for ch in range(1, args.nchan+1):
        try:
            load_ch(args, ch)
        except:
            break
    epics.PV('{}:0:AWG_LOAD_CHANNELS'.format(args.uut)).put(1)

def run_main():
    parser = argparse.ArgumentParser(description="cpsc2 load awg")
    parser.add_argument('--nchan', default=8, type=int, help="set number of channels [8]")
    parser.add_argument('--nsam', default=2048, type=int, help="number of samples in waveform [2048]")
    parser.add_argument('--amplitude', default=1, type=float, help="amplitude in volts")
    parser.add_argument('--mask', default=(1,-1,0.9,-0.9,0.8,-0.8,0.1,-0.1), help="channel scale factors")
    parser.add_argument('uut', nargs=1, help="uut")
    args = parser.parse_args()
    args.uut = args.uut[0]
    tt = np.arange(0,args.nsam,dtype=float)
    args.wf=args.amplitude*np.sin(2*np.pi*tt/args.nsam)

    prepare_awg(args)
    load_awg(args)


# execution starts here

if __name__ == '__main__':
    run_main()


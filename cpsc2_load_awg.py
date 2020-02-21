#!/usr/local/bin/python
import epics
import numpy as np
import argparse
import time

"""
awg04 = epics.PV('cpsc2_003:AO:AWG:04:V')
tt = np.arange(0,2048,dtype=float)
sin=1*np.sin(tt/2048*2*np.pi)
awg04.put(sin)


examples
  python cpsc2_load_awg.py --amplitude=0.01 cpsc2_003
  while [ 1 ]; do python cpsc2_load_awg.py --mask='(1,1,0.9,0.9,0.8,0.8,1,1)' cpsc2_003; sleep 5; python cpsc2_load_awg.py --amplitude=0.01 cpsc2_003; sleep 5; done
  while [ 1 ]; do python cpsc2_load_awg.py --amplitude=0.1 --mask='(1,0.9,0.8,0.7,.6,.5,.4,.3)' cpsc2_003; sleep 5; python cpsc2_load_awg.py --amplitude=0.01 cpsc2_003; sleep 5; done

"""

class AwgController:
	
    def stop_awg(self, args):
        print("prepare_awg() {}".format(args.uut))
	self.active = epics.PV('{}:2:AWG:ACTIVE'.format(args.uut))
        self.abort = epics.PV('{}:2:AWG:MODE:ABO'.format(args.uut))
        if self.active.get():
	    self.abort.put(1)

    def wait_stopped(self):
	while self.active.get():
            print("polling for complete")
	    time.sleep(0.1)

        self.abort.put(0)

    def prepare_awg(self, args):
        for ch in ( 'A', 'B' ):
            epics.PV('{}:2:CPSC_DAC_SRC:{}'.format(args.uut, ch)).put('AWG')

    def load_ch(self, args, ch):
        print("load_ch {} amplitude {}".format(ch, args.mask[ch-1]))
        amp = args.mask[ch-1]
        chpv = epics.PV('{}:AO:AWG:{:02}:V'.format(args.uut, ch))
        chpv.put(amp*args.wf)

    def load_awg(self, args):
        print("load_awg()")
        for ch in range(1, args.nchan+1):
            try:
                self.load_ch(args, ch)
            except:
                break
        self.wait_stopped()
        print('set AWG_LOAD_CHANNELS')
        epics.PV('{}:0:AWG_LOAD_CHANNELS'.format(args.uut)).put(1)

    def set_txsfp(self, args):
	epics.PV('{}:SFP:1:TXEN'.format(args.uut)).put(1 if args.txsfp&1 else 0)
	epics.PV('{}:SFP:2:TXEN'.format(args.uut)).put(1 if args.txsfp&2 else 0)

    def __init__(self, args):
        self.stop_awg(args)
	self.set_txsfp(args)
	if not args.stop:
            self.prepare_awg(args)
            self.load_awg(args)


def run_main():
    parser = argparse.ArgumentParser(description="cpsc2 load awg")
    parser.add_argument('--nchan', default=8, type=int, help="set number of channels [8]")
    parser.add_argument('--nsam', default=2048, type=int, help="number of samples in waveform [2048]")
    parser.add_argument('--amplitude', default=1, type=float, help="amplitude in volts")
    parser.add_argument('--stop', default=0, type=int, help="stop the waveform")
    parser.add_argument('--mask', default='(1,-1,0.9,-0.9,0.8,-0.8,0.1,-0.1)', help="channel scale factors")
    parser.add_argument('--txsfp', default=0, type=int, help="transmit to sfp mask 1:A, 2:B, 3:both")
    parser.add_argument('uut', nargs=1, help="uut")
    args = parser.parse_args()
    args.mask = eval(args.mask)
    args.uut = args.uut[0]
    tt = np.arange(0,args.nsam,dtype=float)
    args.wf=args.amplitude*np.sin(2*np.pi*tt/args.nsam)

    AwgController(args)


# execution starts here

if __name__ == '__main__':
    run_main()


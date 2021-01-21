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
	ttime = 0
	while self.active.get():
	    if (ttime*10) % 10 == 0:
	        print("{} polling for complete".format(ttime))
	    time.sleep(0.1)
	    ttime += 0.1

        self.abort.put(0)

    def prepare_awg(self, args):
        for ch in ( 'A', 'B' ):
            epics.PV('{}:2:CPSC_DAC_SRC:{}'.format(args.uut, ch)).put('AWG')

    def load_ch(self, args, ch):
        print("load_ch {} amplitude {}".format(ch, args.mask[ch-1]))
        amp = args.mask[ch-1]
        chpv = epics.PV('{}:AO:AWG:{:02}:V'.format(args.uut, ch))
        chpv.put(amp*args.wf[ch])

    def load_awg(self, args):
        print("load_awg()")
        for ch in range(1, args.nchan+1):
            try:
                self.load_ch(args, ch)
            except:
                break
        self.wait_stopped()
        print('set AWG_LOAD_CHANNELS')
	epics.PV('{}:2:AWG:BURSTLEN'.format(args.uut)).put(args.burstlen)
        epics.PV('{}:0:AWG_LOAD_CHANNELS'.format(args.uut)).put(args.mode)

    def set_txsfp(self, args):
	epics.PV('{}:SFP:1:TXEN'.format(args.uut)).put(1 if args.txsfp&1 else 0)
	epics.PV('{}:SFP:2:TXEN'.format(args.uut)).put(1 if args.txsfp&2 else 0)

    def __init__(self, args):
        self.stop_awg(args)
	self.set_txsfp(args)
	if not args.stop:
            self.prepare_awg(args)
            self.load_awg(args)

class BwgController:
    def __init__(self, args):
        self.load_awg(args)
        self.init_bwg(args)

    def init_bwg_bank(self, args, bank):
        epics.PV('{}:BWG:{}:NCO:FREQ'.format(args.uut, bank)).put(args.nco_freq)
        epics.PV('{}:BWG:{}:SAMPLES'.format(args.uut, bank)).put(args.nsam)
        epics.PV('{}:BWG:{}:EN'.format(args.uut, bank)).put(1)
        
    def init_bwg(self, args):
        self.init_bwg_bank(args, 'A')
        self.init_bwg_bank(args, 'B')

    def load_ch(self, args, ch):
        print("load_ch {} amplitude {}".format(ch, args.mask[ch-1]))
        amp = args.mask[ch-1]
        chpv = epics.PV('{}:AO:BWG:{:02}:V'.format(args.uut, ch))
        chpv.put(amp*args.wf[ch])

    def load_awg(self, args):
        print("load_awg()")
        for ch in range(1, args.nchan+1):
            try:
                self.load_ch(args, ch)
            except:
                break

def pulse(fun, nsam, amp):
    (hi, lo, count) = [ int(x) for x in fun.split(',')]
    wf = np.arange(nsam, dtype=float)
    wf *= 0
    ix = 0
    for p in range(0, count):
        for hx in range(0, hi):
             wf[ix] = amp
             ix += 1
        for hx in range(0, lo):
             ix += 1

    return wf

def run_main():
    parser = argparse.ArgumentParser(description="cpsc2 load awg")
    parser.add_argument('--nchan', default=8, type=int, help="set number of channels [8]")
    parser.add_argument('--nsam', default=2048, type=int, help="number of samples in waveform [2048]")
    parser.add_argument('--ncycles', default=1, type=int, help="number of cycles in waveform [1]")
    parser.add_argument('--burstlen', default=0, type=int, help=">0 : enable burstlen N")
    parser.add_argument('--amplitude', default=1, type=float, help="amplitude in volts")
    parser.add_argument('--stop', default=0, type=int, help="stop the waveform")
    parser.add_argument('--mask', default='(1,-1,0.9,-0.9,0.8,-0.8,0.1,-0.1)', help="channel scale factors")
    parser.add_argument('--txsfp', default=0, type=int, help="transmit to sfp mask 1:A, 2:B, 3:both")
    parser.add_argument('--fun', default='np.sin', type=str, help="function np.sin, np.sinh, np.cos etc")
    parser.add_argument('--tailz', default=1, type=int, help="trailing zero value count [1]")
    parser.add_argument('--mode', default=2, type=int, help="mode 2: oneshot_repeat, 0: continuous")
    parser.add_argument('--bwg', default=0, type=int, help="BRAM WG")
    parser.add_argument('--nco_freq', default=30000, type=float, help="NCO frequency in Hz")
    parser.add_argument('--phi', default='(0,0,0,0,0,0,0,0)', help="phase in degrees, default=0")
    parser.add_argument('uut', nargs=1, help="uut")
    args = parser.parse_args()
    if args.bwg and args.nsam > 4096:
        args.nsam = 4096
    args.mask = eval(args.mask)
    args.phi = eval(args.phi)
    args.uut = args.uut[0]
    tt = np.arange(0,args.nsam,dtype=float)
#    args.wf=args.amplitude*np.sin(2*np.pi*tt/args.nsam)
    args.wf = {}
    if args.fun.startswith('pulse='):
        for ch in range(1,9):
            args.wf[ch] = pulse(args.fun[len('pulse='):], args.nsam, args.amplitude)
    else:
        fx = eval(args.fun)
        for ch in range(1,9):
            args.wf[ch] = args.amplitude*fx(args.ncycles*2*np.pi*tt/args.nsam + args.phi[ch-1]*2*np.pi/360)
            if args.bwg == 0:
                args.wf[ch][args.nsam-(args.tailz+1):] = 0

    if args.bwg:
        BwgController(args)
    else:
        AwgController(args)


# execution starts here

if __name__ == '__main__':
    run_main()


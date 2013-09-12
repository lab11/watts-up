#!/usr/bin/env python
"""record data from WattsUp power meter

Reads data from a Watts Up PRO or compatible power meter (http://www.wattsupmeters.com).
Plots in real time, can run in simulation mode, reading from a file rather than
a physical power meter.

Output format will be space sperated containing:
YYYY-MM-DD HH:MM:SS.ssssss n W V A
where n is sample number, W is power in watts, V volts, A current in amps

Usage: "wattsup.py -h" for options

Author: Kelsey Jordahl
Copyright: Kelsey Jordahl 2011
License: GPLv3
Time-stamp: <Tue Sep 20 09:14:29 EDT 2011>

"""

from __future__ import print_function

import os, serial
import datetime, time
import argparse
import curses
import sys



EXTERNAL_MODE = 'E'
INTERNAL_MODE = 'I'
TCPIP_MODE = 'T'
FULLHANDLING = 2


commands = {'header_request': '#H,R,0;',
            'logging':        '#L,W,3,E,,{};',
            'reset':          '#V,W,0;'}

verbose = False

class stdoutfile ():
    def write (self, s):
        print(s, end='')
    def close (self):
        pass

class wattsup (object):

    def __init__(self, port):

        if verbose:
            print('Looking for {}'.format(port))

        if not os.path.exists(port):
            # Could not find the watts up meter
            raise Exception('Unable to find {}'.format(port))

        self.s = serial.Serial(port, 115200)
        self.logfile = None
        self.interval = 1
        # initialize lists for keeping data
        self.t = []
        self.power = []
        self.potential = []
        self.current = []

    def getHeader (self):
        """ Return an array of strings that identify the data columns. """
        if verbose:
            print('Retrieving header information')

        # Loop until the header info comes back
        while True:
            self.s.write(commands['header_request'])
            h = self.s.readline()
            if h[0:2] == "#h":
                break

        hf = h.split(';')[0].split(',')
        return hf[3:]

    def logg (self, outfile=None, interval=1, format='raw'):
        """ Log data from the watts up """
        if outfile:
            f = open(outfile, 'w')
        else:
            f = stdoutfile()

        self.s.write(commands['logging'].format(int(interval)))

        try:
            while True:
                l = self.s.readline()
                if l[0:2] == '#d':
                    vals = l.split(';')[0].split(',')[3:]

                    if format == 'raw':
                        f.write(','.join(vals) + '\n')

                    else:
                        m = [('watts', float(vals[0])/10.0),
                             ('volts', float(vals[1])/10.0)]

                        if format == 'pretty':
                            for i,item in zip(range(len(m)), m):
                                print('{} {}'.format(item[1], item[0]), end='')
                                if i == len(m) - 1:
                                    print()
                                else:
                                    print(', ', end='')

        except KeyboardInterrupt:
            self.s.close()

    def reset (self):
        """ Soft reset the watts up """
        if verbose:
            print("Resetting the Watts Up")

        self.s.write(commands['reset'])


    def mode(self, runmode):
        if args.sim:
            return                      # can't set run mode while in simulation
        self.s.write('#L,W,3,%s,,%d;' % (runmode, self.interval) )
        if runmode == INTERNAL_MODE:
            self.s.write('#O,W,1,%d' % FULLHANDLING)

    def fetch(self):
        if args.sim:
            return                      # can't fetch while in simulation
        for line in self.s:
            if line.startswith( '#d' ):
                fields = line.split(',')
                W = float(fields[3]) / 10;
                V = float(fields[4]) / 10;
                A = float(fields[5]) / 1000;

    def log(self, logfile = None):
        if not args.sim:
            self.mode(EXTERNAL_MODE)
        if logfile:
            self.logfile = logfile
            o = open(self.logfile,'w')
        if args.raw:
            rawfile = '.'.join([os.path.splitext(self.logfile)[0],'raw'])
            try:
                r = open(rawfile,'w')
            except:
                args.raw = False
        line = self.s.readline()
        n = 0
        # set up curses
        screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        screen.nodelay(1)
        try:
            curses.curs_set(0)
        except:
            pass
        if args.plot:
            fig = plt.figure()
        while True:
            if args.sim:
                time.sleep(self.interval)
            if line.startswith( '#d' ):
                if args.raw:
                    r.write(line)
                fields = line.split(',')
                if len(fields)>5:
                    W = float(fields[3]) / 10;
                    V = float(fields[4]) / 10;
                    A = float(fields[5]) / 1000;
                    screen.clear()
                    screen.addstr(2, 4, 'Logging to file %s' % self.logfile)
                    screen.addstr(4, 4, 'Time:     %d s' % n)
                    screen.addstr(5, 4, 'Power:   %3.1f W' % W)
                    screen.addstr(6, 4, 'Voltage: %5.1f V' % V)
                    if A<1000:
                        screen.addstr(7, 4, 'Current: %d mA' % int(A*1000))
                    else:
                        screen.addstr(7, 4, 'Current: %3.3f A' % A)
                    screen.addstr(9, 4, 'Press "q" to quit ')
                    #if args.debug:
                    #    screen.addstr(12, 0, line)
                    screen.refresh()
                    c = screen.getch()
                    if c in (ord('q'), ord('Q')):
                        break  # Exit the while()
                    if args.plot:
                        self.t.append(float(n))
                        self.power.append(W)
                        self.potential.append(V)
                        self.current.append(A)
                        fig.clear()
                        plt.plot(np.array(self.t)/60,np.array(self.power),'r')
                        ax = plt.gca()
                        ax.set_xlabel('Time (minutes)')
                        ax.set_ylabel('Power (W)')
                        # show the plot
                        fig.canvas.draw()
                    if self.logfile:
                        o.write('%s %d %3.1f %3.1f %5.3f\n' % (datetime.datetime.now(), n, W, V, A))
                    n += self.interval
            line = self.s.readline()
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        try:
            o.close()
        except:
            pass
        if args.raw:
            try:
                r.close()
            except:
                pass



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get data from Watts Up power meter.')
    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true',
                        help='Extra output messages')
    parser.add_argument('--header',
                        dest='header',
                        action='store_true',
                        help='Print the data header info and exit.')
    parser.add_argument('-c', '--command',
                        dest='command',
                        choices=['log', 'internal', 'network'],
                        default='log',
                        help='The command to send to the Watts Up?.\
log: record samples to stdout or a file. internal: record samples to internal \
memory. network: post samples to a server.')
    parser.add_argument('-f', '--format',
                        dest='format',
                        choices=['raw', 'pretty', 'json'],
                        default='raw',
                        help='How to display the data in log format. raw: \
comma separated values directly from watts up. pretty: easy to read by humans. \
json: JSON dict.')
    parser.add_argument('--outfile',
                        dest='outfile',
                        action='store',
                        help='File to write samples to in log mode.')
    parser.add_argument('--save',
                        dest='save',
                        action='store_true',
                        help='Like --outfile, but the filename is set for you.')
    parser.add_argument('-s', '--sample-interval',
                        dest='interval',
                        default=1.0,
                        type=int,
                        help='Sample interval (default 1 s)')
    parser.add_argument('-p', '--port',
                        dest='port',
                        required=True,
                        help='USB serial port that the meter is connected to')
    args = parser.parse_args()

    if args.verbose:
        verbose = True

    # Connect to the meter
    meter = wattsup(args.port)

    # Do the commands in the correct order

    if args.header:
        # Get the header info for the data
        h = meter.getHeader()
        print('Headings: ' + ', '.join(h))
        sys.exit(0)

    if args.outfile:
        outfile = args.outfile
    elif args.save:
        outfile = 'wattsup_{}.data'.format(
            datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    else:
        # stdout
        outfile = None

    if args.command == 'log':
        # Tell the meter to send us samples
        meter.logg(outfile=outfile, interval=args.interval, format=args.format)


























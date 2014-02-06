#!/usr/bin/env python3

import sys
try:
    import serial
except ImportError:
    print('Need serial package.')
    print('sudo port install py-serial')
    sys.exit(1)
import os
import datetime, time
import argparse
import json
import curses
import string


USER_AGENT = 'WattsUp.NET'

commands = {'header_request':    '#H,R,0;',
            'version_request':   '#V,R,0;',
            'network_info':      '#I,Q,0;',
            'network_info_ext':  '#I,E,0;',
            'set_network_basic': '#I,S,6,{},{},{},{},{},{};',
            'set_network_ext':   '#I,X,5,{},{},{},{},{};',
            'write_network':     '#I,W,0;',
            'logging':           '#L,W,3,E,,{};',
            'reset':             '#V,W,0;'}

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

    def getHeader (self):
        """ Return an array of strings that identify the data columns. """
        if verbose:
            print('Retrieving header information')

        # Loop until the header info comes back
        while True:
            self.s.write(commands['header_request'].encode('ascii'))
            h = self.s.readline().decode('ascii')
            if h[0:2] == "#h":
                break

        hf = h.split(';')[0].split(',')
        return hf[3:]

    def getVersionInfo (self):
        """ Returns a string that nicely formats the meter's version and info"""
        if verbose:
            print('Retrieving identifying information')

        while True:
            self.s.write(commands['version_request'].encode('ascii'))
            i = self.s.readline().decode('ascii')
            if i[0:2] == "#v":
                ifields = i.split(';')[0].split(',')[3:]
                if len(ifields) == 8:
                    break
        ret = ''
        versions = ['Standard', 'PRO', 'ES', '.NET']
        hwma = ['ADE7763, PIC18F45J10', 'ADE7763, PIC18F45J10, Ethernet']
        hwmi = ['no USB', 'USB @ 19200bps', 'USB @ 115200bps', 'Ethernet']
        comptime = datetime.datetime.strptime(ifields[6], '%Y%m%d%H%M%S')
        ret += 'Watts Up? Meter Version Information:\n'
        ret += 'Model type:     {}\n'.format(versions[int(ifields[0])])
        ret += 'Memory (bytes): {}\n'.format(ifields[1])
        ret += 'Hardware Major: {}\n'.format(hwma[int(ifields[2])-5])
        ret += 'Hardware Minor: {}\n'.format(hwmi[int(ifields[3])])
        ret += 'Firmware Major: {}\n'.format(ifields[4])
        ret += 'Firmware Minor: {}\n'.format(ifields[5])
        ret += 'SW Compilation: {}\n'.format(comptime)
        return ret

    def getNetworkInfo (self):
        if verbose:
            print('Retrieving network information')

        while True:
            self.s.write(commands['network_info'].encode('ascii'))
            i = self.s.readline().decode('ascii')
            if i[0:2] == "#i":
                n1 = i.split(';')[0].split(',')[3:]
                if len(n1) == 7:
                    break

        while True:
            self.s.write(commands['network_info_ext'].encode('ascii'))
            i = self.s.readline().decode('ascii')
            if i[0:2] == "#i":
                n2 = i.split(';')[0].split(',')[3:]
                if len(n2) == 5:
                    break

        mac = ':'.join(n1[6][i:i+2] for i in range(0,len(n1[6]),2))
        ret = ''
        ret += 'Watts Up? Meter Network Information:\n'
        ret += 'IP Address:    {}\n'.format(n1[0])
        ret += 'Gateway:       {}\n'.format(n1[1])
        ret += 'DNS 1:         {}\n'.format(n1[2])
        ret += 'DNS 2:         {}\n'.format(n1[3])
        ret += 'Net Mask:      {}\n'.format(n1[4])
        ret += 'DHCP:          {}\n'.format(n1[5]=='1')
        ret += 'MAC Address:   {}\n'.format(mac)
        ret += 'POST Host:     {}\n'.format(n2[0])
        ret += 'POST Port:     {}\n'.format(n2[1])
        ret += 'POST File:     {}\n'.format(n2[2])
        ret += 'User Agent:    {}\n'.format(n2[3])
        ret += 'POST Interval: {} seconds\n'.format(n2[4])
        return ret

    def enableDHCP (self):
        self.setNetworkBasic('0.0.0.0', '0.0.0.0', '0.0.0.0', '0.0.0.0',
            '255.255.255.0', True)

    def setNetworkBasic (self, ip_addr, gateway, dns1, dns2, net_mask, dhcp):

        cmd = commands['set_network_basic'].format(ip_addr, gateway, dns1, dns2,
            net_mask, int(dhcp).encode('ascii'))
        self.s.write(cmd)
        self.s.readline()
        self.s.write(commands['write_network'].encode('ascii'))
        self.s.readline()

    def setNetworkExtended (self, url, port, pfile, interval=1):
        if len(url) > 40:
            print("POST URL too long. Must be 40 characters or less.")
            sys.exit(1)
        if len(pfile) > 40:
            print("POST file too long. Must be 40 characters or less.")
            sys.exit(1)

        cmd = commands['set_network_ext'].format(url, port, pfile,
            USER_AGENT, int(interval)).encode('ascii')
        self.s.write(cmd)
        self.s.readline()
        self.s.write(commands['write_network'].encode('ascii'))
        self.s.readline()

    def log (self, outfile=None, interval=1, format='raw'):
        """ Log data from the watts up """
        if outfile:
            f = open(outfile, 'w')

            f.write('# Readings from a Watts Up? Meter\n')
            f.write('# {}\n\n'.format(datetime.datetime.now()))

            if format == 'raw':
                f.write('timestamp,{}\n'.format(','.join(self.getHeader())))
        else:
            f = stdoutfile()

        self.s.write(commands['logging'].format(int(interval)).encode('ascii'))

        try:
            while True:
                l = self.s.readline().decode('ascii')
                if l[0:2] == '#d':
                    vals = l.split(';')[0].split(',')[3:]

                    now = int(time.time()*1000)

                    m = [('time', now),
                         ('watts', float(vals[0])/10.0),
                         ('volts', float(vals[1])/10.0),
                         ('amps', float(vals[2])/10.0),
                         ('watt-hours', float(vals[3])/10.0),
                         ('dollars', float(vals[4])/1000.0),
                         ('watt hours monthly', float(vals[5])),
                         ('dollars monthly', float(vals[6])*10.0),
                         ('power factor', float(vals[7])),
                         ('duty cycle', float(vals[8])),
                         ('power cycle', float(vals[9])),
                         ('frequency', float(vals[10])/10.0),
                         ('volt-amps', float(vals[10])/10.0)]

                    if format == 'raw':
                        for i,item in zip(range(len(m)), m):
                            f.write('{}'.format(item[1]))
                            if i == len(m) - 1:
                                f.write('\n')
                            else:
                                f.write(',')

                    elif format == 'pretty':
                        for i,item in zip(range(len(m)), m):
                            f.write('{} {}'.format(item[1], item[0]))
                            if i == len(m) - 1:
                                f.write('\n')
                            else:
                                f.write(', ')

                    elif format == 'json':
                        f.write('{}\n'.format(json.dumps(dict(m))))

        except KeyboardInterrupt:
            self.s.close()

    def reset (self):
        """ Soft reset the watts up """
        if verbose:
            print("Resetting the Watts Up")

        self.s.write(commands['reset'].encode('ascii'))



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
    parser.add_argument('-l', '--log',
                        dest='log',
                        action='store_true',
                        help='Tell the meter to send us samples via USB.')
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
    parser.add_argument('-n', '--network-config',
                        dest='network',
                        action='append',
                        nargs=3,
                        help='Configure POST settings. <POST URL> <POST port> \
<POST file>')
    parser.add_argument('--dhcp',
                        dest='dhcp',
                        action='store_true',
                        help='Enable DHCP on the watts up')
    parser.add_argument('--reset',
                        dest='reset',
                        action='store_true',
                        help='Soft reset the meter.')
    parser.add_argument('-i', '--info',
                        dest='info',
                        action='store_true',
                        help='Request identifying information from the meter.')
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
        print('Headings: {}'.format(', '.join(meter.getHeader())))
        sys.exit(0)

    if args.info:
        print(meter.getVersionInfo())
        print(meter.getNetworkInfo())
        sys.exit(0)

    if args.reset:
        meter.reset()
        sys.exit(0)

    if args.log:
        if args.outfile:
            outfile = args.outfile
        elif args.save:
            outfile = 'wattsup_{}.data'.format(
                datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        else:
            # stdout
            outfile = None

        # Tell the meter to send us samples
        meter.log(outfile=outfile, interval=args.interval, format=args.format)

    elif args.network:
        url = args.network[0][0]
        port = args.network[0][1]
        pfile = args.network[0][2]

        interval = 1
        if args.interval:
            interval = int(args.interval)

        meter.setNetworkExtended(url, port, pfile, interval)

    elif args.dhcp:
        meter.enableDHCP()


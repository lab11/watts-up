Watts Up? Python Interface
==========================

Code to interface with the Watts up? .net. Works over the USB cable. Allows you
to view samples in a terminal, save to a logfile, or POST them using the
network connection.


Usage
-----

### Linux

    python wattsup.py -p /dev/ttyUSBX -i
    python wattsup.py --help

### Mac OS X

Install the http://www.ftdichip.com/Drivers/VCP.htm drivers. Restart.

    python wattsup.py -p /dev/tty.usbserial-X -i


Server
------

A simple python script that receives the HTTP request from Watts Up .net
and prints out the values in JSON format.

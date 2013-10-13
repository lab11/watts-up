#!/usr/bin/python


from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import json
import time
import urlparse

PORT_NUMBER = 8080

class myHandler(BaseHTTPRequestHandler):
	requestline = ''
	request_version = 'HTTP/1.0'

	def handle(self):
		now = int(time.time()*1000)

		header_str = ''
		while True:
			byte = self.rfile.read(1)
			header_str += byte
			if len(header_str) > 3 and header_str[-4:] == '\r\n\r\n':
				break
		headers = header_str.split('\n')
		for header in headers:
			val = header.split(': ')
			if val[0] == 'Content-Length':
				length = int(val[1])
				break
		poststr = self.rfile.read(length)

		data = urlparse.parse_qs(poststr)

		m = [('time', now),
			 ('id', data['id'][0]),
			 ('watts', float(data['w'][0])/10.0),
			 ('volts', float(data['v'][0])/10.0),
			 ('amps', float(data['a'][0])/10.0),
			 ('watt-hours', float(data['wh'][0])/10.0),
			 ('max watts', float(data['wmx'][0])/10.0),
			 ('max volts', float(data['vmx'][0])/10.0),
			 ('max amps', float(data['amx'][0])/10.0),
			 ('min watts', float(data['wmi'][0])/10.0),
			 ('min volts', float(data['vmi'][0])/10.0),
			 ('min amps', float(data['ami'][0])/10.0),
			 ('power factor', float(data['pf'][0])),
			 ('power cycle', float(data['pcy'][0])),
			 ('frequency', float(data['frq'][0])/10.0),
			 ('volt-amps', float(data['va'][0])/10.0)]

		print(json.dumps(dict(m)))


		self.send_response(200)
		self.send_header('Content-type','text/html')
		self.end_headers()
		# Send the html message
		self.wfile.write("[0]")
		return

	def log_message(self, format, *args):
		return

try:
	# Create a web server and define the handler to manage the incoming request
	server = HTTPServer(('', PORT_NUMBER), myHandler)
	print 'Started httpserver on port ' , PORT_NUMBER

	# Wait forever for incoming http requests
	server.serve_forever()

except KeyboardInterrupt:
	print '^C received, shutting down the web server'
	server.socket.close()

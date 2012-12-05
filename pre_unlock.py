#!/usr/bin/env python
#
# Copyright 2011: dogbert <dogber1@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

import serial, string, os, getopt, sys, crctable
from struct import pack, unpack, unpack_from
from time import sleep

def crc16(s):
	crc = 0
	for c in s:
		crc = crctable.crcTable[(crc&0xff)^ord(c)] ^ (crc >> 8)
	return crc & 0xFFFF

def readSerial(ser):
	while 1:
		if ser.inWaiting() > 0:
			return ser.read(ser.inWaiting())
		else:
			sleep(0.2)

def sendRawCommand(ser, command, bufsize=-1, timeout=50, dwnMode=False):
	if len(command) > 0: 
		ser.write(command)
	t = 0
	r = ""
	while 1:
		if dwnMode or (bufsize == -1):
			a = ser.inWaiting()
			r += ser.read(a)
			if (len(r) > 2) and dwnMode:
				if (ord(r[len(r)-1]) == 0x7e) and (ord(r[len(r)-2]) != 0x7d):
					return r
			if (len(r) > 2) and not dwnMode:
				if (ord(r[len(r)-1]) == 0x7e):
					return r
			else:
				sleep(0.001)
				t += 1
		else:
			if ser.inWaiting() >= bufsize:
				return ser.read(bufsize)
			else:
				sleep(0.001)
				t += 1
		if t > timeout:
#			print "timeout (buffer size %d)" % ser.inWaiting()
			return ""

def sendCommand(ser, command, bufsize=-1, timeout=1000, dwnMode=False):
	if command[0] == "\x7e":
		crc = crc16(command[1:len(command)])
	else:
		crc = crc16(command)
	command = command + pack('H', crc)

	command = command[0] + command[1:len(command)].replace('\x7D', '\x7D\x5D').replace('\x7E', '\x7D\x5E')
	command += '\x7E'
#	dumphex(command)
	r = sendRawCommand(ser, command, bufsize, timeout, dwnMode)
	if not r is None:
		i = 2
		while i < len(r):
			if (r[i] == "\x5D") and (r[i-1] == "\x7D"):
				r = r[0:i-1] + "\x7D" + r[i+1:len(r)] 
			elif (r[i] == "\x5E") and (r[i-1] == "\x7D"):
				r = r[0:i-1] + "\x7E" + r[i+1:len(r)]
			i += 1
	else:
		r = ""
	return r
	
def dumphex(s):
	i = -1
	if s is None:
		return
	print "dumping %d bytes..." % len(s)
	for i in xrange(0,len(s)/16+1):
		o = '%08x  ' % (i*16)
		for j in range(0, 16):
			if len(s) > i*16+j:
				o += '%02x ' % ord(s[i*16+j])
			else:
				o += '   '
		o += ' |'
		for j in range(0, 16):
			if len(s) > i*16+j:
				if (ord(s[i*16+j]) > 0x1F) and (ord(s[i*16+j]) < 0x7F):
					o += s[i*16+j]
				else:
					o += '.'
			else:
				break
		o += '|'
		print o 

def getInfo(ser):
	return sendCommand(ser, "\x00")

def getGSMStatus(ser):
	r = sendCommand(ser, "\x4b\x08\x01\x00", 35);
	imei = ""
	for i in range(1, 16):
		if i % 2 == 0:
			imei += "%1d" % (ord(r[5+i/2]) & 0x0F)
		else:
			imei += "%1d" % ((ord(r[5+i/2]) & 0xF0) >> 4)
	imsi = ""
	for i in range(1, 16):
		if i % 2 == 0:
			imsi += "%1d" % (ord(r[14+i/2]) & 0x0F)
		else:
			imsi += "%1d" % ((ord(r[14+i/2]) & 0xF0) >> 4)
	return (imei, imsi)

def getBuildID(ser):
	r = sendCommand(ser, "\x7c");
	if r.find("CU") != -1:
		r = "CU" + r.split("CU")[1]
	elif r.find("XU") != -1:
		r = "XU" + r.split("XU")[1]
	elif r.find("BU") != -1:
		r = "BU" + r.split("BU")[1]
	return "%s" % r.split("\x00")[0]
	
def patchPermDescriptor(ser, ver):
	offset = 0
	# pre 1.4.x
	if (ver.find("(259)") != -1) or (ver.find("(257)") != -1) or (ver.find("(241)") != -1):
		offset = 0xEC325C
	# pre 2.1.0
	if ver.find("(5036)") != -1:
		offset = 0xECF4B4
	# pixie 1.4.x
	if (ver.find("(3124)") != -1):
		offset = 0x6DE41A8
	if (ver.find("(3125)") != -1):
		offset = 0x6DE37B8

	if (offset == 0):
		return False
	r = sendCommand(ser, '\x07' + pack("<I", offset) + "\x01" + pack("<I", 0)*2, 17)
	return True

def dumpMem(ser, start, stop, outfile):
	f = open(outfile, "wb")
	currentAddress = start
	size = 16
	while currentAddress < stop:
		if currentAddress % 0x10000 == 0:
			print "Address: %08x" % currentAddress
		command = "\x04" + pack('<I', currentAddress) + pack('<H', size//4)
		data = sendCommand(ser, command, bufsize=-1, timeout=200)
		if len(data) == len(command)+size+3:
			f.write(data[len(command):len(data)-3])
		else:
			print "Error at offset %x %d %d" % (currentAddress, len(data), len(command))
			f.write('\xFF'*size)
			dumphex(data)

		currentAddress += size

	f.close()

def efs_readFile(ser, filename):
	block = 0
	c = ""
	command = '\x59\x04' + chr(block) + chr(len(filename)+1) + filename + '\x00';
	r = sendCommand(ser, command, dwnMode=True)
	if r[0] != '\x59':
		return
	done = False
	totalsize = unpack("<I", r[5:9])[0]
	while not done:
		done = (r[4] == '\x00')
		if block == 0:
			size = unpack("<h", r[9:11])[0]
			c += r[11:11+size]
		else:
			size = unpack("<h", r[5:7])[0]
			c += r[7:7+size]
		block += 1
		command = '\x59\x04' + chr(block);
		r = sendCommand(ser, command, dwnMode=True)
	return c

def efs_writeFile(ser, filename, c):
	block = 0
	pos = 0
	mode = 0x000100FF
	if len(c) > 0x100:
		command = '\x59\x05' + chr(block) + "\x01\x01" + pack("<I", len(c)) + pack("<I", mode) + chr(len(filename)+1) + filename + "\x00" + pack("<h", 0x100)
		command += c[0:0x100]
		pos += 0x100
	else:
		command = '\x59\x05' + chr(block) + "\x00\x01" + pack("<I", len(c)) + pack("<I", mode) + chr(len(filename)+1) + filename + "\x00" + pack("<h", len(c))
		command += c
		pos = len(c)
	r = sendCommand(ser, command, dwnMode=True)
	if r[0] != '\x59':
		return
	while pos < len(c):
		block += 1
		if len(c)-pos < 0x100:
			command = '\x59\x05' + chr(block) + "\x00" + pack("<h", len(c)-pos) + c[pos:]
			pos = len(c)
		else:
			command = '\x59\x05' + chr(block) + "\x01" + pack("<h", 0x100) + c[pos:pos+0x100]
			pos += 0x100
		r = sendCommand(ser, command, dwnMode=True)
		if r[0] != '\x59':
			return
	return True

def rebootModem(ser):
	sendCommand(ser, '\x0b')

def get_codes(c, l=8):
	s = 0
	codes = []
	while 1:
		p = c.find(pack(">h", 2*l), s)
		if p > -1:
			s = p + 2
		else:
			break
		o = ""
		for i in range(0, l):
			o += chr(ord(c[i+s])^ord(c[i+s+l]))
		codes.append(o)
	return codes

def readUnlockCode(c):
	codes = get_codes(c, 8)
	if len(codes) == 0:
		print "The network unlock code has not been found. Please send the perso.txt file to the author."
		return None
	return codes[0]

def patchPerso(c):
	offset = c.find(pack(">h", 10))
	if offset == -1:
		return
	c = c[0:offset+2] + "\x00"*10 + c[offset+2+10:]
	return c

def checkDiagPort(port, token):
	try:
		ser = serial.Serial(port, 115200, timeout=0)
		response = getInfo(ser)
		result = (response.find(token) != -1)
		ser.close()
	except serial.SerialException:
		result = False
	return result

def findSerialPorts(portName):
	for i in range(0, 255):
		port = (portName + '%d') % i
		if checkDiagPort(port, "TSNCJOLYM"):
			return port
		if checkDiagPort(port, "KYRB"):
			return port 
		if checkDiagPort(port, "Castle"):
			print "Your phone is a CDMA device and can't be unlocked for GSM."
			return None
	return None

def info():
	print "pre_unlock.py v1.9"
	print "Copyright (c) 2011 dogbert <dogber1@gmail.com>, http://dogber1.blogspot.com"
	print "This scripts reads the unlock code of Palm Pre/Pixi GSM Phones."
	print ""

def usage():
	print "Options: -d, --diagPort=  name of the serial diagnostics port (e.g. COM4)"
	print "         -w, --writeBack= write back patched personalization file from cell phone (dangerous!)"
	print "         -f, --file=      write personalization file to cell phone (dangerous!)"
	print ""
	print "Example: pre_unlock.py -d COM4"

def idiotExit():
	if (os.name == 'nt'):
		raw_input()
	sys.exit()

def main():
	info()
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hd:wf:", ["help", "diagPort=", "writeBack", "file="])
	except getopt.GetoptError, err:
		print str(err)
		usage()
		sys.exit(2)

	diagPort  = None
	baud	  = 921600
	Init	  = True
	writeBack = False 
	persoFile = None

	for o, a in opts:
		if o in ("-d", "--diagPort"):
			diagPort = a
		elif o in ("-w", "--writeBack"):
			writeBack = True
		elif o in ("-f", "--file"):
			persoFile = a
		elif o in ("-h", "--help"):
			usage()
			sys.exit()

	if (diagPort == None):
		if os.name == 'nt':
			portName = "COM"
		elif sys.platform == 'linux2':
			portName = "/dev/ttyUSB"
		diagPort = findSerialPorts(portName)

	if diagPort == None:
		print "Failed to find the diagnostics port. Exiting..."
		idiotExit()

	print "Diagnostics serial port: %s" % diagPort
	print ""
	
	ser = serial.Serial(diagPort, baud, timeout=0)
	getInfo(ser)
	build = getBuildID(ser)
	(imei, imsi) = getGSMStatus(ser)
	
	print "IMEI:                    %s" % imei
	print "Software Build ID:       %s" % build
	print ""
	print "Patching EFS file permission descriptors..."
	if not patchPermDescriptor(ser, build):
		print "Unknown firmware version."
		idiotExit()
	print "Reading personalization file from EFS..."
	c = efs_readFile(ser, "mmgsdi/perso/perso.txt")
	f = open("perso-%s.txt" % imei, "wb")
	f.write(c)
	f.close()

	print "Network Control Code:    %s" % readUnlockCode(c)
	print ""
	if writeBack:
		print "Writing personalization file..."
		if writeBack:
			c = patchPerso(c)
		if persoFile:
			f = open(persoFile, "rb")
			c = f.read()
			f.close()
		if not efs_writeFile(ser, "mmgsdi/perso/perso.txt", c):
			print "Write failed..."
		
	print "Rebooting Baseband Modem..."
	rebootModem(ser)
	ser.close()
	print "done."
	idiotExit()

if __name__ == "__main__":
	main()


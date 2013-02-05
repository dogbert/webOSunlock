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
	if len(r) == 0:
		return ("unknown", "unknown")
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
	elif r.find("MU") != -1:
		r = "MU" + r.split("MU")[1]
	elif r.find("MW") != -1:
		r = "MW" + r.split("MW")[1]
	return "%s" % r.split("\x00")[0]
	
def dumpMem(ser, start, size):
	c = ""
	currentAddress = start
	stop = currentAddress + size
	chunkSize = 4
	while currentAddress < stop:
		if currentAddress % 0x10000 == 0:
			print "Address: %08x" % currentAddress
		command = "\x04" + pack('<I', currentAddress) + pack('<H', chunkSize//4)
		data = sendCommand(ser, command, bufsize=-1, timeout=200)
		if len(data) == len(command)+chunkSize+3+3*4:
			c += data[len(command):len(command)+chunkSize]
		else:
			print "Error at offset %x %d %d" % (currentAddress, len(data), len(command))
			
			c += '\xFF'*chunkSize

		currentAddress += chunkSize
	return c

def writeMemDWord(ser, m, address):
	currentAddress = address
	if type(m) == str:
		l = len(m)//4
	elif type(m) == list:
		l = len(m)
	for i in range(l):
		if type(m) == str:
			data = unpack("<I", m[4*i:4*i+4])[0]
		elif type(m) == list:
			data = m[i]
		command = "\x07" + pack('<I', currentAddress) + '\x01' + pack('<I', data) + '\x00\x00\x00\x00'
		sendCommand(ser, command, bufsize=-1, timeout=200)
		currentAddress += 4

def sfsGetPersoFile(ser, ver, writeBack):
	argHeapAlloc    = 0x818
	argAllocPktBuf1 = 0x0
	argAllocPktBuf2 = 0x5
	argReadSFS      = 0x818

	diagCmdStruct = 0
	f = open("payload.bin", "rb")
	patch = f.read()
	f.close()
	patch = patch[patch.find("\x00\xb5"):patch.find("\x01\xbd")+2]

	# veer
	if ver.find("(257)") != -1:
		targetCmdHandlerAdr     = 0x0FB81210
		diagCmdStruct           = 0x0EBD15B0
		diagCmdHandler          = 0x0EBD16A0
		funcHeapAlloc           = 0x0E066D3C
		funcAllocPktBuf         = 0x0E33BFFE
		funcReadSFS             = 0x0EABA938
		funcGenerateVirginPerso = 0x0EA1B984
	if ver.find("(264)") != -1:
		targetCmdHandlerAdr     = 0x0fb80210
		diagCmdStruct           = 0x0ebd05b8
		diagCmdHandler          = 0x0ebd0654
		funcHeapAlloc           = 0x0e0639c0
		funcAllocPktBuf         = 0x0e34b7fc
		funcReadSFS             = 0x0eabea1c
		funcGenerateVirginPerso = 0x0e7c8fcc
	if ver.find("(3500)") != -1:
		targetCmdHandlerAdr     = 0x0FB7C20c
		diagCmdStruct           = 0x0EBCC5D8
		diagCmdHandler          = 0x0EBCD990
		funcHeapAlloc           = 0x0E063A0C
		funcAllocPktBuf         = 0x0DE1AE94
		funcReadSFS             = 0x0E5FBCD4
		funcGenerateVirginPerso = 0x0EA1C62C
	
	# pre3 umts
	if ver.find("(3004)") != -1:
		targetCmdHandlerAdr     = 0x0FB7C3D4
		diagCmdStruct           = 0x0EC36FA8
		diagCmdHandler          = 0x0EC38EB8
		funcHeapAlloc           = 0x0E25569C
		funcAllocPktBuf         = 0x0DF880A2
		funcReadSFS             = 0x0E5A2CCC
		funcGenerateVirginPerso = 0x0E245EB8

	# pre3 world phone (umts+cdma) 
	if ver.find("(4089)") != -1:
		targetCmdHandlerAdr     = 0x0FB53D08
		diagCmdStruct           = 0x0EA20164 
		diagCmdHandler          = 0x0EA20D00
		funcHeapAlloc           = 0x0E112DE4
		funcAllocPktBuf         = 0x0DE11502
		funcReadSFS             = 0x0E1FF628
		funcGenerateVirginPerso = 0x0DA18FD4

	if diagCmdStruct == 0:
		print "Unknown firmware version."
		idiotExit()

	patch += "\x00" * (len(patch)%4)
	writeMemDWord(ser, patch, targetCmdHandlerAdr)
	writeMemDWord(ser, [targetCmdHandlerAdr+1], diagCmdHandler+4)
	writeMemDWord(ser, [argAllocPktBuf1,argAllocPktBuf2,funcAllocPktBuf+1,argHeapAlloc,funcHeapAlloc+1,argReadSFS,funcReadSFS+1, 0], diagCmdHandler-28)
	writeMemDWord(ser, [diagCmdHandler], diagCmdStruct)

	resp = sendCommand(ser, "\x00")
	address = unpack("<I", resp[1:5])[0]
	perso = dumpMem(ser, address, 0x200)

	if writeBack:
		writeMemDWord(ser, [funcGenerateVirginPerso+1], diagCmdHandler+4)
		resp = sendCommand(ser, "\x00")

	return perso

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
		if 2*l+s > len(c):
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
		if checkDiagPort(port, "AABBQ"):
			return port 
	return None

def info():
	print "pre3_veer_unlock.py v1.5"
	print "Copyright (c) 2011 dogbert <dogber1@gmail.com>, http://dogber1.blogspot.com"
	print "This script reads the unlock code of HP Veer/Pre3 phones."
	print ""

def usage():
	print "Options: -d, --diagPort=  name of the serial diagnostics port (e.g. COM4 or /dev/ttyUSB0)"
	print "         -w, --writeBack= write patched personalization file to cell phone (dangerous!)"
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
	
	if diagPort == None:
		if os.name == 'nt':
			portName = "COM"
		elif sys.platform == 'linux2':
			portName = "/dev/ttyUSB"
		print "Scanning serial ports..."
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
	if imei == "unknown":
		print "Failed to read the IMEI. Please check the driver for the serial diagnostics port. Exiting..."
		idiotExit()
	
	print "IMEI:                    %s" % imei
	print "Software Build ID:       %s" % build
	print ""
	print "Reading personalization file from SFS..."
	c = sfsGetPersoFile(ser, build, writeBack)
	f = open("perso-%s.txt" % imei, "wb")
	f.write(c)
	f.close()

	print "Network Control Code:    %s" % readUnlockCode(c)
	print ""
	print "Rebooting phone..."
	sleep(1)
	rebootModem(ser)
	ser.close()
	print "done."
	idiotExit()

if __name__ == "__main__":
	main()


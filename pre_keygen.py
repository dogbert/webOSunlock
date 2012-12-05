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

import sys, getopt, os

def calcPassthroughKey(SN):
	SN = SN.upper()
	if len(SN) != 12:
		print "ERROR: Serial Number is not 12 characters long!"
		idiotExit()
	key = 0
	for i in range(12):
		key = (key+4567*ord(SN[i])) % 100000
	return "%05d" % key

def idiotExit():
	if (os.name == 'nt'):
		raw_input()
	sys.exit()

def info():
	print "pre-keygen.py v1.9"
	print "Copyright (c) 2011 dogbert <dogber1@gmail.com>, http://dogber1.blogspot.com"
	print "This scripts calculates the USB passthrough key for Palm Pre cell phones."
	print ""

def usage():
	print "Options: -s, --serial=     serial number"
	print "Example: pre_keygen.py -s 123456789012"

def main():
	info()
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hs:", ["help", "serial="])
	except getopt.GetoptError, err:
		print str(err)
		usage()
		sys.exit(2)

	SN = ''
	for o, a in opts:
		if o in ("-s", "--serial"):
			SN = a
		elif o in ("-h", "--help"):
			usage()
			sys.exit()

	if SN == '':
		print "Please enter the serial number of your Palm Pre (P...):"
		SN = raw_input().strip()
	
	print ""
	print "Passthrough Key: " + calcPassthroughKey(SN)
	print ""
	print "done."
	idiotExit()

if __name__ == "__main__":
	main()


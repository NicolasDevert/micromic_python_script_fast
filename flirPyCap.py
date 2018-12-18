#!/usr/bin/python

import sys
from gi.repository import Aravis
from flirClass import camera
import cv2

try:
    flir = camera()
except TypeError:
    print "Error: Aravis found no Camera." 
    print "Check Connections"
    sys.exit(2)
else:
    print flir.device
    flir.make_stream()
    flir.camera.start_acquisition()
    flir.path = "/home/micromet/repo/flirPyCapSdFast/data/"


flir.nuc_timer()
flir.create_buffer()

while True:
    buffer = flir.stream.try_pop_buffer()
    if buffer:
	if buffer.get_status() == Aravis.BufferStatus.SUCCESS:
            frame = flir.array_from_buffer_address(buffer)
            flir.stream.push_buffer(buffer)
            flir.buffer_to_image(frame)
            cv2.imshow("frame", frame)
            ch = cv2.waitKey(1) & 0xFF
	else:
	    print "Time out"
	    flir.stream.push_buffer(buffer)


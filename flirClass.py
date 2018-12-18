import gi
gi.require_version('GExiv2', '0.10')
gi.require_version('Aravis', '0.6')

from gi.repository import Aravis
from gi.repository import GExiv2
from libtiff import TIFF
from ctypes import POINTER, c_uint16, cast
from numpy import ctypeslib
from datetime import datetime
from threading import Timer, Lock
import json
import os

class camera:
    def __init__(self):
        self.camera = Aravis.Camera.new (None)
        self.device = self.camera.get_device ()
        self.lock = Lock()
        self.buffer_size = 5
        self.pic_int = 60
        self.nuc_int = 60
	self.path = "data/"

    def raw_thermals(self):
        raws = self.return_buffers()
        return raws

    def make_stream(self):
        self.stream = self.camera.create_stream (None, None)

    def create_buffer(self):
        payload = self.camera.get_payload ()
        try:
            for i in range(0,self.buffer_size):
                self.stream.push_buffer (Aravis.Buffer.new_allocate (payload))
        finally:
            print "Create Buffer"

    def return_buffers(self):
        n_Buffers = self.stream.get_n_buffers()[1]
        if n_Buffers == self.buffer_size:
            self.Buffers = []
            for i in range(0,n_Buffers):
                buffer = self.stream.try_pop_buffer()
                if i == n_Buffers - 2 :
                    if buffer.get_status() == Aravis.BufferStatus.SUCCESS:
                        im = self.array_from_buffer_address(buffer)
                        self.buffer_to_image(im)
                    else:
                        print "timeout"
        else:
            pass

    def array_from_buffer_address(self, buf):
        if not buf:
            return None
        pixel_format = buf.get_image_pixel_format()
        bits_per_pixel = pixel_format >> 16 & 0xff
        addr = buf.get_data()
        ptr = cast(addr, POINTER(c_uint16))
        im = ctypeslib.as_array(ptr, (buf.get_image_height(), buf.get_image_width()))
        im = im.copy()
        return im

    def buffer_to_image(self, frame):
        time = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        fileName = self.Vendor + '_' + time + '.tiff'
        fileName = fileName.replace(" ", "")
	fileName = self.path + fileName
        print("Saving image to ", fileName)
        tiff = TIFF.open(fileName, mode='w')
        tiff.write_image(frame)
        exif = GExiv2.Metadata(fileName)
        exif['Exif.Image.ImageDescription'] =self.tag_dict
        exif.save_file()

    def update_tags(self):
        self.Emissivity = self.device.get_float_feature_value("ObjectEmissivity")
        self.T_Refl = self.device.get_float_feature_value("ReflectedTemperature")
        self.Obj_Dist = self.device.get_float_feature_value("ObjectDistance")
        self.Atm_Temp = self.device.get_float_feature_value("AtmosphericTemperature")
        self.RH = self.device.get_float_feature_value("RelativeHumidity")
        self.Ext_Opt_Temp = self.device.get_float_feature_value("ExtOpticsTemperature")
        self.Ext_Opt_Trans = self.device.get_float_feature_value("ExtOpticsTransmission")
        self.Est_Trans = self.device.get_float_feature_value("EstimatedTransmission")
        self.Vendor = self.device.get_string_feature_value ("DeviceVendorName")
        self.Width = self.device.get_integer_feature_value ("Width")
        self.Height = self.device.get_integer_feature_value ("Height")
        self.R = self.device.get_float_feature_value("R")
        self.B = self.device.get_float_feature_value("B")
        self.F = self.device.get_float_feature_value("F")
        self.J0 = self.device.get_integer_feature_value("J0")
        self.J1 = self.device.get_float_feature_value("J1")
        self.alpha1 = self.device.get_float_feature_value("alpha1")
        self.alpha2 = self.device.get_float_feature_value("alpha2")
        self.beta1 = self.device.get_float_feature_value("beta1")
        self.beta2 = self.device.get_float_feature_value("beta2")
        self.X = self.device.get_float_feature_value("X")
        self.tag_dict = {
                "Emissivity"             : self.Emissivity,
                "ReflectedTemperature"   : self.T_Refl,
                "ObjectDistance"         : self.Obj_Dist,
                "AtmosphericTemperature" : self.Atm_Temp,
                "RelativeHumidity"       : self.RH,
                "ExtOpticsTemperature"   : self.Ext_Opt_Temp,
                "ExtOpticsTransmission"  : self.Ext_Opt_Trans,
                "EstimatedTransmission"  : self.Est_Trans,
                "Width"                  : self.Width,
                "Height"                 : self.Height,
                "Planck R1"              : self.R,
                "Planck B"               : self.B,
                "Planck F"               : self.F,
                "Planck O"               : -self.J0,
                "Planck R2"              : 1.0/self.J1,
                "alpha 1"                : self.alpha1,
                "alpha 2"                : self.alpha2,
                "beta 1"                 : self.beta1,
                "beta 2"                 : self.beta2
        }
        self.tag_dict = json.dumps(self.tag_dict)

    def update_nuc(self):
        self.device.execute_command("NUCAction")

    def reset_FLIR(self):
        self.device.execute_command("PT1000Reset")

    def picture_timer(self):
        Timer(1, self.picture_timer).start()
        self.raw_thermals()
            
    def nuc_timer(self):
        Timer(self.nuc_int, self.nuc_timer).start()
        print "Update NUC"
        self.update_nuc()
        self.update_tags()

    def buffer_timer(self):
        Timer(self.pic_int, self.buffer_timer).start()
        self.lock.acquire()
        try:
            n_Buffers = self.stream.get_n_buffers()[1]
            for i in range(0,n_Buffers):
                buffer = self.stream.try_pop_buffer()
            self.create_buffer()
        finally:
            self.lock.release()

    def run_camera(self):
        try:
            self.buffer_timer()
            self.picture_timer()
            self.nuc_timer()
        except Exception, err:
            print "Error: %s " % err
	    self.reset_FLIR()
	    os._exit(2)  


def main():
    FLIR = camera()
    FLIR.make_stream()
    FLIR.camera.start_acquisition ()
    FLIR.picture_timer()
    FLIR.buffer_timer()
    FLIR.nuc_timer()



if __name__ == "__main__":
  main()

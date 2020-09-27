
#!/usr/bin/python3

import PyIndi
import cv2
import time
import sys
import getopt
import threading
import io
import numpy as np
from PIL import Image
from astropy.io import fits
import astropy.io.fits as pyfits

class IndiClient(PyIndi.BaseClient):
    def __init__(self):
        super(IndiClient, self).__init__()
    def newDevice(self, d):
        pass
    def newProperty(self, p):
        pass
    def removeProperty(self, p):
        pass
    def newBLOB(self, bp):
        global blobEvent
        print("new BLOB ", bp.name)
        blobEvent.set()
        pass
    def newSwitch(self, svp):
        pass
    def newNumber(self, nvp):
        pass
    def newText(self, tvp):
        pass
    def newLight(self, lvp):
        pass
    def newMessage(self, d, m):
        pass
    def serverConnected(self):
        pass
    def serverDisconnected(self, code):
        pass

def white_balance(img):
    stack = []
    for i in cv2.split(img):
        hist, bins = np.histogram(i, 256, (0, 256))
        # remove colors at each end of the histogram which are used by only by .05% 
        tmp = np.where(hist > hist.sum() * 0.0005)[0]
        i_min = tmp.min()
        i_max = tmp.max()
        # stretch history a bit
        tmp = (i.astype(np.int32) - i_min) / (i_max - i_min) * 255
        tmp = np.clip(tmp, 0, 255)
        stack.append(tmp.astype(np.uint8))
    return np.dstack(stack)

def main(argv):
    global blobEvent
    try:
        opts, args = getopt.getopt(argv,"hb:c:g:e:f:p:")
    except getopt.GetoptError:
        print ('usage: capture.py -c cam -b binding -g gain -e exposure -f fits_filename -p png_filename')
        sys.exit(2)

    if len(opts) == 0:
        print ('usage: capture.py -c cam -b binding -g gain -e exposure -f fits_filename -p png_filename')
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            print ('usage: capture.py -c cam -b binding -g gain -e exposure -f fits_filename -p png_filename')
            sys.exit()
        elif opt in ("-b"):
            binding = arg.strip()
        elif opt in ("-g"):
            gain = arg.strip()
        elif opt in ("-e"):
            exposure = arg.strip()
        elif opt in ("-f"):
            fitsfilename = arg.strip()
        elif opt in ("-p"):
            pngfilename = arg.strip()
        elif opt in ("-c"):
            camname = arg.strip()
    
    print ('binding is ', binding)
    print ('gain is ', gain)
    print ('exposure is ', exposure)
    print ('fits filename is ', fitsfilename)
    print ('png filename is ', pngfilename)

        # connect the server
    indiclient=IndiClient()
    indiclient.setServer("localhost",7624)
    
    if (not(indiclient.connectServer())):
        print("No indiserver running on "+indiclient.getHost()+":"+str(indiclient.getPort())+" - Try to run")
        print("  indiserver indi_simulator_telescope indi_simulator_ccd")
        sys.exit(1)
    
    # Let's take some pictures
    ccd=camname
    device_ccd=indiclient.getDevice(ccd)
    while not(device_ccd):
        time.sleep(0.5)
        device_ccd=indiclient.getDevice(ccd)   
    
    ccd_connect=device_ccd.getSwitch("CONNECTION")
    while not(ccd_connect):
        time.sleep(0.5)
        ccd_connect=device_ccd.getSwitch("CONNECTION")
    if not(device_ccd.isConnected()):
        ccd_connect[0].s=PyIndi.ISS_ON  # the "CONNECT" switch
        ccd_connect[1].s=PyIndi.ISS_OFF # the "DISCONNECT" switch
        indiclient.sendNewSwitch(ccd_connect)
    
    ccd_exposure=device_ccd.getNumber("CCD_EXPOSURE")
    while not(ccd_exposure):
        time.sleep(0.5)
        ccd_exposure=device_ccd.getNumber("CCD_EXPOSURE")
    
    ccd_gain=device_ccd.getNumber("CCD_GAIN")
    while not(ccd_gain):
        time.sleep(0.5)
        ccd_gain=device_ccd.getNumber("CCD_GAIN")

    ccd_binding=device_ccd.getNumber("CCD_BINNING")
    while not(ccd_binding):
        time.sleep(0.5)
        ccd_binding=device_ccd.getNumber("CCD_BINNING")

    print("Current Values:")
    print("Exposure: ", ccd_exposure[0].value)    
    print("Gain: ", ccd_gain[0].value)    
    print("Binding: ", ccd_binding[0].value)    


    # Ensure the CCD simulator snoops the telescope simulator
    # otherwise you may not have a picture of vega
    ccd_active_devices=device_ccd.getText("ACTIVE_DEVICES")
    while not(ccd_active_devices):
        time.sleep(0.5)
        ccd_active_devices=device_ccd.getText("ACTIVE_DEVICES")
    ccd_active_devices[0].text="Telescope Simulator"
    indiclient.sendNewText(ccd_active_devices)
    
    # we should inform the indi server that we want to receive the
    # "CCD1" blob from this device
    indiclient.setBLOBMode(PyIndi.B_ALSO, ccd, "CCD1")
    
    ccd_ccd1=device_ccd.getBLOB("CCD1")
    while not(ccd_ccd1):
        time.sleep(0.5)
        ccd_ccd1=device_ccd.getBLOB("CCD1")
    
    # we use here the threading.Event facility of Python
    # we define an event for newBlob event
    blobEvent=threading.Event()
    blobEvent.clear()
    
    ccd_exposure[0].value=float(exposure)
    indiclient.sendNewNumber(ccd_exposure)

    ccd_gain[0].value=float(gain)
    indiclient.sendNewNumber(ccd_gain)

    ccd_binding[0].value=float(binding)
    indiclient.sendNewNumber(ccd_binding)

    ccd_exposure=device_ccd.getNumber("CCD_EXPOSURE")
    while not(ccd_exposure):
        time.sleep(0.5)
        ccd_exposure=device_ccd.getNumber("CCD_EXPOSURE")
    
    ccd_gain=device_ccd.getNumber("CCD_GAIN")
    while not(ccd_gain):
        time.sleep(0.5)
        ccd_gain=device_ccd.getNumber("CCD_GAIN")

    ccd_binding=device_ccd.getNumber("CCD_BINNING")
    while not(ccd_binding):
        time.sleep(0.5)
        ccd_binding=device_ccd.getNumber("CCD_BINNING")

    print("Set values to:")
    print("Exposure: ", ccd_exposure[0].value)    
    print("Gain: ", ccd_gain[0].value)    
    #print("Temperature: ", ccd_temperature[0].value)    
    print("Binding: ", ccd_binding[0].value)    

    blobEvent.wait()
    for blob in ccd_ccd1:
        print("name: ", blob.name," size: ", blob.size," format: ", blob.format)
        # pyindi-client adds a getblobdata() method to IBLOB item
        # for accessing the contents of the blob, which is a bytearray in Python
        fits=blob.getblobdata()
        # print("fits data type: ", type(fits))

        # write image data to StringIO buffer
        blobfile = io.BytesIO(fits)
        # open a file and save buffer to disk
        with open(fitsfilename, "wb") as f:
            f.write(blobfile.getvalue())

        # Now convert into png
        hdul = pyfits.open(fitsfilename)
        print (hdul.info)
        image_uint16=hdul[0].data
        image_int8 = cv2.normalize(image_uint16, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        image_rgb = cv2.cvtColor(image_int8, cv2.COLOR_BayerGB2RGB)
        cv2.imwrite(pngfilename, white_balance(image_rgb))

if __name__ == "__main__":
   main(sys.argv[1:])
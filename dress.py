from __future__ import print_function,division
from visual import *
import wx
import pyaudio
import numpy
import math
import threading
import serial
import time

def rgbString(red, green, blue):
    return "#%02x%02x%02x" % (red, green, blue)

class Audio:
    def __init__(self):
        self.chunkSize=8192 #1 chunk is 8192 samples 
        #large chunk so that data is not
        #arriving faster than the computers' ability to read the data
        self.format=pyaudio.paInt16 #have a size of 8, a 16 bit int
        self.channels=1
        self.rate=44100 #44100 samples/sec
        self.recordSec=0.1
        self.recording=False
        self.dtype=numpy.int16
        self.currentFreqInMidi=0
        #the frequency that's currently being detected (in midinum)
        self.currentColor="white"

    def setUp(self):
        #processes sound chunk by chunk, much faster than sample by sample
        #self.chunks is the number of chunks we have to process
        self.chunks=int((self.rate*self.recordSec)/self.chunkSize)
        self.samples=int(self.chunkSize*self.chunks)
        if self.chunks==0:
            self.chunks=1
        self.secPerSamples=1.0/self.rate
        self.p=pyaudio.PyAudio()
        self.stream=self.p.open(format=self.format,channels=self.channels,\
                                rate=self.rate,input=True,\
                                frames_per_buffer=self.chunkSize)
        self.audio=numpy.empty(self.samples,dtype=self.dtype)

    def close(self):
        self.p.close(self.stream)

    def fromFreqToMidi(self,freq):
        #Return midi note number from pitch
        #Midi note numbers go from 0-127, middle C is 60. 
        if freq is None:
            return None
        #formula found on Wikipedia on "pitch"
        return 69 + 12 * math.log((freq / 440.0), 2.0)

    #modified from code found on https://pypi.python.org/pypi/SoundAnalyse
    def getLoudness(self,chunk):
        #return value is in dB
        #loudness ranges from -80dB(no sound) to 0dB(maximum loudness)
        #typical silence is -36dB
        data = numpy.array(chunk, dtype=float) / 32768.0
        ms = math.sqrt(numpy.sum(data ** 2.0) / len(data))
        if ms < 10e-8:
            ms = 10e-8
        return 10.0 * math.log(ms, 10.0)

    def getFrequency(self):
        audioString=self.stream.read(self.chunkSize)
        data=numpy.fromstring(audioString,dtype=self.dtype)
        self.loudness=self.getLoudness(data)
        # Take the fft and square each value
        fftData=abs(numpy.fft.rfft(data))**2
        # find the maximum
        which = fftData[1:].argmax() + 1
        # use quadratic interpolation around the max
        if which != len(fftData)-1:
            y0,y1,y2 = numpy.log(fftData[which-1:which+2:])
            x1 = (y2 - y0) * .5 / (2 * y1 - y2 - y0)
            # find the frequency and output it
            freq = (which+x1)*self.rate/self.chunkSize
        else:
            freq = which*self.rate/self.chunkSize
        return self.fromFreqToMidi(freq)

    def record(self):
        for i in range(self.chunks):
            self.audio[i*self.chunkSize:(i+1)*self.chunkSize]=\
                                                        self.getFrequency()
            self.currentFreqInMidi=self.getFrequency()

    def stopRecording(self):
        if self.recording==True:
            self.recording=False
            self.p.terminate()
            self.close()

    def startRecording(self):
        self.setUp()     
        self.record()

    def findRed(self):
        #the lower the frequency, the more red 
        maxMidi=127
        h=maxMidi/(math.pi/2-50/127*math.pi/2)
        if self.currentFreqInMidi<50:
            return 1
        elif self.currentFreqInMidi>100:
            return 0
        else:
            midiFreq=self.currentFreqInMidi
        return math.cos(midiFreq/h)

    def findBlue(self):
        #the higher the frequency, the more blue
        maxMidi=127
        return 2**(self.currentFreqInMidi/maxMidi)-1

    def findGreen(self):
        #midium frequency has the most green
        maxMidi=127
        h=maxMidi/(math.pi-50/127*math.pi)
        if self.currentFreqInMidi<50:
            return 0
        return abs(math.sin(self.currentFreqInMidi/h+50/127*math.pi))

    def findRGB(self):
        maxRgbCode=255
        red=int(maxRgbCode*self.findRed())
        green=int(maxRgbCode*self.findGreen())
        blue=int(maxRgbCode*self.findBlue())
        self.currentColor=rgbString(red,green,blue)
        if red==max(red,green,blue):
            (red,green,blue)=(red,int(green*0.2),int(blue*0.2))
            #red is very hard to show so whenever red dominates
            #we want it to dominate more
        self.r=red
        self.g=green
        self.b=blue

    def findRedIfRedOnly(self):
        #the higher the frequency, the more red 
        maxMidi=127
        h=maxMidi/(math.pi/2)
        rgbCode=math.sin(self.currentFreqInMidi/h)
        return (rgbCode,0,0)

    def findYellow(self):
        #the higher the frequency, the more yellow
        maxMidi=127
        h=maxMidi/(math.pi/2)
        rgbCode=math.sin(self.currentFreqInMidi/h)
        return (rgbCode,rgbCode,0)

    def findGreenIfGreenOnly(self):
        #the higher the frequency, the more green
        maxMidi=127
        h=maxMidi/(math.pi/2)
        rgbCode=math.sin(self.currentFreqInMidi/h)
        return (0,rgbCode,0)

    def findPurple(self):
        #the higher the frequency, the more purple
        maxMidi=127
        h=maxMidi/(math.pi/2)
        rgbCode=math.sin(self.currentFreqInMidi/h)
        return (rgbCode,0,rgbCode)

    def findBlueIfBlueOnly(self):
        #the higher the frequency, the more blue
        maxMidi=127
        h=maxMidi/(math.pi/2)
        rgbCode=math.sin(self.currentFreqInMidi/h)
        return (0,0,rgbCode)       

class Model:
    def __init__(self,rgbColor):
        self.skinColor=(0.93,0.80,0.68)
        self.red=rgbColor[0]
        self.green=rgbColor[1]
        self.blue=rgbColor[2]
        self.axis=(0,0.7,0)
        self.frame=frame()
        self.dressPattern='waterfall'

    def findRGBTuple(self):
        self.rgbColor=(self.red,self.green,self.blue)

    def drawTrunk(self):
        f=self.frame
        cylinder(frame=f,pos=(0,-0.3,0),axis=self.axis,radius=0.05,length=1,\
                 color=self.skinColor)

    def drawHead(self):
        f=self.frame
        sphere(frame=f,pos=(0,0.7,0),radius=0.2,color=self.skinColor)

    def drawLimbs(self):
        f=self.frame
        #arm 1
        curve(frame=f,pos=[(-0.1,0.35,0), (-0.4,0.2,0), (-0.1,0.05,0)],\
              radius=0.05,color=self.skinColor)
        #elbow1
        sphere(frame=f,pos=(-0.4,0.2,0),radius=0.047,color=self.skinColor)
        #arm 2
        curve(frame=f,pos=[(0.1,0.35,0), (0.4,0.2,0),(0.1,0.05,0)],\
              radius=0.05,color=self.skinColor)
        #elbow2
        sphere(frame=f,pos=(0.4,0.2,0),radius=0.047,color=self.skinColor)
        #thigh 1
        curve(frame=f,pos=[(-0.1,-0.3,0),(-0.06,-0.8,0)],radius=0.07,\
              color=self.skinColor)
        #knee 1
        sphere(frame=f,pos=(-0.06,-0.83,0), radius=0.069, \
               color=self.skinColor)
        #calf 1
        ellipsoid(frame=f,pos=(-0.06,-1,0), length=0.11, height=0.6, \
                  width=0.13,color=self.skinColor)
        #foot 1
        ellipsoid(frame=f,pos=(-0.06,-1.27,0.08),length=0.1,height=0.07,\
                  width=0.23,color=color.white)
        #thigh 2
        curve(frame=f,pos=[(0.1,-0.3,0),(0.094,-0.8,0)],radius=0.07,\
              color=self.skinColor)
        #knee 2
        sphere(frame=f,pos=(0.094,-0.83,0), radius=0.069, \
               color=self.skinColor)
        #calf 2
        ellipsoid(frame=f,pos=(0.094,-1,0), length=0.11, height=0.6,\
                  width=0.13,color=self.skinColor)
        #foot 2
        ellipsoid(frame=f,pos=(0.094,-1.27,0.08),length=0.1,height=0.07,\
                  width=0.23,color=color.white)

    def drawDress(self):
        #the white template
        f=self.frame
        ring(frame=f,pos=(0,0.38,0),axis=(0,0.4,0),radius=0.06, thickness=0.05)
        ring(frame=f,pos=(0,0.34,0),axis=(0,0.4,0), radius=0.1, thickness=0.05)
        ring(frame=f,pos=(0,0.28,0),axis=(0,0.4,0), radius=0.13, thickness=0.05)
        ring(frame=f,pos=(0,0.22,0),axis=(0,0.4,0), radius=0.13, thickness=0.05)
        ring(frame=f,pos=(0,0.16,0),axis=(0,0.4,0), radius=0.12, thickness=0.05)
        ring(frame=f,pos=(0,0.1,0), axis=(0,0.4,0), radius=0.11, thickness=0.05)
        ring(frame=f,pos=(0,0.04,0), axis=(0,0.4,0), radius=0.10,thickness=0.05)
        ring(frame=f,pos=(0,-0.02,0),axis=(0,0.4,0), radius=0.10,thickness=0.05)
        ring(frame=f,pos=(0,-0.08,0), axis=(0,0.4,0),radius=0.12,thickness=0.05)
        ring(frame=f,pos=(0,-0.14,0),axis=(0,0.4,0), radius=0.14,thickness=0.05)
        ring(frame=f,pos=(0,-0.2,0),axis=(0,0.4,0), radius=0.16, thickness=0.05)
        ring(frame=f,pos=(0,-0.26,0),axis=(0,0.4,0), radius=0.17,thickness=0.05)
        ring(frame=f,pos=(0,-0.32,0),axis=(0,0.4,0), radius=0.18,thickness=0.05)
        ring(frame=f,pos=(0,-0.38,0),axis=(0,0.4,0), radius=0.18,thickness=0.05)
        ring(frame=f,pos=(0,-0.44,0),axis=(0,0.4,0), radius=0.17,thickness=0.05)

    def drawLabels(self):
        self.title=label(pos=self.axis,color=(1,1,1),\
                         text='Musical Dress Display',\
                            box=False,line=False,opacity=0,xoffset=0,\
                            yoffset=60)

    def drawTopLEDSpiral(self):
        f=self.frame
        self.spiral1=ring(frame=f,pos=(0,0.4,0),axis=(0,0.4,0),radius=0.11, \
                          thickness=0.01,color=self.rgbColor)
        self.spiral2=ring(frame=f,pos=(0,0.37,0),axis=(0,0.4,0),radius=0.14, \
                          thickness=0.01,color=self.rgbColor)
        self.spiral3=ring(frame=f,pos=(0,0.34,0),axis=(0,0.4,0), radius=0.15, \
                          thickness=0.01,color=self.rgbColor)
        self.spiral4=ring(frame=f,pos=(0,0.31,0),axis=(0,0.4,0),radius=0.17, \
                          thickness=0.01,color=self.rgbColor)
        self.spiral5=ring(frame=f,pos=(0,0.28,0),axis=(0,0.4,0), radius=0.18, \
                          thickness=0.01,color=self.rgbColor)
        self.spiral6=ring(frame=f,pos=(0,0.25,0),axis=(0,0.4,0),radius=0.18, \
                          thickness=0.01,color=self.rgbColor)
        self.spiral7=ring(frame=f,pos=(0,0.22,0),axis=(0,0.4,0), radius=0.18, \
                          thickness=0.01,color=self.rgbColor)
        self.spiral8=ring(frame=f,pos=(0,0.19,0),axis=(0,0.4,0),radius=0.17, \
                          thickness=0.01,color=self.rgbColor)
        self.spiral9=ring(frame=f,pos=(0,0.16,0),axis=(0,0.4,0), radius=0.17, \
                          thickness=0.01,color=self.rgbColor)
        self.spiral10=ring(frame=f,pos=(0,0.13,0),axis=(0,0.4,0),radius=0.17, \
                           thickness=0.01,color=self.rgbColor)
        self.spiral11=ring(frame=f,pos=(0,0.1,0), axis=(0,0.4,0), radius=0.16, \
                           thickness=0.01,color=self.rgbColor)

    def drawWaistLEDSpiral(self):
        f=self.frame
        self.spiral12=ring(frame=f,pos=(0,0.07,0),axis=(0,0.4,0),radius=0.16,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral13=ring(frame=f,pos=(0,0.04,0), axis=(0,0.4,0),radius=0.16,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral14=ring(frame=f,pos=(0,0.01,0),axis=(0,0.4,0),radius=0.16, \
                           thickness=0.01,color=self.rgbColor)
        self.spiral15=ring(frame=f,pos=(0,-0.02,0),axis=(0,0.4,0), radius=0.16,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral16=ring(frame=f,pos=(0,-0.05,0),axis=(0,0.4,0),radius=0.17,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral17=ring(frame=f,pos=(0,-0.08,0), axis=(0,0.4,0),radius=0.18,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral18=ring(frame=f,pos=(0,-0.11,0),axis=(0,0.4,0),radius=0.19, \
                           thickness=0.01,color=self.rgbColor)
        self.spiral19=ring(frame=f,pos=(0,-0.14,0),axis=(0,0.4,0), radius=0.19,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral20=ring(frame=f,pos=(0,-0.11,0),axis=(0,0.4,0),radius=0.19, \
                           thickness=0.01,color=self.rgbColor)
        self.spiral21=ring(frame=f,pos=(0,-0.14,0),axis=(0,0.4,0), radius=0.2,\
                           thickness=0.01,color=self.rgbColor)

    def drawBottomLEDSpiral(self):
        f=self.frame
        self.spiral22=ring(frame=f,pos=(0,-0.17,0),axis=(0,0.4,0),radius=0.21, \
                           thickness=0.01,color=self.rgbColor)
        self.spiral23=ring(frame=f,pos=(0,-0.2,0),axis=(0,0.4,0), radius=0.22,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral24=ring(frame=f,pos=(0,-0.23,0),axis=(0,0.4,0),radius=0.22, \
                           thickness=0.01,color=self.rgbColor)
        self.spiral25=ring(frame=f,pos=(0,-0.26,0),axis=(0,0.4,0), radius=0.225,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral26=ring(frame=f,pos=(0,-0.29,0),axis=(0,0.4,0),radius=0.23, \
                           thickness=0.01,color=self.rgbColor)
        self.spiral27=ring(frame=f,pos=(0,-0.32,0),axis=(0,0.4,0), radius=0.23,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral28=ring(frame=f,pos=(0,-0.35,0),axis=(0,0.4,0),radius=0.23, \
                           thickness=0.01,color=self.rgbColor)
        self.spiral29=ring(frame=f,pos=(0,-0.38,0),axis=(0,0.4,0), radius=0.228,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral30=ring(frame=f,pos=(0,-0.41,0),axis=(0,0.4,0),radius=0.228,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral31=ring(frame=f,pos=(0,-0.44,0),axis=(0,0.4,0), radius=0.224,\
                           thickness=0.01,color=self.rgbColor)
        self.spiral32=ring(frame=f,pos=(0,-0.47,0),axis=(0,0.4,0),radius=0.22, \
                           thickness=0.01,color=self.rgbColor)

    def gatherLEDSpirals(self):
        self.LEDSpirals=[self.spiral1,self.spiral2,self.spiral3,self.spiral4,\
                         self.spiral5,self.spiral6,self.spiral7,self.spiral8,\
                         self.spiral9,self.spiral10,self.spiral11,self.spiral12,\
                         self.spiral13,self.spiral14,self.spiral15,\
                         self.spiral16,self.spiral17,self.spiral18,\
                         self.spiral19,self.spiral20,self.spiral21,\
                         self.spiral22,self.spiral23,self.spiral24,\
                         self.spiral25,self.spiral26,self.spiral27,\
                         self.spiral28,self.spiral29,self.spiral30,\
                         self.spiral31,self.spiral32]

    def drawLEDSpirals(self):
        #when lightup mode is 'waterfall'
        self.findRGBTuple()
        self.drawTopLEDSpiral()
        self.drawWaistLEDSpiral()
        self.drawBottomLEDSpiral()
        self.gatherLEDSpirals()

    def drawLEDPoints1(self):
        f=self.frame
        self.points1=points(frame=f,\
                           pos=[(-0.1,0.35,0.115),(0.1,0.35,0.115),\
                                (0.1,0.35,-0.115),(-0.1,0.35,-0.115)],\
                           color=self.rgbColor)
        self.points2=points(frame=f,\
                            pos=[(-0.165,0.3,0.055),(-0.1,0.3,0.15),\
                                 (0.1,0.3,0.15),(0.165,0.3,0.055),\
                                 (0.165,0.3,-0.055),(0.1,0.3,-0.15),\
                                 (-0.1,0.3,-0.15),(-0.165,0.3,-0.055)],\
                            color=self.rgbColor)
        self.points3=points(frame=f,\
                            pos=[(-0.18,0.25,0),(-0.17,0.25,0.065),\
                                 (-0.1,0.25,0.15),(0,0.25,0.185),\
                                 (0.1,0.25,0.15),(0.17,0.25,0.065),\
                                 (0.18,0.25,0),(0.17,0.25,-0.065),\
                                 (0.1,0.25,-0.15),(0,0.25,-0.185),\
                                 (-0.1,0.25,-0.15),(-0.17,0.25,-0.065)],\
                            color=self.rgbColor)

    def drawLEDPoints2(self):
        f=self.frame
        self.points4=points(frame=f,\
                            pos=[(-0.18,0.2,0),(-0.17,0.2,0.065),\
                                 (-0.1,0.2,0.15),(0,0.2,0.185),\
                                 (0.1,0.2,0.15),(0.17,0.2,0.065),\
                                 (0.18,0.2,0),(0.17,0.2,-0.065),\
                                 (0.1,0.2,-0.15),(0,0.2,-0.185),\
                                 (-0.1,0.2,-0.15),(-0.17,0.2,-0.065)],\
                            color=self.rgbColor)
        self.points5=points(frame=f,\
                            pos=[(-0.16,0.15,0.078),(-0.1,0.15,0.14),\
                                 (0,0.15,0.172),(0.1,0.15,0.14),\
                                 (0.16,0.15,0.078),(0.16,0.15,-0.078),\
                                 (0.1,0.15,-0.14),(0,0.15,-0.172),\
                                 (-0.1,0.15,-0.14),(-0.16,0.15,-0.078)],\
                            color=self.rgbColor)
        self.points6=points(frame=f,\
                            pos=[(-0.15,0.1,0.062),(-0.1,0.1,0.13),\
                                 (0,0.1,0.165),(0.1,0.1,0.13),\
                                 (0.15,0.1,0.062),(0.15,0.1,-0.062),\
                                 (0.1,0.1,-0.13),(0,0.1,-0.165),\
                                 (-0.1,0.1,-0.13),(-0.15,0.1,-0.062)],\
                            color=self.rgbColor)

    def drawLEDPoints3(self):
        f=self.frame
        self.points7=points(frame=f,\
                            pos=[(-0.14,0.05,0.07),(-0.1,0.05,0.11),\
                                 (-0.05,0.05,0.145),(0,0.05,0.15),\
                                 (0.05,0.05,0.145),(0.1,0.05,0.11),\
                                 (0.14,0.05,0.07),(0.14,0,-0.07),\
                                 (0.1,0.05,-0.11),(0.05,0.05,-0.14),\
                                 (0,0.05,-0.15),(-0.05,0.05,-0.14),\
                                 (-0.1,0.05,-0.11),(-0.14,0.05,-0.07)],\
                            color=self.rgbColor)
        self.points8=points(frame=f,\
                            pos=[(-0.15,0,0),(-0.14,0,0.07),(-0.1,0,0.11),\
                                 (-0.05,0,0.14),(0,0,0.14),(0.05,0,0.14),\
                                 (0.1,0,0.11),(0.14,0,0.07),(0.15,0,0),\
                                 (0.14,0,-0.07),(0.1,0,-0.11),(0.05,0,-0.14),\
                                 (0,0,-0.14),(-0.05,0,-0.14),(-0.1,0,-0.11),\
                                 (-0.14,0,-0.07)],\
                            color=self.rgbColor)
        self.points9=points(frame=f,\
                            pos=[(-0.15,-0.05,0.062),(-0.1,-0.05,0.13),\
                                 (0,-0.05,0.16),(0.1,-0.05,0.13),\
                                 (0.15,-0.05,0.062),(0.15,-0.05,-0.062),\
                                 (0.1,-0.05,-0.13),(0,-0.05,-0.16),\
                                 (-0.1,-0.05,-0.13),(-0.15,-0.05,-0.062)],\
                            color=self.rgbColor)

    def drawLEDPoints4(self):
        f=self.frame
        self.points10=points(frame=f,\
                             pos=[(-0.173,-0.08,0),(-0.14,-0.08,0.1),\
                                  (-0.06,-0.08,0.165),(0.06,-0.08,0.165),\
                                  (0.14,-0.08,0.1),(0.173,-0.08,0),\
                                  (0.14,-0.08,-0.1),(0.06,-0.08,-0.165),\
                                  (-0.06,-0.08,-0.165),(-0.14,-0.08,-0.1)],\
                             color=self.rgbColor)
        self.points11=points(frame=f,\
                             pos=[(-0.17,-0.12,0.065),(-0.12,-0.12,0.15),\
                                  (0,-0.12,0.19),(0.12,-0.12,0.15),\
                                  (0.17,-0.12,0.065),(0.17,-0.12,-0.065),\
                                  (0.12,-0.12,-0.15),(0,-0.12,-0.19),\
                                  (-0.12,-0.12,-0.15),(-0.17,-0.12,-0.065)],\
                             color=self.rgbColor)
        self.points12=points(frame=f,\
                             pos=[(-0.195,-0.15,0),(-0.16,-0.15,0.115),\
                                  (-0.07,-0.15,0.19),(0.07,-0.15,0.19),\
                                  (0.16,-0.15,0.115),(0.195,-0.15,0),\
                                  (0.16,-0.15,-0.115),(0.07,-0.15,-0.19),\
                                  (-0.07,-0.15,-0.19),(-0.16,-0.15,-0.115)],\
                             color=self.rgbColor)

    def drawLEDPoints5(self):
        f=self.frame
        self.points13=points(frame=f,\
                             pos=[(-0.19,-0.18,0.07),(-0.13,-0.18,0.16),\
                                  (0,-0.18,0.21),(0.13,-0.18,0.16),\
                                  (0.19,-0.18,0.07),(0.19,-0.18,-0.07),\
                                  (0.13,-0.18,-0.16),(0,-0.18,-0.21),\
                                  (-0.13,-0.18,-0.16),(-0.19,-0.18,-0.07)],\
                             color=self.rgbColor)
        self.points14=points(frame=f,\
                             pos=[(-0.21,-0.21,0),(-0.18,-0.21,0.125),\
                                  (-0.075,-0.21,0.2),(0.075,-0.21,0.2),\
                                  (0.18,-0.21,0.125),(0.21,-0.21,0),\
                                  (0.18,-0.21,-0.125),(0.075,-0.21,-0.2),\
                                  (-0.075,-0.21,-0.2),(-.18,-0.21,-0.125)],\
                             color=self.rgbColor)
        self.points15=points(frame=f,\
                             pos=[(-0.205,-0.24,0.07),(-0.14,-0.24,0.18),\
                                  (0,-0.24,0.22),(0.14,-0.24,0.18),\
                                  (0.205,-0.24,0.07),(0.205,-0.24,-0.07),\
                                  (0.14,-0.24,-0.18),(0,-0.24,-0.22),\
                                  (-.14,-0.24,-0.18),(-0.205,-0.24,-0.07)],\
                             color=self.rgbColor)

    def drawLEDPoints6(self):
        f=self.frame
        self.points16=points(frame=f,\
                             pos=[(-0.205,-0.29,0.075),(-0.145,-0.29,0.18),\
                                  (0,-0.29,0.22),(0.145,-0.29,0.18),\
                                  (0.205,-0.29,0.075),(0.205,-0.29,-0.075),\
                                  (0.145,-0.29,-0.18),(0,-0.29,-0.22),\
                                  (-.145,-0.29,-0.18),(-.205,-.29,-0.075)],\
                             color=self.rgbColor)

    def gatherLEDPoints(self):
        self.LEDPoints=[self.points1,self.points2,self.points3,\
                        self.points4,self.points5,self.points6,\
                        self.points7,self.points8,self.points9,\
                        self.points10,self.points11,self.points12,\
                        self.points13,self.points14,self.points15,\
                        self.points16]

    def drawLEDPoints(self):
        #when lightup mode is 'fireworks'
        self.findRGBTuple()
        self.drawLEDPoints1()
        self.drawLEDPoints2()
        self.drawLEDPoints3()
        self.drawLEDPoints4()
        self.drawLEDPoints5()
        self.drawLEDPoints6()
        self.gatherLEDPoints()

    def draw(self):
        self.drawTrunk()
        self.drawDress()
        self.drawHead()
        self.drawLimbs()
        self.drawLabels()
        self.drawLEDSpirals()
        self.drawLEDPoints()
        for point in self.LEDPoints:
            point.visible=False


class Bars:
    def __init__(self,rgbColor,loudness):
        self.red=rgbColor[0]
        self.green=rgbColor[1]
        self.blue=rgbColor[2]
        self.frame=frame()
        self.axis=(0,1,0)
        self.loudness=loudness
        self.rgbSum=self.red+self.green+self.blue

    def drawRedBar(self):
        self.redBar=cylinder(frame=self.frame,pos=(-1,-2,0),\
                             axis=(0,self.red*10,0),\
                 radius=1,color=color.red,length=self.red*10,\
                             opacity=self.loudness)

    def drawGreenBar(self):
        self.greenBar=cylinder(frame=self.frame,pos=(1,-2,0),\
                               axis=(0,self.green*10,0),\
                 radius=1,color=color.green,length=self.green*10,\
                               opacity=self.loudness)

    def drawBlueBar(self):
        self.blueBar=cylinder(frame=self.frame,pos=(0,-2,-(3**0.5)),\
                              axis=(0,self.blue*10,0),\
                 radius=1,color=color.blue,length=self.blue*10,\
                              opacity=self.loudness)
        
    def drawLabels(self):
        self.redLabel=label(pos=self.axis,color=(1,1,1),text='% of red',\
                            box=False,line=False,opacity=0,xoffset=-60,\
                            yoffset=-60)
        self.redness=label(pos=self.axis,color=(1,1,1),\
                           text='%0.2f'%(self.red/self.rgbSum*100)+'%',\
                            box=False,line=False,opacity=0,xoffset=20,\
                            yoffset=-60)
        self.blueLabel=label(pos=self.axis,color=(1,1,1),text='% of blue',\
                             box=False,line=False,opcaity=0,xoffset=-58,\
                             yoffset=-80)
        self.blueness=label(pos=self.axis,color=(1,1,1),\
                            text='%0.2f'%(self.green/self.rgbSum*100)+'%',\
                             box=False,line=False,opcaity=0,xoffset=20,\
                             yoffset=-80)
        self.greenLabel=label(pos=self.axis,color=(1,1,1),text='% of green',\
                              box=False,line=False,opacity=0,xoffset=-53,\
                              yoffset=-100)
        self.greenness=label(pos=self.axis,color=(1,1,1),\
                             text='%0.2f'%(self.blue/self.rgbSum*100)+'%',\
                              box=False,line=False,opacity=0,xoffset=20,\
                              yoffset=-100)

    def draw(self):
        self.drawRedBar()
        self.drawGreenBar()
        self.drawBlueBar()
        self.drawLabels()

class Window:
    def __init__(self,data):
        self.w=data.w
        self.L=data.L #half the length of the window
        self.margin=data.margin
        self.p=self.w.panel
        #the full region of the window in which to place widgets
        self.p.SetBackgroundColour('#000000') #black

    def staticTexts1(self):
        self.frequencyDetectorText=wx.StaticText(self.p,\
                      pos=(1.6*self.L,self.L*0.4),\
                      label="Frequency Detector")
        self.frequencyDetectorText.SetFont(wx.Font(22,wx.SCRIPT,wx.NORMAL,\
                                                   wx.BOLD))
        self.frequencyDetectorText.SetForegroundColour((255,255,255))
        self.barsText=wx.StaticText(self.p,\
                                    pos=(1.5*(self.L+self.margin*2),\
                                         self.L-self.margin*3),\
                                    label="Red,Green,Blue Distribution")
        self.barsText.SetForegroundColour((255,255,255))
        self.detectFreqText=wx.StaticText(self.p,\
                            pos=(self.L,self.margin*5),\
                            label="Detect Sound Frequency")
        self.detectFreqText.SetForegroundColour((255,255,255))
        self.detectFreqText.SetFont(wx.Font(16,wx.SCRIPT,wx.NORMAL,\
                                                   wx.BOLD))
    def staticTexts2(self):
        self.dressPatternText=wx.StaticText(self.p,\
                                        pos=(self.margin*2.5,self.margin),\
                                        label='Choose a Dress Pattern')
        self.dressPatternText.SetForegroundColour((255,255,255))
        self.colorModeText=wx.StaticText(self.p,\
                                pos=(self.L+self.margin/5,self.margin),\
                                label='Choose a Color Mode ')
        self.colorModeText.SetForegroundColour((255,255,255))
        self.modeText=wx.StaticText(self.p,\
                                    pos=(self.L*1.8,self.margin),\
                                    label="Choose a Light-up Mode")
        self.modeText.SetForegroundColour((255,255,255))
        self.dressText=wx.StaticText(self.p,\
                                     pos=(self.L*1.63,self.L*1.74),\
                                     label='Choose a Light-up Mode')
        self.dressText.SetForegroundColour((255,255,255))

    def staticTexts(self):
        self.staticTexts1()
        self.staticTexts2()
        
    def freqText(self,data):
        self.fText=wx.StaticText(self.p,pos=\
                                (1.54*self.L,self.L*0.5)\
                                 ,label='')
        self.fText.SetFont(wx.Font(74, wx.MODERN,wx.NORMAL,wx.BOLD))

    def displayCheckBox(self):
        self.checkBox=wx.CheckBox(self.p,label="",\
                                  pos=(self.L-self.margin*1.5,self.margin*5))

    def displayComboBox(self):
        choices=['Select Color Mode','Red Only Mode','Yellow Only Mode',\
                 'Green Only Mode','Purple Only Mode','Blue Only Mode',\
                 'Multicolor Mode']
        self.comboBox=wx.ComboBox(self.p,choices=choices,pos=\
                                  (self.L-self.margin/2,self.margin*2.2))

    def displayRadioBox(self):
        choices1=['Waterfall Pattern','Fireworks Pattern']
        self.radioBox1=wx.RadioBox(self.p,choices=choices1,\
                                  pos=(self.margin,self.margin*2),
                                  style=wx.RA_SPECIFY_ROWS,\
                                  size=(self.L/1.5,self.L/4.5))
        self.radioBox1.SetBackgroundColour((255,255,255))
        choices2=['Dropping Mode','Expanding Mode']
        self.radioBox2=wx.RadioBox(self.p,choices=choices2,\
                                   pos=(self.L*1.7,self.margin*2),\
                                   style=wx.RA_SPECIFY_ROWS,\
                                   size=(self.L/1.5,self.L/4.5))
        self.radioBox2.SetBackgroundColour((255,255,255))
        choices3=['Demo Mode','Current Mode']
        self.radioBox3=wx.RadioBox(self.p,choices=choices3,\
                                   pos=(self.L*1.6,self.L*1.8),\
                                   style=wx.RA_SPECIFY_ROWS,\
                                   size=(self.L/2,self.L/5))
        self.radioBox3.SetBackgroundColour((255,255,255))

    def displayShowDressButton(self):
        self.showDressButton=wx.Button(self.p,pos=(self.L*2.18,self.L*1.85),\
                                  label="Light Up!")
        
    def display(self,data):
        self.displayCheckBox()
        self.displayComboBox()
        self.displayRadioBox()
        self.displayShowDressButton()
        self.staticTexts()
        self.freqText(data)

def initArduino(data):
    #set up pins
    data.pinDict={'row1':([2],[3],[4]),'row2':([5],[6],[7]),'row3':([8],[10],[9]),\
       'row4':([11],[12],[14]),'row5':([15],[16],[17]),\
       'row6':([18,21],[19,22],[20,23]),'row7':([24,27],[25,28],[26,29]),\
       'row8':([30],[31],[32]),'row9':([33],[34],[35]),\
       'row10':([36],[37],[38]),'row11':([39],[40],[41]),\
       'row12':([42],[43],[44]),'row13':([45],[46],[47]),\
       'row14':([48],[49],[50])}
    data.ser=serial.Serial('/dev/cu.usbmodem1411',9600)
    time.sleep(2) #wait for everything to initialize

def initData(data):
    data.L=320
    data.margin=20
    data.sound=Audio()
    #anything below -50db is definitely silence
    #data.loudness: a scale of loudness from 0(no sound) to 1(maximum sound)
    #begin with 0.375, which is silence
    data.loudness=0.375
    data.loudnessInterval=9
    data.detectedFreqList=[]
    data.colorModeSelected=False
    data.colorMode=None
    data.mode='dropping'
    data.rgbColor=(1,1,1)
    data.dressShow=False
    data.dressMode='demo'
    data.i=0
    data.dress=Dress()

def initWindow(data):
    initData(data)
    data.w=window(width=2.5*(data.L+window.dwidth),\
                  height=2*(data.L+window.dheight+window.menuheight),\
                  menus=True,title='Musical Garment',\
                  style=wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX|\
                  wx.FRAME_EX_METAL)
    data.screen1=display(window=data.w,x=0,y=data.margin*6,\
                         width=data.L*1.5,height=data.L*1.6,\
                         forward=-vector(0,0,4))
    data.screen2=display(window=data.w,x=1.6*data.L,\
                         y=data.L*0.9,\
                         width=data.L-4*data.margin,\
                         height=data.L-4*data.margin,\
                         forward=-vector(0,0.15,-0.1))
    data.window=Window(data)
    data.window.display(data) #all the widgets
    data.screen1.select()
    data.model=Model(data.rgbColor)
    data.model.draw()
    data.screen2.select()
    data.bars=Bars(data.rgbColor,data.loudness)
    #loudness determines the bars' opacity
    data.bars.draw()

def calculateLoudness(data):
    #typical loundness ranges from -80dB to 0dB
    #make the loudness value positive by adding 80
    #now the higher the value, the louder
    positiveLoudness=data.sound.loudness+80
    silence=30
    maxLoudness=80
    data.loudness=positiveLoudness/80
    #determine qualitatively how loud a sound is
    #the louder, the smaller the loudness level
    if positiveLoudness<=silence:
        loudnessLevel=5
    elif silence<positiveLoudness<=\
         silence+2*data.loudnessInterval:
        loudnessLevel=3
    else:
        loudnessLevel=1
    return loudnessLevel

def mousePressed(data):
    def toggleAudio(evt):
        choice=data.window.checkBox.GetValue()
        if choice==False:
            data.sound.stopRecording()
        else:
            data.sound.recording=True

    def selectDressPattern(evt):
        choice=data.window.radioBox1.GetSelection()
        if choice==0:
            data.detectedFreqList=[] #turn the dress white
            if data.model.dressPattern=='fireworks':
                for point in data.model.LEDPoints:
                    point.visible=False
            data.model.dressPattern='waterfall'
            for spiral in data.model.LEDSpirals:
                spiral.visible=True
        else:
            data.detectedFreqList=[] #turn the dress white
            if data.model.dressPattern=='waterfall':
                for spiral in data.model.LEDSpirals:
                    spiral.visible=False 
            data.model.dressPattern='fireworks'
            for point in data.model.LEDPoints:
                point.visible=True

    def selectMode(evt):
        choice=data.window.radioBox2.GetSelection()
        if choice==0:
            data.detectedFreqList=[]
            data.mode='dropping'
        if choice==1:
            data.detectedFreqList=[]
            data.mode='expanding'

    def selectColorMode(evt):
        choice=data.window.comboBox.GetSelection()
        if choice==0:
            data.colorModeSelected=False
        else:
            data.colorModeSelected=True
            if choice==1:
                data.colorMode='red'
            elif choice==2:
                data.colorMode='yellow'
            elif choice==3:
                data.colorMode='green'
            elif choice==4:
                data.colorMode='purple'
            elif choice==5:
                data.colorMode='blue'
            elif choice==6:
                data.colorMode='multicolor'

    def selectDressMode(evt):
        choice=data.window.radioBox3.GetSelection()
        if choice==0:
            data.dressMode='demo'
        else:
            data.dressMode=data.mode

    def lightUp(evt):
        data.w.visible=False #hide the main window
        runDress(data)

    data.window.checkBox.Bind(wx.EVT_CHECKBOX, toggleAudio)
    data.window.radioBox1.Bind(wx.EVT_RADIOBOX,selectDressPattern)
    data.window.radioBox2.Bind(wx.EVT_RADIOBOX,selectMode)
    data.window.comboBox.Bind(wx.EVT_COMBOBOX,selectColorMode)
    data.window.showDressButton.Bind(wx.EVT_BUTTON,lightUp)
    data.window.radioBox3.Bind(wx.EVT_RADIOBOX,selectDressMode)

def determineRgbBasingOnMode(data):
    #rgbcodes are different for each color mode
    if data.colorMode=='red':
        data.rgbColor=data.sound.findRedIfRedOnly()
    elif data.colorMode=='yellow':
        data.rgbColor=data.sound.findYellow()
    elif data.colorMode=='green':
        data.rgbColor=data.sound.findGreenIfGreenOnly()
    elif data.colorMode=='purple':
        data.rgbColor=data.sound.findPurple()
    elif data.colorMode=='blue':
        data.rgbColor=data.sound.findBlueIfBlueOnly()
    elif data.colorMode=='multicolor':
        data.rgbColor=(data.sound.findRed(),data.sound.findGreen(),\
                       data.sound.findBlue())

def findCurrentColor(data):
    if data.colorMode!='multicolor':
        (i,j,k)=data.rgbColor
        currentColor=(i*255,j*255,k*255)
    else:
        currentColor=data.sound.currentColor
    return currentColor
        
def showDetectedFrequency(data):
    data.window.fText.SetLabel("%0.2f"%data.sound.currentFreqInMidi)
    #the color of the text is black so that the background color can be
    #easily seen
    data.window.fText.SetForegroundColour((0,0,0))
    #background corresponds to the frequency detected
    if data.model.dressPattern!=None and data.colorModeSelected==True:
        data.window.fText.SetBackgroundColour(findCurrentColor(data))
    else:
        data.window.fText.SetBackgroundColour((255,255,255))

def gatherDetectedFreq(data):
    if data.mode=='dropping':
        droppingGatherDetectedFreq(data)
    elif data.mode=='expanding':
        expandingGatherDetectedFreq(data)

def droppingGatherDetectedFreq(data):
    #get new frequency, delete an old frequency
    if data.model.dressPattern=='waterfall':
        numberOfHoops=32 #32 circuits
        if len(data.detectedFreqList)==numberOfHoops:
            data.detectedFreqList=data.detectedFreqList[1:]+[data.rgbColor]
        else:
            data.detectedFreqList.append(data.rgbColor)
    elif data.model.dressPattern=='fireworks':
        numberOfHoops=16 #16 circuits
        if len(data.detectedFreqList)==numberOfHoops:
            data.detectedFreqList=data.detectedFreqList[1:]+[data.rgbColor]
        else:
            data.detectedFreqList.append(data.rgbColor)

def expandingGatherDetectedFreq(data):
    #the top row is the newest frequency detected and so on
    if data.model.dressPattern=='waterfall':
        bottomNumberOfHoops=18
        if len(data.detectedFreqList)==bottomNumberOfHoops:
            data.detectedFreqList=data.detectedFreqList[1:]+[data.rgbColor]
        else:
            data.detectedFreqList.append(data.rgbColor)
    elif data.model.dressPattern=='fireworks':
        bottomNumberOfHoops=9
        if len(data.detectedFreqList)==bottomNumberOfHoops:
            data.detectedFreqList=data.detectedFreqList[1:]+[data.rgbColor]
        else:
            data.detectedFreqList.append(data.rgbColor)
        
def dressChangeColor(data):
    n=len(data.detectedFreqList)
    step=calculateLoudness(data)
    if data.mode=='dropping':
        droppingDressChangeColor(data,n)
    elif data.mode=='expanding':
        expandingDressChangeColor(data,n)

def droppingDressChangeColor(data,n):
    if data.model.dressPattern=='waterfall':
        for i in range(0,n):
            data.model.LEDSpirals[i].color=data.detectedFreqList[n-i-1]
    elif data.model.dressPattern=='fireworks':
        for i in range(0,n):
            data.model.LEDPoints[i].color=data.detectedFreqList[n-i-1]

def expandingDressChangeColor(data,n):
    #similar to doppingChangeColor but loops differently
    if data.model.dressPattern=='waterfall':
        topNumberOfHoops,totalHoops=14,32
        #expand towards top
        j=0
        for i in range(topNumberOfHoops-1,-1,-1):
            if j>=n: break
            data.model.LEDSpirals[i].color=data.detectedFreqList[n-j-1]
            j+=1
        #expand towards bottom
        j=0
        for i in range(topNumberOfHoops,totalHoops):
            if j>=n: break
            data.model.LEDSpirals[i].color=data.detectedFreqList[n-j-1]
            j+=1
    elif data.model.dressPattern=='fireworks':
        topNumberOfHoops,totalHoops=7,16
        #expand towards top
        j=0
        for i in range(topNumberOfHoops-1,-1,-1):
            if j>=n: break
            data.model.LEDPoints[i].color=data.detectedFreqList[n-j-1]
            j+=1
        #expand towards bottom
        j=0
        for i in range(topNumberOfHoops,totalHoops):
            if j>=n: break
            data.model.LEDPoints[i].color=data.detectedFreqList[n-j-1]
            j+=1

def dressChange(data):
    data.screen1.select()
    gatherDetectedFreq(data)
    dressChangeColor(data)
    
def barsChangeHeight(data):
    #height changes with frequency
    data.bars.redBar.axis=(0,data.rgbColor[0]*10,0)
    data.bars.redBar.height=data.rgbColor[0]
    data.bars.greenBar.axis=(0,data.rgbColor[1]*10,0)
    data.bars.greenBar.height=data.rgbColor[1]
    data.bars.blueBar.axis=(0,data.rgbColor[2]*10,0)
    data.bars.blueBar.height=data.rgbColor[2]

def barsChangeOpacity(data):
    #opacity changes with loudness
    data.bars.redBar.opacity=data.loudness
    data.bars.greenBar.opacity=data.loudness
    data.bars.blueBar.opacity=data.loudness

def barsChangeLabel(data):
    rgbSum=data.rgbColor[0]+data.rgbColor[1]+data.rgbColor[2]
    data.bars.redness.text='%0.2f'%(data.rgbColor[0]/rgbSum*100)+'%'
    data.bars.greenness.text='%0.2f'%(data.rgbColor[1]/rgbSum*100)+'%'
    data.bars.blueness.text='%0.2f'%(data.rgbColor[2]/rgbSum*100)+'%'

def barsChange(data):
    data.screen2.select()
    barsChangeHeight(data)
    barsChangeOpacity(data)
    barsChangeLabel(data)

def runDress(data):
    if data.dressMode=='demo':
        data.dress.dressDemo()
    elif data.dressMode=='dropping':
        data.dress.dressLightUpInMode1()
    elif data.dressMode=='expanding':
        data.dress.dressLightUpInMode2()

class Dress:
    def __init__(self):
        self.audio=Audio()
        self.initArduino()

    def initArduino(self):
        #set up pins
        self.pinDict={'row1':([2],[3],[4]),'row2':([5],[6],[7]),\
                      'row3':([8],[10],[9]),'row4':([11],[12],[14]),\
                      'row5':([15],[16],[17]),'row6':([18,21],[19,22],[20,23]),\
                      'row7':([24,27],[25,28],[26,29]),'row8':([30],[31],[32]),\
                      'row9':([33],[34],[35]),'row10':([36],[37],[38]),\
                      'row11':([39],[40],[41]),'row12':([42],[43],[44]),\
                      'row13':([45],[46],[47]),'row14':([48],[49],[50])}
        self.ser=serial.Serial('/dev/cu.usbmodem1411',9600)
        time.sleep(2) #wait for everything to initialize

    def dressDemo(self):
        self.mode='demo'
        while True:
            self.redBottomUp()
            self.greenTopDown()
            self.blueBottomUp()
            self.redTopDown()
            self.greenBottomUp()
            self.blueTopDown()

    def redBottomUp(self):
        (r,g,b)=(255,0,0)
        d=self.pinDict
        ser=self.ser
        for i in range(13,-1,-1):
            row='row'+str(i+1)
            if len(d[row][0])==1: #other areas
                ser.write(str(d[row][0][0])+" "+str(r)+' '+str(d[row][1][0])+" "\
                      +str(g)+' '+str(d[row][2][0])+" "+str(b)+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+'0'+' '+str(d[row][1][0])+" "\
                      +'0'+' '+str(d[row][2][0])+" "+'0'+'\n')

            else: #waistband
                ser.write(str(d[row][0][0])+" "+\
                                str(r)+' '+str(d[row][1][0])+" "+str(g)+' '+\
                                str(d[row][2][0])+" "+str(b)+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+\
                                '0'+' '+str(d[row][1][0])+" "+'0'+' '+\
                                str(d[row][2][0])+" "+'0'+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
            time.sleep(0.25)

    def greenTopDown(self):
        d=self.pinDict
        ser=self.ser
        (r,g,b)=(0,255,0)
        for i in range(14):
            row='row'+str(i+1)
            if len(d[row][0])==1: #other areas
                ser.write(str(d[row][0][0])+" "+str(r)+' '+str(d[row][1][0])+" "\
                      +str(g)+' '+str(d[row][2][0])+" "+str(b)+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+'0'+' '+str(d[row][1][0])+" "\
                      +'0'+' '+str(d[row][2][0])+" "+'0'+'\n')

            else: #waistband
                ser.write(str(d[row][0][0])+" "+\
                                str(r)+' '+str(d[row][1][0])+" "+str(g)+' '+\
                                str(d[row][2][0])+" "+str(b)+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+\
                                '0'+' '+str(d[row][1][0])+" "+'0'+' '+\
                                str(d[row][2][0])+" "+'0'+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')

            time.sleep(0.25)

    def blueBottomUp(self):
        d=self.pinDict
        ser=self.ser
        (r,g,b)=(0,0,255)
        for i in range(13,-1,-1):
            row='row'+str(i+1)
            if len(d[row][0])==1: #other areas
                ser.write(str(d[row][0][0])+" "+str(r)+' '+str(d[row][1][0])+" "\
                      +str(g)+' '+str(d[row][2][0])+" "+str(b)+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+'0'+' '+str(d[row][1][0])+" "\
                      +'0'+' '+str(d[row][2][0])+" "+'0'+'\n')

            else: #waistband
                ser.write(str(d[row][0][0])+" "+\
                                str(r)+' '+str(d[row][1][0])+" "+str(g)+' '+\
                                str(d[row][2][0])+" "+str(b)+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+\
                                '0'+' '+str(d[row][1][0])+" "+'0'+' '+\
                                str(d[row][2][0])+" "+'0'+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
            time.sleep(0.25)

    def redTopDown(self):
        d=self.pinDict
        ser=self.ser
        (r,g,b)=(255,0,0)
        for i in range(14):
            row='row'+str(i+1)
            if len(d[row][0])==1: #other areas
                ser.write(str(d[row][0][0])+" "+str(r)+' '+str(d[row][1][0])+" "\
                      +str(g)+' '+str(d[row][2][0])+" "+str(b)+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+'0'+' '+str(d[row][1][0])+" "\
                      +'0'+' '+str(d[row][2][0])+" "+'0'+'\n')

            else: #waistband
                ser.write(str(d[row][0][0])+" "+\
                                str(r)+' '+str(d[row][1][0])+" "+str(g)+' '+\
                                str(d[row][2][0])+" "+str(b)+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+\
                                '0'+' '+str(d[row][1][0])+" "+'0'+' '+\
                                str(d[row][2][0])+" "+'0'+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
            time.sleep(0.25)

    def greenBottomUp(self):
        d=self.pinDict
        ser=self.ser
        (r,g,b)=(0,255,0)
        for i in range(13,-1,-1):
            row='row'+str(i+1)
            if len(d[row][0])==1: #other areas
                ser.write(str(d[row][0][0])+" "+str(r)+' '+str(d[row][1][0])+" "\
                      +str(g)+' '+str(d[row][2][0])+" "+str(b)+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+'0'+' '+str(d[row][1][0])+" "\
                      +'0'+' '+str(d[row][2][0])+" "+'0'+'\n')

            else: #waistband
                ser.write(str(d[row][0][0])+" "+\
                                str(r)+' '+str(d[row][1][0])+" "+str(g)+' '+\
                                str(d[row][2][0])+" "+str(b)+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+\
                                '0'+' '+str(d[row][1][0])+" "+'0'+' '+\
                                str(d[row][2][0])+" "+'0'+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')

            time.sleep(0.25)

    def blueTopDown(self):
        d=self.pinDict
        ser=self.ser
        (r,g,b)=(0,0,255)
        for i in range(14):
            row='row'+str(i+1)
            if len(d[row][0])==1: #other areas
                ser.write(str(d[row][0][0])+" "+str(r)+' '+str(d[row][1][0])+" "\
                      +str(g)+' '+str(d[row][2][0])+" "+str(b)+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+'0'+' '+str(d[row][1][0])+" "\
                      +'0'+' '+str(d[row][2][0])+" "+'0'+'\n')

            else: #waistband
                ser.write(str(d[row][0][0])+" "+\
                                str(r)+' '+str(d[row][1][0])+" "+str(g)+' '+\
                                str(d[row][2][0])+" "+str(b)+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
                time.sleep(0.05)
                ser.write(str(d[row][0][0])+" "+\
                                '0'+' '+str(d[row][1][0])+" "+'0'+' '+\
                                str(d[row][2][0])+" "+'0'+" "+\
                                str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                str(d[row][2][1])+'\n')
            time.sleep(0.25) 

    def dressLightUpInMode1(self):
        d=self.pinDict
        ser=self.ser
        while True:
            for i in range(14):
                self.audio.startRecording()
                self.audio.findRGB()
                (r,g,b)=(self.audio.r,self.audio.g,self.audio.b)
                row='row'+str(i+1)
                if len(d[row][0])==1: #other areas
                    ser.write(str(d[row][0][0])+" "+str(r)+' '+str(d[row][1][0])+" "\
                          +str(g)+' '+str(d[row][2][0])+" "+str(b)+'\n')
                    time.sleep(0.1)
                    ser.write(str(d[row][0][0])+" "+'0'+' '+str(d[row][1][0])+" "\
                          +'0'+' '+str(d[row][2][0])+" "+'0'+'\n') #turn off
                else: #waistband
                    ser.write(str(d[row][0][0])+" "+\
                                    str(r)+' '+str(d[row][1][0])+" "+str(g)+' '+\
                                    str(d[row][2][0])+" "+str(b)+" "+\
                                    str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                    str(d[row][2][1])+'\n')
                    time.sleep(0.1)
                    ser.write(str(d[row][0][0])+" "+\
                                    '0'+' '+str(d[row][1][0])+" "+'0'+' '+\
                                    str(d[row][2][0])+" "+'0'+" "+\
                                    str(d[row][0][1])+" "+str(d[row][1][1])+" "+\
                                    str(d[row][2][1])+'\n') #turn off
                time.sleep(0.1)

    def lightUpBottomOnly(self,bottomRow,d,ser,r,g,b):
        if len(d[bottomRow][0])==1: #other areas
            ser.write(str(d[bottomRow][0][0])+" "+str(r)+' '+\
                      str(d[bottomRow][1][0])+" "+str(g)+' '+\
                      str(d[bottomRow][2][0])+" "+str(b)+'\n')
            time.sleep(0.1)
            ser.write(str(d[bottomRow][0][0])+" "+'0'+' '+\
                      str(d[bottomRow][1][0])+" "+'0'+' '+\
                      str(d[bottomRow][2][0])+" "+'0'+'\n') #turn off
        else: #waistband
            ser.write(str(d[bottomRow][0][0])+" "+str(r)+' '+\
                  str(d[bottomRow][1][0])+" "+str(g)+' '+\
                  str(d[bottomRow][2][0])+" "+str(b)+" "+\
                  str(d[bottomRow][0][1])+" "+str(d[bottomRow][1][1])+\
                  " "+str(d[bottomRow][2][1])+'\n')
            time.sleep(0.1)
            ser.write(str(d[bottomRow][0][0])+" "+'0'+' '+\
                  str(d[bottomRow][1][0])+" "+'0'+' '+\
                  str(d[bottomRow][2][0])+" "+'0'+" "+\
                  str(d[bottomRow][0][1])+" "+str(d[bottomRow][1][1])+\
                  " "+str(d[bottomRow][2][1])+'\n') #turn off
        time.sleep(0.1)

    def lightUpBoth(self,topRow,bottomRow,d,ser,r,g,b):
        if len(d[topRow][0])==1: #other areas
            ser.write(str(d[topRow][0][0])+" "+str(r)+' '+\
                      str(d[topRow][1][0])+" "+str(g)+' '+\
                      str(d[topRow][2][0])+" "+str(b)+" "+\
                      str(d[bottomRow][0][0])+" "+str(d[bottomRow][1][0])+\
                      " "+str(d[bottomRow][2][0])+'\n')
            time.sleep(0.1)
            ser.write(str(d[topRow][0][0])+" "+'0'+' '+\
                      str(d[topRow][1][0])+" "+'0'+' '+\
                      str(d[topRow][2][0])+" "+'0'+" "+\
                      str(d[bottomRow][0][0])+" "+str(d[bottomRow][1][0])+\
                      " "+str(d[bottomRow][2][0])+'\n') #turn off
        else: #waistband
            ser.write(str(d[topRow][0][0])+" "+str(r)+' '+\
                      str(d[topRow][1][0])+" "+str(g)+' '+\
                      str(d[topRow][2][0])+" "+str(b)+" "+\
                      str(d[topRow][0][1])+" "+str(d[topRow][1][1])+" "+\
                      str(d[topRow][2][1])+" "+str(d[bottomRow][0][0])+" "+\
                      str(d[bottomRow][1][0])+" "+str(d[bottomRow][2][0])+\
                      " "+str(d[bottomRow][0][1])+" "+\
                      str(d[bottomRow][1][1])+" "+\
                      str(d[bottomRow][2][1])+'\n')
            time.sleep(0.1)
            ser.write(str(d[topRow][0][0])+" "+'0'+' '+\
                      str(d[topRow][1][0])+" "+'0'+' '+\
                      str(d[topRow][2][0])+" "+'0'+" "+\
                      str(d[topRow][0][1])+" "+str(d[topRow][1][1])+" "+\
                      str(d[topRow][2][1])+" "+str(d[bottomRow][0][0])+\
                      " "+str(d[bottomRow][1][0])+" "+\
                      str(d[bottomRow][2][0])+" "+str(d[bottomRow][0][1])+\
                      " "+str(d[bottomRow][1][1])+" "+\
                      str(d[bottomRow][2][1])+'\n') #turn off
        time.sleep(0.1)            

    def dressLightUpInMode2(self):
        d=self.pinDict
        ser=self.ser
        while True:
            for i in range(8):
               topRow='row'+str(6-i)
               bottomRow='row'+str(7+i)
               self.audio.startRecording()
               self.audio.findRGB()
               (r,g,b)=(self.audio.r,self.audio.g,self.audio.b)
               topRow='row'+str(6-i)
               bottomRow='row'+str(7+i)
               #only light up the bottom part
               #top part waits for the bottom to finish
               #since the bottom has more strings
               if i>=6:
                   self.lightUpBottomOnly(bottomRow,d,ser,r,g,b)
                   #when both top and bottom turn on together
               else:
                   self.lightUpBoth(topRow,bottomRow,d,ser,r,g,b)
        
def runVisual():
    class Struct: pass
    data=Struct()
    initWindow(data)
    mousePressed(data)
    while True:
        rate(20)
        #rotate the model
        data.model.frame.rotate(axis=data.model.axis,angle=2*pi/100)
        #rotate the bars
        data.bars.frame.rotate(axis=data.bars.axis,angle=2*pi/100)
        if data.sound.recording==True:
            data.sound.startRecording()
            showDetectedFrequency(data)
        if data.colorModeSelected==False or data.colorMode==None or \
           data.model.dressPattern==None or data.sound.recording==False:
            continue
        determineRgbBasingOnMode(data)
        data.sound.findRGB()
        calculateLoudness(data)
        #show color of the dress (corresponds to the frequency detected)
        dressChange(data)
        #show change of heights of the bars
        barsChange(data)

runVisual()


#!/usr/bin/env python
import numpy
import PyTango
from sardana import State, DataAccess
from sardana.pool.controller import CounterTimerController
from sardana.pool.controller import Type, Access, Description

def __braggCountToDegree(count):
    offset = 2683367
    stepPerUnit = 200000
    return (count + offset) / stepPerUnit

class AlbaBl22DcmTurboPmacCoTiCtrl(CounterTimerController):
    """This class is the Sardana CounterTimer controller for TurboPmac controller.
       It is used to """
    
    MaxDevice = 1
    START_INDEX = 6000

    class_prop = {'TurboPmacDeviceName':{'Description' : 'TurboPmac controller Tango device', 'Type' : 'PyTango.DevString'},
                  'EnergyDeviceName':{'Description' : 'Energy pseudomotor Tango device', 'Type' : 'PyTango.DevString'}}
    
    axis_attributes ={#attributes added for continuous acqusition mode
                      "NrOfTriggers":
                        {Type : long,
                         Description : 'Nr of triggers',
                         Access : DataAccess.ReadWrite
                        },
                      "SamplingFrequency":
                       {Type : float,
                        Description : 'Sampling frequency',
                        Access : DataAccess.ReadWrite
                       },
                      "AcquisitionTime":
                       {Type : float,
                        Description : 'Acquisition time per trigger',
                        Access : DataAccess.ReadWrite
                       },
                      "TriggerMode":
                       {Type : str,
                        Description : 'Trigger mode: soft or gate',
                        Access : DataAccess.ReadWrite
                       },
                       "Data":
                       {Type : [float],
                        Description : 'Data buffer',
                        Access : DataAccess.ReadWrite
                       }
                      }


    def __init__(self, inst, props, *args, **kwargs):
        #        self._log.setLevel(logging.DEBUG)
        CounterTimerController.__init__(self, inst, props, *args, **kwargs)
        self._log.debug("__init__(%s, %s): Entering...", repr(inst), repr(props))
        self.nrOfTriggers = 1000

        msg = None
        try:
            self.pmac = PyTango.DeviceProxy(self.TurboPmacDeviceName)
        except PyTango.DevFailed, e:
            msg = "__init__(): Could not create a device proxy from following device name: %s.\nException: %s" % \
                  (self.TurboPmacDeviceName, e)
        try:
            self.energy = PyTango.DeviceProxy(self.EnergyDeviceName)
        except PyTango.DevFailed, e:
            msg += "\n__init__(): Could not create a device proxy from following device name: %s.\nException: %s" % \
                  (self.TurboPmacDeviceName, e)

        if msg != None:
            self._log.error(msg)
            self.pmac = None
            self.energy = None
            self.state = State.Fault
            self.status = msg
        
    def AddDevice(self, axis):  
        self._log.debug("AddDevice(%d): Entering...", axis)
        
    def DeleteDevice(self, axis):
        self._log.debug("DeleteDevice(%d): Entering...", axis)
        
    def StateOne(self, axis):
        self._log.debug("StateOne(%d): Entering...", axis)
        if self.pmac is not None:
            try:
                m = int(self.pmac.GetMVariable(3300))
            except PyTango.DevFailed, e:
                msg = "StateOne(%d): Could not verify state of the device: %s.\nException: %s" % \
                                (axis, self.TurboPmacDeviceName, e)
                self._log.error(msg)
                self.state = State.Unknown
                self.status = msg
            #value 0 means that plc0 is enabled, and value 1 means that plc0 is disabled
            if bool(m): 
                self.state = State.On
                self.status = "Plc0 is disabled"
            else:
                self.state = State.Moving
                self.status = "Plc0 is enabled"
        self._log.debug("StateOne(%d): Leaving...", axis)
        return (self.state, self.status) 
        
    def PreReadOne(self, axis):
        self._log.debug("PreReadOne(%d): Entering...", axis)        
        
    def ReadOne(self, axis):
        self._log.debug("ReadOne(%d): Entering...", axis)
        return float("nan")
            
    def AbortOne(self, axis):
        self._log.debug("AbortOne(%d): Entering...", axis)
        self.pmac.command_inout("DisablePLC", 0)
    
    def PreStartAllCT(self):
        self._log.debug("PreStartAllCT(): Entering...")
        
    def PreStartOneCT(self, axis):
        self._log.debug("PreStartOneCT(%d): Entering...", axis)
        return True

    def StartAllCT(self):
        """Starting the acquisition is done only if before was called PreStartOneCT for master channel."""
        self._log.debug("StartAllCT(): Entering...")
        self.pmac.command_inout("EnablePLC", 0)
        
    def PreLoadOne(self, axis, value):
        """Here we are keeping a reference to the master channel, so later in StartAll() 
        we can distinguish if we are starting only the master channel."""
        self._log.debug("PreLoadOne(%d, %f): Entering...", axis, value)
        return True
        
    def LoadOne(self, axis, value):
        self._log.debug("LoadOne(%d, %f): Entering...", axis, value)

    def GetAxisExtraPar(self, axis, name):
        self._log.debug("GetAxisExtraPar(%d, %s): Entering...", axis, name)
        #attributes used for continuous acquisition
        if name.lower() == "samplingfrequency":            
            return float("nan")
        if name.lower() == "triggermode":
            return "gate"
        if name.lower() == "nroftriggers":
            nrOfTriggers = self.pmac.command_inout("GetPVariable", 5998) - self.START_INDEX
            return long(nrOfTriggers)
        if name.lower() == "acquisitiontime":
            return float("nan")
        if name.lower() == "data":
            degrees = self.__getPositions()
            energies = [self.energy.calcPseudo([d, float("nan")]) for d in degrees]
            return energies

    def SetAxisExtraPar(self,axis, name, value):
        #attributes used for continuous acquisition
        if name.lower() == "samplingfrequency":
            pass
        if name.lower() == "triggermode":
            pass
        if name.lower() == "nroftriggers":
            self.nrOfTriggers = value
            self.pmac.SetPVariable([5998, self.START_INDEX + self.nrOfTriggers])            
        if name.lower() == "acquisitiontime":
            pass

    def SendToCtrl(self, cmd):
        cmd = cmd.lower()
        words = cmd.split(" ")
        ret = "Unknown command"
        if len(words) == 2:
            action = words[0]
            axis = int(words[1])
            if action == "pre-start":
                ret = "Nothing to do in pre-start"
            elif action == "start":
                self._log.debug("SendToCtrl(%s): starting channel %d", cmd, axis)
                self.pmac.EnablePLC(0)
                ret = "PLC0 enabled"
            elif action == "pre-stop":
                ret = "Nothing to do in pre-stop"
            elif action == "stop":
                self._log.debug("SendToCtrl(%s): stopping channel %d", cmd, axis)
                self.pmac.DisablePLC(0)
                ret = "PLC0 disabled"
        return ret
            
    def __getPositions(self):
        ranges = []
        start = self.START_INDEX
        end = endOfRange = start + self.nrOfTriggers
        
        maxLen = 100
        #composing ranges in case of multiple queries
        while (end - start) > maxLen:
            endOfRange = start + (maxLen - 1)
            ranges.append([start,endOfRange])
            start = endOfRange + 1
        else:
            ranges.append([start, end - 1])        
            
        rawCounts = numpy.array([])
        for r in ranges:
            self._log.error("Range: %s" % repr(r))
            rawCounts = numpy.append(rawCounts, self.pmac.GetPVariableRange(r))
        #translations from raw counts to degrees
        #getting an offset between position and encoder register (offset = 2683367)
        braggPosCounts = float(self.pmac.SendCtrlChar("P").split()[0])
        encRegCounts = float(self.pmac.GetMVariable(101))
        offset = braggPosCounts - encRegCounts
        stepPerUnit = 200000
        translate = lambda count: (count + offset) / stepPerUnit 
        degrees = [translate(count) for count in rawCounts]
        #degrees = rawCounts
        return degrees
    

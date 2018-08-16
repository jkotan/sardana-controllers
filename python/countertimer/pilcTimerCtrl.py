import PyTango
from sardana.pool.controller import CounterTimerController
import time

from sardana import State, DataAccess
from sardana.pool.controller import MotorController
from sardana.pool.controller import Type, Access, Description, DefaultValue
from sardana.pool import PoolUtil

ReadOnly = DataAccess.ReadOnly
ReadWrite = DataAccess.ReadWrite

# TimeTriggerStepSize
# TriggerPulseLength

class pilcTimerCtrl(CounterTimerController):
    "This class is the Tango Sardana CounterTimer controller for the PiLCTriggerGenerator used as timer"
    

    axis_attributes = {'TangoDevice':{Type:str,Access:ReadOnly}, 
                       }
             
    ctrl_properties = {'RootDeviceName':{Type:str,Description:'The root name of the PiLCTriggerGenerator Tango device'},
                       'TangoHost':{Type:str,Description:'The tango host where searching the devices'}, 
                       }

    gender = "CounterTimer"
    model = "PilcTriggerGenerator"
    organization = "DESY"
    state = ""
    status = ""
    
    def __init__(self,inst,props, *args, **kwargs):
        self.TangoHost = None
        CounterTimerController.__init__(self,inst,props, *args, **kwargs)
        if self.TangoHost == None:
            self.db = PyTango.Database()
        else:
            self.node = self.TangoHost
            self.port = 10000
            if self.TangoHost.find( ':'):
                lst = self.TangoHost.split(':')
                self.node = lst[0]
                self.port = int( lst[1])
        self.db = PyTango.Database(self.node, self.port)
        name_dev_ask =  self.RootDeviceName + "*"
        self.devices = self.db.get_device_exported(name_dev_ask)
        self.max_device = 0
        self.tango_device = []
        self.proxy = []
        self.device_available = []
        for name in self.devices.value_string:
                self.tango_device.append(name)
                self.proxy.append(None)
                self.device_available.append(0)
                self.max_device =  self.max_device + 1
        self.started = False
        self.preset_mode = 0 # Trigger with counts

    def AddDevice(self,ind):
        CounterTimerController.AddDevice(self,ind)
        if ind > self.max_device:
            print "False index"
            return
        proxy_name = self.tango_device[ind-1]
        if self.TangoHost == None:
            proxy_name = self.tango_device[ind-1]
        else:
            proxy_name = str(self.node) + (":%s/" % self.port) + str(self.tango_device[ind-1])
        self.proxy[ind-1] = PyTango.DeviceProxy(proxy_name)
        self.device_available[ind-1] = 1


    def DeleteDevice(self,ind):
        CounterTimerController.DeleteDevice(self,ind)
        self.proxy[ind-1] =  None
        self.device_available[ind-1] = 0


    def StateOne(self,ind):
        if  self.device_available[ind-1] == 1:
            sta = self.proxy[ind-1].command_inout("State")
            if sta == PyTango.DevState.ON:
                status_string = "Timer is in ON state"
            elif sta == PyTango.DevState.MOVING:
                status_string = "Timer is busy"

            return (sta, status_string)

    def PreReadAll(self):
        pass
        

    def PreReadOne(self,ind):
        pass

    def ReadAll(self):
        pass

    def PreStartOne(self,ind,pos):

        ## Set the gate down time.
        self.proxy[ind-1].write_attribute('TriggerPulseLength',0.00005)
        
        return True

    def ReadOne(self,ind):
        if self.device_available[ind-1] == 1:
            ## Sample time can not be calculated at the moment.
            sample_time = (self.
                           proxy[ind-1].
                           read_attribute("TimeTriggerStepSize").
                           value
            )
            return  sample_time
    
    def AbortOne(self,ind):
        if self.device_available[ind-1] == 1:
            self.proxy[ind-1].write_attribute('Arm',0)

        
    def PreStartAllCT(self):
        pass

    def PreStartOneCT(self,ind):
        pass
        
    def StartOneCT(self,ind):
        if self.device_available[ind-1] == 1:
            self.proxy[index-1].write_attribute('Arm',1)
    
    def StartAllCT(self):
        pass


    def LoadOne(self,ind,value):
        if self.device_available[ind-1] == 1:
            self.proxy[ind-1].write_attribute("TimeTriggerStepSize",value)
    
    def GetExtraAttributePar(self,ind,name):
        if self.device_available[ind-1]:
            if name == "TangoDevice":
                tango_device = self.node + ":" + str(self.port) + "/" + self.proxy[ind-1].name() 
                return tango_device
        
            
    def SetExtraAttributePar(self,ind,name,value):
        pass
            
    def SendToCtrl(self,in_data):
        return "Nothing sent"

    def __del__(self):
        print "PYTHON -> pilcTimerCtrl/",self.inst_name,": dying"



import time, os

import PyTango
from sardana import State, DataAccess
from sardana.pool.controller import CounterTimerController
from sardana.pool.controller import Type, Access, Description, DefaultValue
from sardana.pool import PoolUtil

ReadOnly = DataAccess.ReadOnly
ReadWrite = DataAccess.ReadWrite

global last_sta


class Xspress3RoIsCtrl(CounterTimerController):
    "This class is the Tango Sardana CounterTimer controller for making RoIs from OneD"

    ctrl_extra_attributes = {'TangoDevice':{Type:'PyTango.DevString',Access:ReadOnly},
                             'RoIStart':{Type:'PyTango.DevLong',Access:ReadWrite},
                             'RoIEnd':{Type:'PyTango.DevLong',Access:ReadWrite}, 
                             'DataChannel':{Type:'PyTango.DevLong',Access:ReadWrite}                               
                             }
                 
    class_prop = {'RootDeviceName':{Type:'PyTango.DevString',Description:'The root name of the MCA Tango devices'},
                  'TangoHost':{Type:str,Description:'The tango host where searching the devices'}, }
                 
    MaxDevice = 97

    gender = "CounterTimer"
    model = "Xspress3RoIs"
    organization = "DESY"
    state = ""
    status = ""

    def __init__(self,inst,props, *args, **kwargs):
        self.TangoHost = None
        CounterTimerController.__init__(self,inst,props, *args, **kwargs)
        self.debugFlag = False
        if os.isatty(1):
            self.debugFlag = True
        if self.debugFlag: print "Xspress3RoIsCtrl.__init__, inst ",self.inst_name,"RootDeviceName",self.RootDeviceName
        self.ct_name = "Xspress3RoIsCtrl/" + self.inst_name

        if self.TangoHost != None:
            self.node = self.TangoHost
            self.port = 10000
            if self.TangoHost.find( ':'):
                lst = self.TangoHost.split(':')
                self.node = lst[0]
                self.port = int( lst[1])
        self.RoIs_start = []
        self.RoIs_end = []
        self.value = []
        self.channel = []
        proxy_name = self.RootDeviceName
        if self.TangoHost != None:
            proxy_name = str(self.node) + (":%s/" % self.port) + str(proxy_name)
        self.proxy = PyTango.DeviceProxy(proxy_name) 
        global last_sta
        last_sta = PyTango.DevState.ON

        
    def AddDevice(self,ind):
        CounterTimerController.AddDevice(self,ind)
        self.RoIs_start.append(0)
        self.RoIs_end.append(0)
        self.value.append(0)
        self.channel.append(0)
       
    def DeleteDevice(self,ind):
        if self.debugFlag: print "Xspress3RoIsCtrl.DeleteDevice",self.inst_name,"index",ind
        CounterTimerController.DeleteDevice(self,ind)
        self.proxy =  None
        
        
    def StateOne(self,ind):
        global last_sta
        try:
            sta = self.proxy.command_inout("State")
            last_sta = sta
        except:
            sta = last_sta
        if sta == PyTango.DevState.ON:
            tup = (sta,"Xspress3 idle")
        elif sta == PyTango.DevState.MOVING or  sta == PyTango.DevState.RUNNING:
            tup = (PyTango.DevState.MOVING,"Device is acquiring data")
        else:
            tup = (sta, "")

        return tup
    
    def LoadOne(self, axis, value):
        if self.debugFlag: print "Xspress3RoIsCtrl.LoadOne",self.inst_name,"axis", axis
        self.proxy.ExposureTime = value
        
    def PreReadAll(self):
        pass

    def PreReadOne(self,ind):
        pass

    def ReadAll(self):
        if self.debugFlag: print "Xspress3RoIsCtrl.ReadAll",self.inst_name

    def ReadOne(self,ind):
        if self.debugFlag: print "Xspress3RoIsCtrl.ReadOne",self.inst_name,"index",ind
        attr_name = "DataCh" + str(self.channel[ind-1])
        data = self.proxy.read_attribute(attr_name).value
        self.value[ind - 1] = 0
        for j in range(self.RoIs_start[ind -1], self.RoIs_end[ind - 1] + 1):
            self.value[ind-1] = self.value[ind -1] + data[j]
        return self.value[ind - 1]

    def PreStartAll(self):
        pass	

    def StartAll(self):
        try:
            sta = self.proxy.command_inout("State")
        except:
            sta = PyTango.DevState.ON
        if sta == PyTango.DevState.ON:
            self.proxy.command_inout("StartAcquisition")
        
    def PreStartOne(self,ind, value):
        return True
        
    def StartOne(self,ind, value):
        pass
        
    def AbortOne(self,ind):
        if self.debugFlag: print "Xspress3RoIsCtrl.AbortOne",self.inst_name,"index",ind
        self.proxy.command_inout("StopAcquisition")

    def GetPar(self, ind, par_name):
        if self.debugFlag: print "Xspress3RoIsCtrl.GetPar",self.inst_name,"index",ind, "par_name", par_name

    def SetPar(self,ind,par_name,value):
        pass
    
    def GetExtraAttributePar(self,ind,name):
        if self.debugFlag: print "Xspress3RoIsCtrl.GetExtraAttrPar",self.inst_name,"index",ind, "name", name
        if name == "TangoDevice":
            tango_device = self.node + ":" + str(self.port) + "/" + self.proxy.name() 
            return tango_device
        elif name == "DataLength":
            if self.flagIsXIA:
                datalength = int(self.proxy.read_attribute("McaLength").value)
            else:
                datalength = int(self.proxy.read_attribute("DataLength").value)
            return datalength
        elif name == "RoIStart":
            return self.RoIs_start[ind-1]
        elif name == "RoIEnd":
            return self.RoIs_end[ind-1]
        elif name == "DataChannel":
            return self.channel[ind-1]

    def SetExtraAttributePar(self,ind,name,value):
        if self.debugFlag: print "Xspress3RoIsCtrl.SetExtraAttributePar",self.inst_name,"index",ind," name=",name," value=",value
        if name == "DataLength":
            if self.flagIsXIA:
                self.proxy.write_attribute("McaLength",value)
            else:
                self.proxy.write_attribute("DataLength",value)
        elif name == "RoIStart":
            self.RoIs_start[ind-1] = value
        elif name == "RoIEnd":
            self.RoIs_end[ind-1] = value
        elif name == "DataChannel":
            self.channel[ind-1] = value

    def SendToCtrl(self,in_data):
        return "Nothing sent"
        
    def __del__(self):
        if self.debugFlag: print "Xspress3RoIsCtrl/",self.inst_name,": dying"

        
if __name__ == "__main__":
    obj = CounterTimerController('test')
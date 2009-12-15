#!/usr/bin/env python2.5

#############################################################################
##
## file :    PmacCtrl.py
##
## description : 
##
## project :    miscellaneous/PoolControllers/MotorControllers
##
## developers history: zreszela
##
## copyleft :    Cells / Alba Synchrotron
##               Bellaterra
##               Spain
##
#############################################################################
##
## This file is part of Sardana.
##
## This is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This software is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
###########################################################################

import PyTango
from pool import MotorController


class PmacController(MotorController):
    """This class is the Tango Sardana motor controller for the Pmac motor controller device."""

    class_prop = {'DevName':{'Description' : 'Device name of the PmacEth DS','Type' : 'PyTango.DevString'}}
    
    ctrl_extra_attributes = {'PowerOn':{'Type':'PyTango.DevBoolean','R/W Type':'PyTango.READ_WRITE'}}

    MaxDevice = 32

    def __init__(self,inst,props):
        MotorController.__init__(self,inst,props)
        self.pmacEth = PyTango.DeviceProxy(self.DevName)

    def AddDevice(self, axis):
        pass

    def DeleteDevice(self, axis):
        pass

    def StateOne(self, axis):
        self._log.info('RETURNING THE STATE OF AXIS %d'%axis)
        state = PyTango.DevState.ON
        switchstate = 0
        status = "No limits are active, motor is in position"
        if not bool(int(self.pmacEth.command_inout("GetMVariable",(int("%d40" % axis))))):
               state = PyTango.DevState.MOVING
               status = '\nThe motor is moving'
        if bool(int(self.pmacEth.command_inout("GetMVariable",(int("%d21" % axis))))):
               state = PyTango.DevState.ALARM
               status = '\nAt least one of the lower/upper switches is activated'
               switchstate += 2
        if bool(int(self.pmacEth.command_inout("GetMVariable",(int("%d22" % axis))))):
               state = PyTango.DevState.ALARM
               status = '\nAt least one of the negative/positive limit is activated'
               switchstate += 4
        return (state, status, switchstate)

    def ReadOne(self, axis):
        self._log.info('Returning the current position for axis %d'%axis)
        position = self.pmacEth.command_inout("GetMotorPos",(axis))
        self._log.info('POSITION: %s'%position)
        return float(position)

    def StartOne(self, axis, position):
        self._log.info('Moving the axis %d to position %d'%(axis, position))
	if not self.GetExtraAttributePar(axis,"PowerOn"):
	    error_msg = '''It's not possible to move motor %d with disabled amplifier ''' % axis
	    self._log.error(error_msg)
	    raise Exception(error_msg) 
        self.pmacEth.command_inout("JogToPos",[axis,position])

    def SetPar(self, axis, parname, parvalue):
        pass

    def GetPar(self, axis, parname):
        return 0

    def GetExtraAttributePar(self, axis, attr_name):
        return 0

    def SetExtraAttributePar(self, axis, attr_name, value):
        pass

    def AbortOne(self, axis):
        self._log.info('Stopping the movement of axis %d'%axis)
        self.pmacEth.command_inout("JogStop",[axis])
    
    def DefinePosition(self,powerConverter, current):
        pass
    
    def GetExtraAttributePar(self, axis, name):
        """ Get Pmac axis particular parameters.
        @param axis to get the parameter
        @param name of the parameter to retrive
        @return the value of the parameter
        """
	name = name.lower()
	if name == "poweron":
	    return bool(self.pmacEth.command_inout("GetMVariable",int("%d39"%axis)))

    def SetExtraAttributePar(self, axis, name, value):
        """ Set Pmac axis particular parameters.
        @param axis to set the parameter
        @param name of the parameter
        @param value to be set
        """
        name = name.lower()
        if name == "poweron":
            if value:
                self.pmacEth.command_inout("JogStop", [axis])
            else:
                self.pmacEth.command_inout("KillMotor", [axis])
		
    def SendToCtrl(self,cmd):
        """ Send custom native commands.
        @param string representing the command
        @return the result received
        """
        self._log.info('SendToCtrl(%s).' % cmd)
	cmd_splitted = cmd.split()
	if len(cmd_splitted) == 1: 
            self.pmacEth.command_inout(cmd)
	else:
	    if len(cmd_splitted) == 2:
	        if cmd_splitted[0].lower() == "enableplc":
	            self.pmacEth.command_inout("enableplc",int(cmd_splitted[1]))
		if cmd_splitted[0].lower() =="getmvariable":
		    return str(self.pmacEth.command_inout("getmvariable",int(cmd_splitted[1])))
            elif len(cmd_splitted) > 2:
	        if cmd_splitted[0].lower() == "setpvariable":
		    array = [float(cmd_splitted[i]) for i in range(1, len(cmd_splitted))]
	            self.pmacEth.command_inout("setpvariable", array)

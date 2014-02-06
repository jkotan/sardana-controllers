##############################################################################
##
## This file is part of Sardana
##
## http://www.tango-controls.org/static/sardana/latest/doc/html/index.html
##
## Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
## Author: Marc Rosanes 
##
## Sardana is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
## 
## Sardana is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
## 
## You should have received a copy of the GNU Lesser General Public License
## along with Sardana.  If not, see <http://www.gnu.org/licenses/>.
##
##############################################################################

"""This module contains the definition of a linear to rotation pseudo motor 
controller for the Sardana Device Pool"""


__all__ = ["clear"]

__docformat__ = 'restructuredtext'

from sardana import DataAccess
from sardana.pool.controller import PseudoMotorController
from sardana.pool.controller import DefaultValue, Description, Access, Type

import PyTango
import math
   


class EnergyOut(PseudoMotorController):
    """An EnergyOut pseudomotorController (taking as physical motor the 
       bragg pseudoMotor) for handling Clear Eout pseudomotor."""

    gender = "Eout"
    model  = "Default Eout"
    organization = "Sardana team"

    # theta = bragg
    pseudo_motor_roles = ["Eout"]
    motor_roles = ["bragg"]
    
    # Introduce properties here.
    ctrl_properties = { 'crystalIOR' : { Type : str,
                                     Description  : 'CrystalIOR from which ' + 
                                    'the Eout pseudomotor must infer H,K,L ' + 
                                    'and the lattice spacing a' }, } 
                              #'DefaultValue' : 'ioregister/clearhome_iorctrl/2' 
    
    # Introduce attributes here.
    axis_attributes = {  'n' : { Type : int,
                                 Access : DataAccess.ReadWrite,
                                 Description : 'Order: Energy harmonic.' }, }



    """ Limit angles between 50 and 80 degrees because for smaller angles we
        lose a lot of resolution. At the moment bigger angles of 76 degrees are
        not allowed by the hardware limits of Detector Rotation motor.
        Smaller angles than 43 degrees can occasionate a collision 
        between analyzer and detector.""" 
    
    """d for 25CelsiusDegrees and for a Silicon crystal with 
       miller indices (1,1,1) -> 3.13 nm = 0.5430710/math.sqrt(3)"""
    def __init__(self, inst, props, *args, **kwargs):
       
        PseudoMotorController.__init__(self, inst, props, *args, **kwargs)
        self._log.debug("Created CLEAR Eout %s", inst)

        self.hc = 0.00123984193 #[eV*mm]
        self.crystal = PyTango.DeviceProxy(self.crystalIOR)

    # Calculation of input motors values.
    def CalcPhysical(self, index, pseudo_pos, curr_physical_pos):
        """Bragg angle"""

        """ hkl is specific for the crystal. We extract them from the 
            number of ioregister managing the crystal."""
        """ 'a' is specific of the crystal: I have to extract it from 
            the position of the IORegister managing the change of crystal. 
            0.5430710nm is specific for the Silicon and 0.56579nm is specific
            for the Germanium."""
        if self.crystal.value == 0: #Silicon crystal
            self.a = 0.0000005430710 
            self.h = 1
            self.k = 1
            self.l = 1
        elif self.crystal.value == 1: #Silicon crystal
            self.a = 0.0000005430710 
            self.h = 2
            self.k = 2
            self.l = 0
        elif self.crystal.value == 2: #Silicon crystal
            self.a = 0.0000005430710 
            self.h = 4
            self.k = 0
            self.l = 0 
        elif self.crystal.value == 3: #Germanium crystal
            self.a = 0.000000565791 
            self.h = 1
            self.k = 1
            self.l = 1

        energy = pseudo_pos[0]
        lambdas = self.hc / energy 
        
        sq = (self.h)**2 + (self.k)**2 + (self.l)**2
        theta_rad= math.asin(lambdas * self.n * math.sqrt(sq) / (2 * self.a)) 
        theta = theta_rad * 180.0 / math.pi
        bragg = theta

        #self._log.debug("CalcPhysical is being executed")
        ret = bragg
        return ret

    # Calculation of output PseudoMotor values.
    def CalcPseudo(self, index, physical_pos, curr_pseudo_pos):
        
        """Bragg = Theta: They are given in degrees."""
        """We have: n*lambda=2*d*sin(theta). 
           Where 'd' is the distance between atomic planes.
           We also have: d=a/sqrt(h^2+k^2+l^2) for a cubic crystal. 
           Then: lambda= a*2*sin(theta)/(n*sqrt(h^2+k^2+l^2)).
           'a' is the lattice spacing (of 0.5430710nm in the case of Silicon). 
           'd' is the distance between planes of crystalline structure."""


        if self.crystal.value == 0: #Silicon crystal
            self.a = 0.0000005430710 
            self.h = 1
            self.k = 1
            self.l = 1
        elif self.crystal.value == 1: #Silicon crystal
            self.a = 0.0000005430710 
            self.h = 2
            self.k = 2
            self.l = 0
        elif self.crystal.value == 2: #Silicon crystal
            self.a = 0.0000005430710 
            self.h = 4
            self.k = 0
            self.l = 0 
        elif self.crystal.value == 3: #Germanium crystal
            self.a = 0.000000565791 
            self.h = 1
            self.k = 1
            self.l = 1

        bragg = physical_pos[0]
        theta = bragg #theta is in degrees here.

        theta_rad = theta*math.pi/180.0 #theta_rad is theta in radians.
        denominator = self.n*math.sqrt((self.h)**2 + (self.k)**2 + (self.l)**2)
        lambdas = 2 * self.a * math.sin(theta_rad) / denominator
        ener_out = self.hc/lambdas

        #self._log.debug("CalcPseudo is being executed")
        ret = ener_out
        return ret

    # Introduce here attribute setter.
    def SetAxisExtraPar(self, axis, parameter, value):
        if (parameter == 'n'):
            self.n = value

    # Introduce here attribute getter.
    def GetAxisExtraPar(self, axis, parameter):
        if (parameter == 'n'):
            return self.n
        else:
            return 1







 
class LinearRotController(PseudoMotorController):
    """A LinearRotController pseudoMotorController for handling the 'atheta' 
       rotation pseudomotor. The system uses the real motor 'azlin' , which is
       the linear motor of the Clear Analyzer allowing the rotation."""

    gender = "Linear2RotController"
    model  = "Default Linear2RotController"
    organization = "Sardana team"
    
    pseudo_motor_roles = "atheta",
    motor_roles = "azlin",


    def __init__(self, inst, props, *args, **kwargs):
        PseudoMotorController.__init__(self, inst, props, *args, **kwargs)
        self._log.debug("Created LinearRotController %s", inst)


    def CalcPhysical(self, index, pseudo_pos, curr_physical_pos):
         
        #angular offsets deduced with Jon help: 57.5902 and 72.22. 
        value_for_tangent = ((pseudo_pos[0]-57.5902) * math.pi / 180.0)
        azlin = 155.0 * math.tan(value_for_tangent) - 72.22 
        ret = azlin
        
        #self._log.debug("LinearRot.CalcPhysical")
        return ret
    

    def CalcPseudo(self, index, physical_pos, curr_pseudo_pos):

        """ atheta = Psi_center + 180.0/math.pi * math.atan(value)
            with:
            value: (delta + physical_pos[0])/155.0) """

        """ 155.0: distance (in mm) between center of analyzer platform and the 
            pivot of the arm that allows the platform rotation: Given by 
            Llibert.     
  
            Psi_center = 57.5902 (given by Jon: angle of analyzer when arm 
            giving rotation of analyzer is in the Y axis).

            delta = 72.22 (given by Jon: linear offset in Z direction in mm 
            between Y axis and arm). """
         
        value = ((72.22 + physical_pos[0])/155.0)
        atheta = 57.5902 + 180.0/math.pi * math.atan(value) 
        ret = atheta

        #self._log.debug("LinearRot.CalcPseudo")
        return ret








    
class bragg(PseudoMotorController):
    """A bragg pseudo motor controller for handling Clear theta pseudomotor."""
    """bragg=theta """

    gender = "bragg"
    model  = "Default bragg"
    organization = "Sardana team"
    
    # theta = bragg
    pseudo_motor_roles = ["theta"]
    motor_roles = ["rota", "rots", "rotd", "ya", "yd", "zd", "b1", "b2"]
    
    # Introduce attributes in here.
    axis_attributes = { 'offset_sample_clear' : { Type : float,
                                     Access : DataAccess.ReadWrite,
                                     Description : 'Offset from sample to ' + 
                                     'external wall of Clear in Y direction' },

                        'my' : { Type : float,
                                 Access : DataAccess.ReadWrite,
                                 Description : 'y slope coefficient for ' +
                                                    'detector correction' }, 

                        'oy' : { Type : float,
                                 Access : DataAccess.ReadWrite,
                                 Description : 'z slope coefficient for ' +
                                                    'detector correction'},

                        'mz' : { Type : float,
                                 Access : DataAccess.ReadWrite,
                                 Description : 'x offset coefficient ' +
                                                    'for detector correction'},

                        'oz' : { Type : float,
                                 Access : DataAccess.ReadWrite,
                                 Description : 'z offset coefficient ' +
                                                  'for detector correction'},}

    """ Konstantin said: Limit angles: from 35 to 80 degrees. 
        From papers: the most interesting is from 55 and 80 degrees because for
        smaller angles we lose a lot of Energy resolution. 
        At this moment, physically only a range between 43 and 76 degrees is 
        possible if we want to avoid collisions. """
    """Currently, everything is done by considering that p=q=ya 
       (ya: y analyzer: being the distance between the sample and 
       the analyzer). """

    def __init__(self, inst, props, *args, **kwargs):

        PseudoMotorController.__init__(self, inst, props, *args, **kwargs)
        self._log.debug("Created CLEAR %s", inst)

        # R is the radius of the Rowland circle in meters.        
        self.R = 500
 
        """ Initialize attributes here.
         Correction coefficients introduced by Laura for the 
         detector: my, mz, oy, oz. Used as attributes. """
        self.my = 0.0
        self.mz = 0.0
        self.oy = 0.0
        self.oz = 0.0
        self.offset_sample_clear = 350.0

    # Calculation of input motors values.
    def CalcPhysical(self, index, pseudo_pos, curr_physical_pos):	
        """Bragg angle"""
        theta = pseudo_pos[0] 
        theta_rad = theta*3.141592/180.0

        alpha_rad = math.pi/2.0 - theta_rad
        alpha = alpha_rad*180.0/math.pi

        """ Info: Xtal.Y = p = q - XES.y -y 
        In this pseudo we will work On Rowland, so 'p = q = Xtal.Y'. 
        XES.y will be always set to 0 because the distance between the sample 
        and the WholeClear will be fixed. 
        'y' is the inside-Rowland done by the translation of detector and 
        analyzer (set to 0 for this pseudo)."""

        ya= 2*self.R*math.sin(theta_rad)

        # rota: Rotation Analyzer
        if index==1:
            ret = theta #In degrees

        # rots: Rotation Slits
        elif index == 2:
            ret = theta #In degrees

        # rotd: Rotation Detector
        elif index == 3:
            ret = 2*theta - 90.0 #In degrees 

        # ya: Y analyzer
        elif index == 4:
            """ self.offset_sample_clear is subtracted in order to take into 
                account the variation of the distance between the sample and 
                the external wall of clear (default 350mm). """  
            ret = ya - (self.offset_sample_clear)

        # yd: Y detector
        elif index == 5:
            """  self.offset_sample_clear has been subtracted in order to take 
                 into account the variation of the distance between the sample 
                 and the external wall of clear (default 350mm). """
            f_theta = ya + ya*math.cos(2*theta_rad) - (self.offset_sample_clear)
            ret = f_theta + self.my*(f_theta)*math.sin(2*alpha_rad) + self.oy
            #self._log.debug('my {0}.'.format(self.my))
            #self._log.debug('oy {0}.'.format(self.oy))           

        # zd: Z detector
        elif index == 6:
            g_theta = ya*math.sin(2*theta_rad)
            ret = g_theta + self.mz*(g_theta)*math.cos(2*alpha_rad) + self.oz
            #self._log.debug('mz: {0}.'.format(self.mz))
            #self._log.debug('oz: {0}.'.format(self.oz))

        # b1: B1
        elif index == 7:
            ret = 2*math.sin(theta_rad)*ya/2.0

        # b2: B2
        elif index ==8:
            ret = 2*math.sin(theta_rad)*ya/2.0
        
        else:
            pass

        self._log.debug("CalcPhysical is being executed")
        return ret

    # Calculation of output PseudoMotor values.
    def CalcPseudo(self, index, physical_pos, curr_pseudo_pos):
        """ This pseudomotor returns the Bragg angle in function of the 
        physical motors position (taking as reference the Analyzer rotation).
        The Bragg angle is the angle between the Y axis (beam direction) 
        and the analyzer pitch.
        It is the same angle that exists between the Y axis and the 
        Slits pitch"""
        """bragg = theta; they are given in degrees."""

        theta = physical_pos[0] 
        ret = theta
        #self._log.debug("CalcPseudo is being executed")	
        return ret 
    
    # Introduce here attribute setter.
    def SetAxisExtraPar(self, axis, parameter, value):
        if (parameter == 'my'):
            self.my = value
        elif (parameter == 'oy'):
            self.oy = value
        elif (parameter == 'mz'):
            self.mz = value
        elif (parameter == 'oz'):
            self.oz = value
        elif (parameter == 'offset_sample_clear'):
            self.offset_sample_clear = value
      
    # Introduce here attribute getter.
    def GetAxisExtraPar(self, axis, parameter):
        if (parameter == 'my'):
            return self.my
        elif (parameter == 'oy'):
            return self.oy
        elif (parameter == 'mz'):
            return self.mz
        elif (parameter == 'oz'):
            return self.oz
        elif (parameter == 'offset_sample_clear'):
            return self.offset_sample_clear
        else:
            return 1






##############################################################################
##
# This file is part of Sardana
##
# http://www.tango-controls.org/static/sardana/latest/doc/html/index.html
##
# Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
##
# Sardana is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
##
# Sardana is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
##
# You should have received a copy of the GNU Lesser General Public License
# along with Sardana.  If not, see <http://www.gnu.org/licenses/>.
##
##############################################################################
import time
import numpy
import taurus
from sardana import State
from sardana.pool.pooldefs import SynchDomain, SynchParam
from sardana.pool.controller import TriggerGateController, Access, Memorize, \
    Memorized, Type, Description, DataAccess, DefaultValue


# [WIP] This controller need the Sardana PR 671 !!!!!

LOW = 'low'
HIGH = 'high'
ECAM = 'ecam'


class IcePAPTriggerController(TriggerGateController):
    """Basic IcePAPPositionTriggerGateController.
    """

    organization = "ALBA-Cells"
    gender = "TriggerGate"
    model = "Icepap"

    MaxDevice = 1

    ActivePeriod = 50e-6  # 50 micro seconds

    # The properties used to connect to the ICEPAP motor controller
    ctrl_properties = {
        'IcepapController': {Type: str,
                             Description: 'Icepap Controller name'},
        'DefaultMotor': {Type: str,
                      Description: 'motor base'},
        'UseMasterOut': {Type: bool,
                         Description: 'use the master syncaux output',
                         DefaultValue: True},
        'AxisInfos': {Type: str,
                      Description: 'List of InfoX separated by colons, used '
                                   'when the trigger is generated by the '
                                   'axis UseMasterOut=False',
                      DefaultValue: 'InfoA'}
    }
    ctrl_attributes = {
        # TODO: This attribute should be removed when the Sardana PR 671 is
        # integrated.
        'MasterMotor': {
            Type: str,
            Description: 'Master motor name used to generate the trigger',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
    }

    def __init__(self, inst, props, *args, **kwargs):
        """
        :param inst:
        :param props:
        :param args:
        :param kwargs:
        :return:
        """
        TriggerGateController.__init__(self, inst, props, *args, **kwargs)
        self._log.debug('IcePAPTriggerCtr init....')
        self._time_mode = False
        self._last_motor_name = self.DefaultMotor
        self._motor_name = self._last_motor_name
        self._motor = None
        self._use_master_out = self.UseMasterOut
        self._axis_info_list = map(str.strip, self.AxisInfos.split(','))
        self._ipap_ctrl = taurus.Device(self.IcepapController)
        # self._configureMotor(self.BaseMotor)

    def _set_out(self, out=LOW):
        if self._use_master_out:
            self._motor['syncaux'] = [out]
        else:
            for info_out in self._axis_info_list:
                self._motor[info_out] = out + ' normal'

    def StateOne(self, axis):
        """Get the trigger/gate state"""
        self._log.debug('StateOne(%d): entering...' % axis)
        state = State.On
        status = 'Motor is not generating triggers.'
        if self._motor is not None:
            state = self._motor.state
            status = self._motor.status

        return state, status

    def PreStartOne(self, axis):
        """PreStart the specified trigger"""
        self._log.debug('PreStartOne(%d): entering...' % axis)
        if self._time_mode:
            self._set_out(out=LOW)
        else:
            self._set_out(out=ECAM)
        return True

    def StartOne(self, axis):
        """Overwrite the StartOne method"""
        if not self._time_mode:
            return
        self._set_out(out=HIGH)
        time.sleep(0.01)
        self._set_out(out=LOW)

    def AbortOne(self, axis):
        """Start the specified trigger"""
        self._log.debug('AbortOne(%d): entering...' % axis)
        self._set_out(out=LOW)

    def SetAxisPar(self, axis, name, value):
        idx = axis - 1
        tg = self.triggers[idx]
        name = name.lower()
        pars = ['offset', 'passive_interval', 'repetitions', 'sign',
                'info_channels']
        if name in pars:
            tg[name] = value

    def GetAxisPar(self, axis, name):
        idx = axis - 1
        tg = self.triggers[idx]
        name = name.lower()
        v = tg.get(name, None)
        if v is None:
            msg = ('GetAxisPar(%d). The parameter %s does not exist.'
                   % (axis, name))
            self._log.error(msg)
        return v

    def SynchOne(self, axis, configuration):
        # TODO: implement the configuration for multiples configuration
        synch_group = configuration[0]

        nr_points = synch_group[SynchParam.Repeats]
        if SynchParam.Initial not in synch_group:
            # Synchronization by time (step scan and ct)
            if nr_points > 1:
                msg = 'The IcePAP Trigger Controller is not allowed to ' \
                      'generate multiple trigger synchronized by time'
                raise ValueError(msg)
            else:
                self._time_mode = True

            if not self._use_master_out and \
               self._last_motor_name != self.DefaultMotor:
                raise RuntimeError('The motor used in the scan is not the '
                                   'same than the motor configure with the '
                                   'trigger cable')
            self._configureMotor(self._last_motor_name)

        else:
            self._time_mode = False
            # Synchronization by time and position (continuous scan)
            # TODO: Uncomment next line when Sardana PR 671 was integrated.
            # master = synch_group[SynchParam.Master][SynchDomain.Position]
            master = self._last_motor_name

            if not self._use_master_out and master != self.DefaultMotor:
                raise RuntimeError('The motor used in the scan is not the '
                                   'same than the motor configure with the '
                                   'trigger cable')

            self._configureMotor(master)

            step_per_unit = self._motor['step_per_unit'].value
            offset = self._motor['offset'].value
            sign = self._motor['sign'].value
            initial_user = synch_group[SynchParam.Initial][SynchDomain.Position]
            total_user = synch_group[SynchParam.Total][SynchDomain.Position]
            initial = (initial_user - offset) * (step_per_unit / sign)
            total = total_user * (step_per_unit / sign)
            final = initial + (total * nr_points)
            self._log.debug('IcepapTriggerCtr configuration: %f %f %d %d' %
                            (initial, final, nr_points, total))

            # There is a limitation of numbers of point on the icepap (8192)
            # ecamdat = motor.getAttribute('ecamdatinterval')
            # ecamdat.write([initial, final, nr_points], with_read=False)

            # The ecamdattable attribute is protected against non increasing
            # list at the pyIcePAP library level. HOWEVER, is not protected
            # agains list with repeated elements
            trigger_positions_tables = numpy.linspace(int(initial),
                                                      int(final-total),
                                                      int(nr_points))

            self._log.debug('trigger table %r' % trigger_positions_tables)
            ecamdattable = self._motor.getAttribute('ecamdattable')
            ecamdattable.write(trigger_positions_tables, with_read=False)



    def _configureMotor(self, motor_name):
        if motor_name != self._last_motor_name or self._motor is None:
            self._last_motor_name = motor_name
            self._motor = taurus.Device(self._last_motor_name)
            if self._use_master_out:
                motor_axis = self._motor.get_property('axis')['axis'][0]
                # remove previous connection and connect the new motor
                pmux = eval(self._ipap_ctrl['PMUX'].value)
                for p in pmux:
                    if 'E0' in p:
                        self._ipap_ctrl['PMUX'] = 'remove e0'
                        break
                self._ipap_ctrl['PMUX'] = 'hard aux b{0} e0'.format(motor_axis)

                pmux = self._ipap_ctrl['PMUX'].value
                self._log.debug('_connectMotor PMUX={0}'.format(pmux))

    def SetCtrlPar(self, parameter, value):
        param = parameter.lower()
        if param == 'mastermotor':
            self._configureMotor(value)
        else:
            super(IcePAPTriggerGateController,
                  self).SetCtrlPar(parameter, value)

    def GetCtrlPar(self, parameter):
        param = parameter.lower()
        if param == 'mastermotor':
            value = self._last_motor_name
        else:
            value = super(IcePAPTriggerGateController,
                          self).GetCtrlPar(parameter)
        return value
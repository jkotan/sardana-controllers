#!/usr/bin/env python

import PyTango
from sardana import State
from sardana.pool.controller import CounterTimerController, Type, \
    Description, Access, DataAccess, Memorize, NotMemorized, \
    Memorized, DefaultValue, FGet, FSet
from sardana.pool import AcqSynch


# TODO: WIP version.

LIMA_ATTRS = {'cameramode': 'camera_mode',
              'cameratype': 'camera_type',
              # 'instrumentname': 'instrument_name',
              'savingcommonheader': 'saving_common_header',
              'savingdirectory': 'saving_directory',
              'savingformat': 'saving_format',
              'savingframeperfile': 'saving_frame_per_file',
              'savingheaderdelimiter': 'saving_header_delimiter',
              'savingmanagemode': 'saving_manage_mode',
              'savingmaxwritingtask': 'saving_max_writing_task',
              'savingmode': 'saving_mode',
              'savingnextnumber': 'saving_next_number',
              'savingoverwritepolicy': 'saving_overwrite_policy',
              'savingprefix': 'saving_prefix',
              'savingsuffix': 'saving_suffix'}


class LimaCoTiCtrl(CounterTimerController):
    """This class is a Tango Sardana Counter Timer Controller for any
    Lima Device. This controller is used as an alternative to current
    2D controller. It has a single (master) axis which it provides the
    integration time as a value of an experimental channel in a measurement
    group.
    This controller avoids passing the image which was known to slow the
    acquisition process ans can be used as a workaround before the full
    integration of the 2D Sardana controller."""

    gender = "LimaAcquisition"
    model = "LimaCCD"
    organization = "CELLS - ALBA"
    image = "Lima_ctrl.png"
    logo = "ALBA_logo.png"

    MaxDevice = 1

    class_prop = {}
    ctrl_attributes = {
        'CameraModel': {
            Type: str,
            Description: 'LimaCCD attribute camera_model',
            Access: DataAccess.ReadOnly,
            Memorize: NotMemorized},
        'CameraType': {
            Type: str,
            Description: 'LimaCCD attribute camera_type',
            Access: DataAccess.ReadOnly,
            Memorize: NotMemorized},
        'ExpectedScanImages': {
            Type: int,
            Description: 'Expected Images on the scan. It will set by the '
                         'recorder',
            Access: DataAccess.ReadWrite,
            Memorize: NotMemorized,
            DefaultValue: 0},
        'InstrumentName': {
            Type: str,
            Description: 'LimaCCD attribute instrument_name',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingCommonHeader': {
            Type: [str, ],
            Description: 'LimaCCD attribute saving_common_header',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingDirectory': {
            Type: str,
            Description: 'LimaCCD attribute saving_directory',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingFormat': {
            Type: str,
            Description: 'LimaCCD attribute saving_format',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingFramePerFile': {
            Type: int,
            Description: 'LimaCCD attribute saving_frame_per_file',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingHeaderDelimiter': {
            Type: [str, ],
            Description: 'LimaCCD attribute saving_header_delimiter',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingIndexFormat': {
            Type: str,
            Description: 'LimaCCD attribute saving_index_format',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingManagedMode': {
            Type: str,
            Description: 'LimaCCD attribute saving_managed_mode',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingMaxWritingTask': {
            Type: int,
            Description: 'LimaCCD attribute saving_max_writing_task',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingMode': {
            Type: str,
            Description: 'LimaCCD attribute saving_mode. The controller will'
                         'set it to MANUAL on the startup.',
            Access: DataAccess.ReadWrite,
            Memorize: NotMemorized},
        'SavingNextNumber': {
            Type: int,
            Description: 'LimaCCD attribute saving_next_number',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingOverwritePolicy': {
            Type: str,
            Description: 'LimaCCD attribute saving_overwrite_policy',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingPrefix': {
            Type: str,
            Description: 'LimaCCD attribute saving_prefix',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        'SavingSuffix': {
            Type: str,
            Description: 'LimaCCD attribute saving_suffix',
            Access: DataAccess.ReadWrite,
            Memorize: Memorized},
        }

    axis_attributes = {}

    ctrl_properties = {
        'LimaCCDDeviceName': {Type: str, Description: 'Detector device name'},
        'HardwareSync': {Type: str,
                         Description: 'acq_trigger_mode for hardware mode'},
        }

    def __init__(self, inst, props, *args, **kwargs):
        CounterTimerController.__init__(self, inst, props, *args, **kwargs)
        self._log.debug("__init__(%s, %s): Entering...", repr(inst),
                        repr(props))

        try:
            self._limaccd = PyTango.DeviceProxy(self.LimaCCDDeviceName)
            self._limaccd.reset()
        except PyTango.DevFailed as e:
            raise RuntimeError('__init__(): Could not create a device proxy '
                               'from following device name: %s.\nException: '
                               '%s ' % (self.LimaCCDDeviceName, e))

        self._data_buff = {}
        self._hw_state = None
        self._last_image_read = -1
        self._repetitions = 0
        self._state = None
        self._status = None
        self._new_data = False
        self._int_time = 0
        self._latency_time = 0
        self._expected_scan_images = 0
        self._hardware_trigger = self.HardwareSync
        self._saving_folder_name = ''
        self._synchronization = AcqSynch.SoftwareTrigger
        self._abort_flg = False
        self._load_flag = False
        self._start_flg = False

        # Check if the LimaCCD has the instrument name attribute
        attrs = attrs_lima = self._limaccd.get_attribute_list()
        if 'instrument_name' in attrs:
            self._instrument_name = None
        else:
            self._instrument_name = ''

    def _clean_acquisition(self):
        acq_ready = self._limaccd.read_attribute('acq_status').value.lower()
        if acq_ready != 'ready':
            self._limaccd.stopAcq()
        self._last_image_read = -1
        self._repetitions = 0
        self._new_data = False
        self._abort_flg = False
        self._start_flg = False

    def AddDevice(self, axis):
        if axis != 1:
            raise ValueError('This controller only have the axis 1')
        self._data_buff[1] = []

    def DeleteDevice(self, axis):
        self._data_buff.pop(axis)

    def StateAll(self):
        attr_list = ['acq_status', 'ready_for_next_acq',
                     'ready_for_next_image']
        values = [i.value for i in self._limaccd.read_attributes(attr_list)]
        acq_ready, ready_for_next_acq, ready_for_next_image = values
        self._hw_state = acq_ready

        if acq_ready not in ['Ready', 'Running']:
            self._state = State.Fault
            self._status = 'The LimaCCD state is: {0}'.format(acq_ready)
            return

        if self._expected_scan_images == 0:
            if acq_ready == 'Ready':
                self._state = State.On
                self._status = 'The LimaCCD is ready to acquire'
            else:
                self._state = State.Moving
                self._status = 'The LimaCCD is acquiring'
        else:
            if self._repetitions == 1:
                # Step scan or Continuous scan by software synchronization
                if ready_for_next_image:
                    self._state = State.On
                    self._status = 'The LimaCCD is ready to acquire'
                else:
                    self._state = State.Moving
                    self._status = 'The LimaCCD is acquiring'
                if acq_ready == 'Ready':
                    self._expected_scan_images = 0
                    self._load_flag = False
            else:
                if self._synchronization == AcqSynch.HardwareTrigger:
                    # Continuous scan
                    if acq_ready == 'Ready':
                        if self._last_image_read != (self._repetitions - 1)\
                                and not self._abort_flg:
                            self._log.warning('The LimaCCDs finished but the'
                                              'ctrl did not read all the data '
                                              'yet. Last image read %r' %
                                              self._last_image_read)
                            self._state = State.Moving
                            self._status = 'The LimaCCD is acquiring'
                        else:
                            self._state = State.On
                            self._status = 'The LimaCCD is ready to acquire'
                            self._expected_scan_images = 0
                            self._load_flag = 0
                    else:
                        self._state = State.Moving
                        self._status = 'The LimaCCD is acquiring'

        self._log.debug('Leaving Stateall %s %s' % (self._state, self._status))

    def StateOne(self, axis):
        return self._state, self._status

    def LoadOne(self, axis, value, repetitions):
        self._log.debug('LoadOne flag=%s images=%s' %
                        (self._load_flag, self._expected_scan_images))
        if self._load_flag:
            return

        # Detect if is using the recorder
        if self._expected_scan_images == 0:
            acq_nb_frames = repetitions
            self._load_flag = False
        else:
            self._load_flag = True
            acq_nb_frames = self._expected_scan_images

        self._clean_acquisition()
        if axis != 1:
            raise RuntimeError('The master channel should be the axis 1')

        self._int_time = value
        self._repetitions = repetitions

        if self._synchronization == AcqSynch.SoftwareTrigger:
            acq_trigger_mode = 'INTERNAL_TRIGGER_MULTI'
        elif self._synchronization == AcqSynch.HardwareTrigger:
            acq_trigger_mode = self._hardware_trigger
        else:
            # TODO: Implement the hardware gate
            raise ValueError('LimaCoTiCtrl allows only Software or Hardware '
                             'triggering')
        values = [['acq_expo_time', self._int_time],
                  ['acq_nb_frames', acq_nb_frames],
                  ['latency_time', self._latency_time],
                  ['acq_trigger_mode', acq_trigger_mode]]
        self._limaccd.write_attributes(values)
        self._limaccd.prepareAcq()

    def PreStartAll(self):
        return True

    def StartAll(self):
        self._abort_flg = False
        if self._expected_scan_images > 0 and self._repetitions > 1 and \
                self._start_flg:
            return
        self._limaccd.startAcq()
        self._start_flg = True

    def ReadAll(self):
        axis = 1
        attr = 'last_image_ready'
        new_image_ready = self._limaccd.read_attribute(attr).value
        if self._repetitions == 1:
            # Step scan or Continuous scan by software
            self._data_buff[axis] = [self._int_time]
        else:
            self._data_buff[axis] = []
            if new_image_ready == self._last_image_read:
                self._new_data = False
                return
            self._last_image_read += 1
            new_data = (new_image_ready - self._last_image_read) + 1
            if new_image_ready == 0:
                new_data = 1
            self._data_buff[axis] = [self._int_time] * new_data
        self._last_image_read = new_image_ready
        self._log.debug('Leaving ReadAll %r' % len(self._data_buff[axis]))

    def ReadOne(self, axis):
        self._log.debug('Entering in  ReadOnly')
        if self._repetitions == 1:
            value = self._data_buff[axis][0]
        else:
            value = self._data_buff[axis]
        return value

    def AbortOne(self, axis):
        self._log.debug('AbortOne in')
        self._abort_flg = True
        self._load_flag = False
        self._expected_scan_images = 0
        self._clean_acquisition()

###############################################################################
#                Controller Extra Attribute Methods
###############################################################################
    def getInstrumentName(self):
        self._log.debug('getIntrumentName')

        if self._instrument_name is None:
            value = self._limaccd.read_attribute('instrument_name').value
        else:
            value = self._instrument_name
        return  value

    def setInstrumentName(self, value):
        self._log.debug('setIntrumentName with %s'%value)
        if self._instrument_name is None:
            self._limaccd.write_attribute('instrument_name', value)
        else:
            self._instrument_name = value

    def SetCtrlPar(self, parameter, value):
        self._log.debug('SetCtrlPar %s %s' % (parameter, value))
        param = parameter.lower()
        if param == 'expectedscanimages':
            self._expected_scan_images = value
            self._load_flag = False

        elif param in LIMA_ATTRS:
            attr = LIMA_ATTRS[param]
            self._limaccd.write_attribute(attr, value)
        else:
            super(LimaCoTiCtrl, self).SetCtrlPar(parameter, value)

    def GetCtrlPar(self, parameter):
        param = parameter.lower()
        if param == 'expectedscanimages':
            value = self._expected_scan_images
        elif param in LIMA_ATTRS:
            # TODO: Verify instrument_name attribute
            attr = LIMA_ATTRS[param]
            value = self._limaccd.read_attribute(attr).value
        else:
            value = super(LimaCoTiCtrl, self).GetCtrlPar(parameter)

        return value

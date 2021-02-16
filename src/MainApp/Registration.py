from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from upyiot.comm.Messaging.MessageExchange import MessageExchange
from upyiot.comm.Messaging.MessageFormatter import MessageFormatter
from upyiot.middleware.SubjectObserver.SubjectObserver import Observer
from upyiot.system.Service.Service import Service
from upyiot.system.Service.Service import ServiceException
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.Util import DeviceId
from upyiot.system.Util.Version import Version

from Schemas.RegistrationInfo import RegistrationInfo
from Schemas import Metadata

from micropython import const


class RegistrationService(Service):
    REG_SERVICE_MODE = Service.MODE_RUN_ONCE

    def __init__(self):
        super().__init__("Reg", self.REG_SERVICE_MODE, {})


class Registration(RegistrationService, Observer):

    def __init__(self, msg_ex_obj, reg_info_spec):
        """
        Registration object, implements the RegistrationService and Observer classes.
        :param msg_ex_obj: MessageExchange object
        :type msg_ex_obj: <MessageExchange>
        :param reg_info_spec: Registration info specification
        :type reg_info_spec: <<MessageSpecification>RegistrationInfo>
        """
        super().__init__()
        self.MsgEx = msg_ex_obj
        self.RegInfoSpec = reg_info_spec
        self.Version = Version.Instance()
        self.Log = ExtLogging.Create("Reg")
        return

    def SvcInit(self):
        """
        Initialize the Registration service.
        """


    def SvcRun(self):
        """
        Run the Registration service.
        The Registration service composes the registration info message, queues the message and activates
        the Message Exchange service.
        :except
        """
        reg_msg = self.RegInfoSpec.DataDef.copy()

        # Compose the registration info message.
        reg_msg[RegistrationInfo.DATA_KEY_HW_ID] = DeviceId.DeviceIdString()
        reg_msg[RegistrationInfo.DATA_KEY_SW_VER] = self.Version.SwVersionEncoded()
        reg_msg[RegistrationInfo.DATA_KEY_FW_VER] = 100

        self.Log.info("Registration info: {}".format(reg_msg))

        reg_msg_meta = {
            Metadata.MSG_META_TYPE: self.RegInfoSpec.Type,
            Metadata.MSG_META_SUBTYPE: self.RegInfoSpec.Subtype,
        }

        # Put the registration info in the Message Exchange queue and activate the service.
        # TODO: Add urgency to the Put function to implicitly activate the Message Exchange service.
        # TODO: Manual activation should not be necessary and should not be the responsibility of the user.
        self.MsgEx.MessagePut(msg_data_dict=reg_msg,
                              msg_type=self.RegInfoSpec.Type,
                              msg_subtype=self.RegInfoSpec.Subtype,
                              msg_meta_dict=reg_msg_meta)
        self.MsgEx.SvcActivate()
        self.Log.info("Registration complete")

    def DeviceIsRegistered(self):
        """
        Check if the device has sent its registration info.
        :return: True if the device is registered.
        :rtype: boolean
        """
        return self.SvcLastRun > 0

    def Update(self, connected):
        """
        Connection state observer callback. Updates the connection state.
        Must be attached to a connection state subject.
        :param connected: Connection state.
        :type connected: boolean
        """
        if connected is True and self.DeviceIsRegistered() is False:
            self.SvcActivate()

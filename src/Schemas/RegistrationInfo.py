from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from micropython import const


class RegistrationInfo(MessageSpecification):

    TYPE_REGISTRATION       = const(1)
    SUBTYPE_REGISTRATION    = const(0)

    DATA_KEY_HW_ID  = const(101)
    DATA_KEY_SW_VER = const(102)
    DATA_KEY_FW_VER = const(103)

    DIRECTION_REGISTRATION = MessageSpecification.MSG_DIRECTION_SEND

    def __init__(self):
        self.DataDef = {RegistrationInfo.DATA_KEY_HW_ID: "",
                        RegistrationInfo.DATA_KEY_SW_VER: 201,
                        RegistrationInfo.DATA_KEY_FW_VER: 101
                        }

        super().__init__(RegistrationInfo.TYPE_REGISTRATION,
                         RegistrationInfo.SUBTYPE_REGISTRATION,
                         self.DataDef,
                         "",
                         RegistrationInfo.DIRECTION_REGISTRATION)

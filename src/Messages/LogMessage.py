from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from micropython import const


class LogMessage(MessageSpecification):

    TYPE_LOG_MSG        = const(1)
    SUBTYPE_LOG_MSG     = const(1)
    URL_LOG_MSG         = "<pn>/<id>/log"
    DATA_KEY_LOG_MSG  = "msg"
    DATA_DEF_LOG_MSG    = {DATA_KEY_LOG_MSG: ""}
    DIRECTION_LOG_MSG   = MessageSpecification.MSG_DIRECTION_SEND

    def __init__(self):
        super().__init__(LogMessage.TYPE_LOG_MSG,
                         LogMessage.SUBTYPE_LOG_MSG,
                         LogMessage.DATA_DEF_LOG_MSG,
                         LogMessage.URL_LOG_MSG,
                         LogMessage.DIRECTION_LOG_MSG)


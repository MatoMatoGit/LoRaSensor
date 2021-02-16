from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from micropython import const


class EventReport(MessageSpecification):

    TYPE_REPORT              = const(0)
    SUBTYPE_EVENT_REPORT     = const(1)

    DATA_KEY_EVENT            = const(104)

    DIRECTION_REPORT   = MessageSpecification.MSG_DIRECTION_SEND

    def __init__(self):
        self.DataDef = {EventReport.DATA_KEY_EVENT: []}

        super().__init__(EventReport.TYPE_REPORT,
                         EventReport.SUBTYPE_EVENT_REPORT,
                         self.DataDef,
                         "",
                         EventReport.DIRECTION_REPORT)


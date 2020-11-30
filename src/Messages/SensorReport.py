from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from micropython import const


class SensorReport(MessageSpecification):

    TYPE_SENSOR_REPORT        = const(0)
    SUBTYPE_SENSOR_REPORT     = const(0)

    DATA_KEY_MOIST            = const(101)
    DATA_KEY_BAT              = const(102)
    DATA_KEY_TEMP             = const(103)

    DIRECTION_SENSOR_REPORT   = MessageSpecification.MSG_DIRECTION_SEND

    def __init__(self):
        self.DataDef = {SensorReport.DATA_KEY_MOIST: 0,
                        SensorReport.DATA_KEY_BAT: 100,
                        SensorReport.DATA_KEY_TEMP: 20}

        super().__init__(SensorReport.TYPE_SENSOR_REPORT,
                         SensorReport.SUBTYPE_SENSOR_REPORT,
                         self.DataDef,
                         "",
                         SensorReport.DIRECTION_SENSOR_REPORT)


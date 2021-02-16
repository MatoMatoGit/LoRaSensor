from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from micropython import const


class SensorReport(MessageSpecification):

    TYPE_REPORT              = const(0)

    DATA_KEY_MEASUREMENTS     = const(100)

    DIRECTION_REPORT   = MessageSpecification.MSG_DIRECTION_SEND

    def __init__(self, subtype):
        self.DataDef = {SensorReport.DATA_KEY_MEASUREMENTS: []}

        super().__init__(SensorReport.TYPE_REPORT,
                         subtype,
                         self.DataDef,
                         "",
                         SensorReport.DIRECTION_REPORT)


class MoistureSensorReport(SensorReport):

    SUBTYPE_MOISTURE_REPORT = const(1)

    def __init__(self):
        super().__init__(self.SUBTYPE_MOISTURE_REPORT)


class BatterySensorReport(SensorReport):

    SUBTYPE_BATTERY_REPORT = const(2)

    def __init__(self):
        super().__init__(self.SUBTYPE_BATTERY_REPORT)


class TemperatureSensorReport(SensorReport):

    SUBTYPE_TEMPERATURE_REPORT = const(3)

    def __init__(self):
        super().__init__(self.SUBTYPE_TEMPERATURE_REPORT)


# upyiot modules
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.SystemTime.SystemTime import SystemTime
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.system.Service.ServiceScheduler import Service
from upyiot.system.Util import ResetReason
from upyiot.system.Util import DeviceId
from upyiot.comm.Messaging.Message import Message
from upyiot.comm.Messaging.MessageTemplate import MessageTemplate
from upyiot.comm.Messaging.MessageExchange import MessageExchange
from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from upyiot.comm.Messaging.MessageFormatter import MessageFormatter
from upyiot.comm.Messaging.Protocol.LoraProtocol import LoraProtocol
from upyiot.comm.Messaging.Parser.CborParser import CborParser
from upyiot.middleware.Sensor import Sensor
from upyiot.middleware.StructFile import StructFile
from upyiot.drivers.Sleep.DeepSleep import DeepSleep
from upyiot.drivers.Sensors.DummySensor import DummySensor
from upyiot.drivers.Sensors.InternalTemp import InternalTemp
from upyiot.drivers.Modems.Sx127x.sx127x import TTN, SX127x
from upyiot.drivers.Modems.Sx127x.config import *

# SmartSensor modules
from Messages.LogMessage import LogMessage
from Messages.SensorReport import SensorReport
from Messages import MetadataSchema
#from Config.Hardware import Pins
from MainApp.PowerManager import PowerManager

# micropython modules
import network
from network import WLAN
from micropython import const
import machine
from machine import Pin, SPI
import ubinascii
import utime


class MainApp:

    DummySamples = [20, 30, 25, 11, -10, 40, 32]

    DIR = "/"
    ID = str(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
    RETRIES = 3
    FILTER_DEPTH = const(1)
    DEEPSLEEP_THRESHOLD_SEC = const(5)

    SamplesPerMessage   = const(1)

    # Service intervals in seconds.
    MsgExInterval           = const(15)
    SensorReadInterval      = const(15)
    Lora = None
    PowerMngr = None

    def __init__(self):
        return

    def Setup(self):
        # Configure the ExtLogging class.
        ExtLogging.ConfigGlobal(level=ExtLogging.INFO, stream=None, dir="",
                                file_prefix="log_", line_limit=1000, file_limit=10)
        StructFile.InitLogger()

        self.Log = ExtLogging.Create("Main")

        self.Log.info("Device ID: {}".format(DeviceId.DeviceId()))

        rst_reason = ResetReason.ResetReason()
        self.Log.debug("Reset reason: {}".format(ResetReason.ResetReasonToString(rst_reason)))

        # Create driver instances.
        self.DummySensorDriver = DummySensor(self.DummySamples)

        self.InternalTemp = InternalTemp()

        self.Ttn = TTN(ttn_config['devaddr'], ttn_config['nwkey'],
                       ttn_config['app'], country=ttn_config['country'])

        self.LoraSpi = SPI(baudrate = 10000000,
                polarity = 0, phase = 0, bits = 8, firstbit = SPI.MSB,
                sck = Pin(device_config['sck'], Pin.OUT, Pin.PULL_DOWN),
                mosi = Pin(device_config['mosi'], Pin.OUT, Pin.PULL_UP),
                miso = Pin(device_config['miso'], Pin.IN, Pin.PULL_UP))

        MainApp.Lora = SX127x(self.LoraSpi, pins=device_config, lora_parameters=lora_parameters, ttn_config=self.Ttn)

        self.LoraProtocol = LoraProtocol(MainApp.Lora)

        self.DummySensor = Sensor.Sensor(self.DIR,
                                        "Dummy",
                                        self.FILTER_DEPTH, self.DummySensorDriver,
                                        samples_per_read=1,
                                        dec_round=True,
                                        store_data=False)

        self.TempSensor = Sensor.Sensor(self.DIR,
                                        "Temp",
                                        self.FILTER_DEPTH, self.InternalTemp,
                                        samples_per_read=1,
                                        dec_round=True,
                                        store_data=False)

        self.MsgEx = MessageExchange(self.DIR,
                                     self.LoraProtocol,
                                     self.RETRIES)

        self.Scheduler = ServiceScheduler(self.DEEPSLEEP_THRESHOLD_SEC)

        self.MsgEx.SvcModeSet(Service.MODE_RUN_ONCE)
        self.DummySensor.SvcModeSet(Service.MODE_RUN_ONCE)
        self.TempSensor.SvcModeSet(Service.MODE_RUN_ONCE)

        # Set service dependencies.
        self.MsgEx.SvcDependencies({self.DummySensor: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_RUN,
                                    self.TempSensor: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_RUN})
        self.DummySensor.SvcDependencies({})
        self.TempSensor.SvcDependencies({})

        # Register all services to the scheduler.
        self.Scheduler.ServiceRegister(self.MsgEx)
        self.Scheduler.ServiceRegister(self.DummySensor)
        self.Scheduler.ServiceRegister(self.TempSensor)

        self.Parser = CborParser()
        Message.SetParser(self.Parser)

        MessageTemplate.SectionsSet(MetadataSchema.MSG_SECTION_META, MetadataSchema.MSG_SECTION_DATA)
        MessageTemplate.MetadataTemplateSet(MetadataSchema.Metadata, MetadataSchema.MetadataFuncs)

        # Create message specifications.
        self.SensorReportSpec = SensorReport()
        # self.LogMsgSpec = LogMessage()

        #sensor_report_meta = {
        #   SensorReport.MSG_META_TYPE: self.SensorReportSpec.Type
        #}
        # Create MessageFormatters and couple them with their message specs.
        self.ReportFmt = MessageFormatter(self.MsgEx,
                                          MessageFormatter.SEND_ON_COMPLETE,
                                          self.SensorReportSpec,
                                          None)

        # Register message specs for exchange.
        self.MsgEx.RegisterMessageType(self.SensorReportSpec)
        # self.MsgEx.RegisterMessageType(self.LogMsgSpec)

        # Create observers for the sensor data.
        self.MoistObserver = self.ReportFmt.CreateObserver(SensorReport.DATA_KEY_MOIST, self.SamplesPerMessage)
        self.BatteryObserver = self.ReportFmt.CreateObserver(SensorReport.DATA_KEY_BAT, self.SamplesPerMessage)
        self.TempObserver = self.ReportFmt.CreateObserver(SensorReport.DATA_KEY_TEMP, self.SamplesPerMessage)

        # Link the observers to the sensors.
        self.DummySensor.ObserverAttachNewSample(self.MoistObserver)
        self.TempSensor.ObserverAttachNewSample(self.TempObserver)

        self.Scheduler.DeepSleep.RegisterCallbackBeforeDeepSleep(MainApp.LoraSleep)

        # Set intervals for all services.
        self.MsgEx.SvcIntervalSet(self.MsgExInterval)
        self.DummySensor.SvcIntervalSet(self.SensorReadInterval)
        self.TempSensor.SvcIntervalSet(self.SensorReadInterval)

        self.BatteryObserver.Update(100)

        MainApp.PowerMngr = PowerManager.PowerManager()

        self.Log.info("Finished initialization.")


    def Reset(self):
        self.MsgEx.Reset()
        self.DummySensor.SamplesDelete()

    def Run(self):
        self.Log.info("Starting scheduler")
        self.MsgEx.SvcActivate()
        self.Scheduler.Run(4)
        self.Scheduler.RequestDeepSleep(20)

    @staticmethod
    def LoraSleep():
        MainApp.Lora.sleep()
        ExtLogging.Stop()
        while True:
            MainApp.PowerMngr.Sleep(1000 * 3590) # 86400
            utime.sleep(10)


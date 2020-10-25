
# upyiot modules
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.SystemTime.SystemTime import SystemTime
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.system.Service.ServiceScheduler import Service
from upyiot.system.Util import ResetReason
from upyiot.comm.Messaging.Message import Message
from upyiot.comm.Messaging.MessageTemplate import MessageTemplate
from upyiot.comm.Messaging.MessageExchange import MessageExchange
from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from upyiot.comm.Messaging.MessageFormatter import MessageFormatter
from upyiot.comm.Messaging.Protocol.LoraProtocol import LoraProtocol
from upyiot.comm.Messaging.Parser.CborParser import CborParser
from upyiot.middleware.Sensor import Sensor
from upyiot.drivers.Sensors.DummySensor import DummySensor
from upyiot.drivers.Modems.Sx127x.sx127x import TTN, SX127x
from upyiot.drivers.Modems.Sx127x.config import *

# SmartSensor modules
from Messages.LogMessage import LogMessage
from Messages.SensorReport import SensorReport
from Messages.MetadataSchema import *
from Config.Hardware import Pins

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
    MsgExInterval           = const(60)
    SensorReadInterval      = const(15)

    def __init__(self):
        return

    def Setup(self):
        print("Device ID: {}".format(self.ID))

        rst_reason = ResetReason.ResetReason()
        print("[Setup] Reset reason: {}".format(ResetReason.ResetReasonToString(rst_reason)))

        # Create driver instances.
        self.DummySensorDriver = DummySensor(self.DummySamples)

        self.Ttn = TTN(ttn_config['devaddr'], ttn_config['nwkey'],
                       ttn_config['app'], country=ttn_config['country'])

        self.LoraSpi = SPI(baudrate = 10000000,
                polarity = 0, phase = 0, bits = 8, firstbit = SPI.MSB,
                sck = Pin(device_config['sck'], Pin.OUT, Pin.PULL_DOWN),
                mosi = Pin(device_config['mosi'], Pin.OUT, Pin.PULL_UP),
                miso = Pin(device_config['miso'], Pin.IN, Pin.PULL_UP))

        self.Lora = SX127x(self.LoraSpi, pins=device_config, lora_parameters=lora_parameters, ttn_config=self.Ttn)

        self.LoraProtocol = LoraProtocol(self.Lora)

        self.DummySensor = Sensor.Sensor(self.DIR,
                                        "Dummy",
                                        self.FILTER_DEPTH, self.DummySensorDriver,
                                        self.FILTER_DEPTH,
                                        samples_per_read=1,
                                        dec_round=True,
                                        store_data=False)

        self.MsgEx = MessageExchange(self.DIR,
                                     self.LoraProtocol,
                                     self.RETRIES)

        self.Scheduler = ServiceScheduler(self.DEEPSLEEP_THRESHOLD_SEC)

        # Set service dependencies.
        self.MsgEx.SvcDependencies({})
        self.DummySensor.SvcDependencies({})

        # Register all services to the scheduler.
        self.Scheduler.ServiceRegister(self.MsgEx)
        self.Scheduler.ServiceRegister(self.DummySensor)

        self.Parser = CborParser()
        Message.SetParser(self.Parser)

        MessageTemplate.SectionsSet(MetadataSchema.MSG_SECTION_META, MetadataSchema.MSG_SECTION_DATA)
        MessageTemplate.MetadataTemplateSet(MetadataSchema.Metadata, MetadataSchema.MetadataFuncs)

        # Create message specifications.
        self.SensorReportSpec = SensorReport()
        # self.LogMsgSpec = LogMessage()

        # Create MessageFormatters and couple them with their message specs.
        self.ReportFmt = MessageFormatter(self.MsgEx,
                                          MessageFormatter.SEND_ON_COMPLETE,
                                          self.SensorReportSpec,
                                          self.MsgMetadata)

        # Register message specs for exchange.
        self.MsgEx.RegisterMessageType(self.SensorReportSpec)
        self.MsgEx.RegisterMessageType(self.LogMsgSpec)

        # Create observers for the sensor data.
        self.MoistObserver = self.ReportFmt.CreateObserver(SensorReport.DATA_KEY_MOIST, self.SamplesPerMessage)
        self.BatteryObserver = self.ReportFmt.CreateObserver(SensorReport.DATA_KEY_BAT, self.SamplesPerMessage)

        # Link the observers to the sensors.
        self.DummySensor.ObserverAttachNewSample(self.MoistObserver)

        # Create a stream for the log messages.
        # self.LogStream = self.LogAdapt.CreateStream(LogMessage.DATA_KEY_LOG_MSG,
        #                                            ExtLogging.WRITES_PER_LOG)

        # Configure the ExtLogging class.
        # ExtLogging.ConfigGlobal(level=ExtLogging.INFO, stream=self.LogStream)

        # Set intervals for all services.
        self.MsgEx.SvcIntervalSet(self.MsgExInterval)
        self.DummySensor.SvcIntervalSet(self.SensorReadInterval)

    def Reset(self):
        self.MsgEx.Reset()
        self.DummySensor.SamplesDelete()

    def Run(self):
        self.Scheduler.Run()
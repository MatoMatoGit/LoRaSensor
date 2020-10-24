
# upyiot modules
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.SystemTime.SystemTime import SystemTime
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.system.Service.ServiceScheduler import Service
from upyiot.system.Util import ResetReason
from upyiot.comm.Messaging.MessageExchange import MessageExchange
from upyiot.comm.Messaging.MessageSpecification import MessageSpecification
from upyiot.comm.Messaging.MessageFormatter import MessageFormatter
from upyiot.comm.Messaging.Protocol.LoraProtocol import LoraProtocol
from upyiot.middleware.Sensor import Sensor

from upyiot.drivers.Sensors.DummySensor import DummySensor
from upyiot.drivers.Modems.Sx127x.sx127x import TTN, SX127x
from upyiot.drivers.Modems.Sx127x.config import *

# SmartSensor modules
from Messages.LogMessage import LogMessage
from Messages.SensorReport import SensorReportTemp
from Messages.SensorReport import SensorReportMoist
from Messages.SensorReport import SensorReportLight
from UserInterface.Notification import Notifyer
from UserInterface.Notification import NotificationRange
from UserInterface.Notification import Notification
from UserInterface.UserButton import UserButton
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

    ID = str(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
    RETRIES = 3
    FILTER_DEPTH = const(1)
    DEEPSLEEP_THRESHOLD_SEC = const(5)

    SamplesPerMessage   = const(1)

    # Service intervals in seconds.
    MsgExInterval           = const(60)
    EnvSensorReadInterval   = const(15)
    NotificationInterval    = const(15)

    def __init__(self):
        return

    def Setup(self):

        rst_reason = ResetReason.ResetReason()
        print("[Setup] Reset reason: {}".format(ResetReason.ResetReasonToString(rst_reason)))

        # Create driver instances.
        self.DummySensorDriver = DummySensor(self.DummySamples)

        self.Ttn = TTN(ttn_config['devaddr'], ttn_config['nwkey'], ttn_config['app'], country=ttn_config['country'])

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

        # Create message specifications.
        self.TempMsgSpec = SensorReportTemp()
        self.MoistMsgSpec = SensorReportMoist()
        self.LightMsgSpec = SensorReportLight()
        self.LogMsgSpec = LogMessage()

        # Create MessageFormatAdapters and couple them with their message specs.
        self.TempAdapt = MessageFormatAdapter(self.MsgEp,
                                              MessageFormatAdapter.SEND_ON_COMPLETE,
                                              self.TempMsgSpec)
        self.MoistAdapt = MessageFormatAdapter(self.MsgEp,
                                               MessageFormatAdapter.SEND_ON_COMPLETE,
                                               self.MoistMsgSpec)
        self.LightAdapt = MessageFormatAdapter(self.MsgEp,
                                               MessageFormatAdapter.SEND_ON_COMPLETE,
                                               self.LightMsgSpec)
        self.LogAdapt = MessageFormatAdapter(self.MsgEp,
                                             MessageFormatAdapter.SEND_ON_COMPLETE,
                                             self.LogMsgSpec)

        # Register message specs for exchange.
        self.MsgEx.RegisterMessageType(self.TempMsgSpec)
        self.MsgEx.RegisterMessageType(self.MoistMsgSpec)
        self.MsgEx.RegisterMessageType(self.LightMsgSpec)
        self.MsgEx.RegisterMessageType(self.LogMsgSpec)

        # Create observers for the sensor data.
        self.TempObserver = self.TempAdapt.CreateObserver(
            SensorReportTemp.DATA_KEY_SENSOR_REPORT_SAMPLES,
            self.SamplesPerMessage)
        self.MoistObserver = self.MoistAdapt.CreateObserver(
            SensorReportMoist.DATA_KEY_SENSOR_REPORT_SAMPLES,
            self.SamplesPerMessage)
        self.LightObserver = self.LightAdapt.CreateObserver(
            SensorReportLight.DATA_KEY_SENSOR_REPORT_SAMPLES,
            self.SamplesPerMessage)

        # Link the observers to the sensors.
        self.TempSensor.ObserverAttachNewSample(self.TempObserver)
        self.MoistSensor.ObserverAttachNewSample(self.MoistObserver)
        self.MoistSensor.ObserverAttachNewSample(self.MoistNotif)
        self.LightSensor.ObserverAttachNewSample(self.LightObserver)

        # Create a stream for the log messages.
        self.LogStream = self.LogAdapt.CreateStream(LogMessage.DATA_KEY_LOG_MSG,
                                                    ExtLogging.WRITES_PER_LOG)

        # Configure the ExtLogging class.
        ExtLogging.ConfigGlobal(level=ExtLogging.INFO, stream=self.LogStream)

        # Set intervals for all services.
        self.MsgEx.SvcIntervalSet(self.MsgExInterval)
        self.MoistSensor.SvcIntervalSet(self.EnvSensorReadInterval)
        self.TempSensor.SvcIntervalSet(self.EnvSensorReadInterval)
        self.LightSensor.SvcIntervalSet(self.EnvSensorReadInterval)
        self.Notifyer.SvcIntervalSet(self.NotificationInterval)

    def Reset(self):
        self.MsgEx.Reset()
        self.TempSensor.SamplesDelete()
        self.MoistSensor.SamplesDelete()
        self.LightSensor.SamplesDelete()
        self.NetCon.StationSettingsReset()

    def Run(self):
        self.Scheduler.Run()

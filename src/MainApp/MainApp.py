
# upyiot modules
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.SystemTime.SystemTime import SystemTime
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.system.Service.ServiceScheduler import Service
from upyiot.system.Util import ResetReason
from upyiot.system.Util import DeviceId
from upyiot.system.Util.Version import Version
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

# LoRaSensor modules
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

    VER_MAJOR = const(0)
    VER_MINOR = const(1)
    VER_PATCH = const(0)

    DummySamples = [20, 30, 25, 11, -10, 40, 32]

    DIR = "/"
    ID = str(ubinascii.hexlify(machine.unique_id()).decode('utf-8'))
    RETRIES = 1
    FILTER_DEPTH = const(1)
    DEEPSLEEP_THRESHOLD_SEC = const(5)

    SamplesPerMessage   = const(1)

    # Service intervals in seconds.
    MsgExInterval           = const(15)
    SensorReadInterval      = const(15)
    Lora = None
    PowerMngr = None

    # TTN

    TtnAppEui = [0x70, 0xB3, 0xD5, 0x7E, 0xD0, 0x03, 0x2C, 0xDC]

    # OTAA Test node 01
    TtnDevEui = [0x00, 0x09, 0xF8, 0x76, 0x3D, 0x22, 0x4F, 0xD5]
    TtnAppKey = [0xA9, 0x03, 0xC9, 0x5F, 0xEF, 0x14, 0x9F, 0x7C,
                 0xCA, 0xB9, 0x06, 0xAC, 0x74, 0x11, 0x5E, 0xA8]

    # ABP Test node 01
    DevAddr = [0x26, 0x01, 0x16, 0x76]
    NwkSKey  = [0x69, 0xBD, 0x0C, 0x69, 0x7A, 0x2C, 0xCE, 0xB4,
               0x26, 0x12, 0xFC, 0xB7, 0x3D, 0x54, 0x3A, 0xE6]
    AppSKey = [0xC2, 0x4E, 0x3D, 0xB0, 0x86, 0x5D, 0x29, 0x09,
               0xB5, 0xBD, 0x43, 0x26, 0x43, 0x4C, 0x6E, 0x5B]


    TtnLoraConfig = {
        "freq"  : 868.1,
        "sf"    : 7,
        "ldro"  : 0,
        "app_eui" : TtnAppEui,
        "dev_eui" : TtnDevEui,
        "app_key" : TtnAppKey
    }

    # KPN
    KpnAppEui = [0x00, 0x59, 0xAC, 0x00, 0x00, 0x01, 0x09, 0xCB]

    # Node 01
    # kpn_deveui = [0x00, 0x59, 0xAC, 0x00, 0x00, 0x1B, 0x06, 0x16]
    # kpn_appeui = [0x00, 0x59, 0xAC, 0x00, 0x00, 0x01, 0x09, 0xCB]
    # kpn_appkey = [0x20, 0x45, 0xa7, 0x01, 0xbc, 0x6f, 0x90, 0x66,
    # 0x8d, 0x73, 0x07, 0xe3, 0x19, 0x84, 0xf7, 0x1f]

    # Node 02
    KpnDevEui = [0x00, 0x59, 0xAC, 0x00, 0x00, 0x1B, 0x07, 0xDB]
    KpnAppKey = [0xc4, 0x91, 0xbc, 0xe0, 0xd9, 0x21, 0x84, 0x63,
                 0x9a, 0x57, 0x63, 0xac, 0x87, 0x6b, 0xe4, 0x05]

    # Node 03
    # KpnDevEui = [0x00, 0x59, 0xAC, 0x00, 0x00, 0x1B, 0x06, 0xD4]
    # KpnAppKey = [0xe5, 0x14, 0x54, 0x06, 0x19, 0x64, 0xfa, 0x3a,
    #              0x28, 0xe6, 0xdd, 0xcb, 0x74, 0xec, 0xcb, 0xf2]

    KpnLoraConfig = {
        "freq"  : 868.1,
        "sf"    : 12,
        "ldro"  : 1,
        "app_eui" : KpnAppEui,
        "dev_eui" : KpnDevEui,
        "app_key" : KpnAppKey
    }

    def __init__(self):
        return

    def Setup(self):
        # Configure the ExtLogging class.
        ExtLogging.ConfigGlobal(level=ExtLogging.DEBUG, stream=None, dir="",
                                file_prefix="log_", line_limit=1000, file_limit=10)

        StructFile.InitLogger(ExtLogging.Create("StructFile"))

        self.Log = ExtLogging.Create("Main")

        self.Log.info("Device ID: {}".format(DeviceId.DeviceId()))

        Version("", self.VER_MAJOR, self.VER_MINOR, self.VER_PATCH)

        rst_reason = ResetReason.ResetReason()
        self.Log.debug("Reset reason: {}".format(ResetReason.ResetReasonToString(rst_reason)))

        # Create driver instances.
        self.DummySensorDriver = DummySensor(self.DummySamples)

        self.InternalTemp = InternalTemp()

        self.LoraProtocol = LoraProtocol(self.KpnLoraConfig, dir="/")
        # self.LoraProtocol.Params.StoreSession(self.DevAddr, self.AppSKey, self.NwkSKey)


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
        # self.MsgEx.SvcDependencies({self.DummySensor: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_RUN,
        #                             self.TempSensor: Service.DEP_TYPE_RUN_ALWAYS_BEFORE_RUN})
        self.MsgEx.SvcDependencies({})
        self.DummySensor.SvcDependencies({})
        self.TempSensor.SvcDependencies({})

        # Register all services to the scheduler.
        self.Scheduler.ServiceRegister(self.MsgEx)
        # self.Scheduler.ServiceRegister(self.DummySensor)
        # self.Scheduler.ServiceRegister(self.TempSensor)

        self.Parser = CborParser()
        Message.SetParser(self.Parser)

        MessageTemplate.SectionsSet(MetadataSchema.MSG_SECTION_META,
                                    MetadataSchema.MSG_SECTION_DATA)
        MessageTemplate.MetadataTemplateSet(MetadataSchema.Metadata,
                                            MetadataSchema.MetadataFuncs)

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
        # self.MoistObserver = self.ReportFmt.CreateObserver(SensorReport.DATA_KEY_MOIST, self.SamplesPerMessage)
        # self.BatteryObserver = self.ReportFmt.CreateObserver(SensorReport.DATA_KEY_BAT, self.SamplesPerMessage)
        # self.TempObserver = self.ReportFmt.CreateObserver(SensorReport.DATA_KEY_TEMP, self.SamplesPerMessage)

        # Link the observers to the sensors.
        # self.DummySensor.ObserverAttachNewSample(self.MoistObserver)
        # self.TempSensor.ObserverAttachNewSample(self.TempObserver)

        self.Scheduler.DeepSleep.RegisterCallbackBeforeDeepSleep(MainApp.BeforeSleep)

        # Set intervals for all services.
        self.MsgEx.SvcIntervalSet(self.MsgExInterval)
        # self.DummySensor.SvcIntervalSet(self.SensorReadInterval)
        # self.TempSensor.SvcIntervalSet(self.SensorReadInterval)

        # self.BatteryObserver.Update(100)

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
    def BeforeSleep():
        ExtLogging.Stop()
        while True:
            # MainApp.PowerMngr.Sleep(1000 * 300) # 86400 3590
            for i in range(0, 10):
                utime.sleep(30)
            machine.reset()



# upyiot modules
from upyiot.system.ExtLogging import ExtLogging
from upyiot.system.Service.ServiceScheduler import ServiceScheduler
from upyiot.system.Util import ResetReason
from upyiot.system.Util import DeviceId
from upyiot.system.Util.Version import Version
from upyiot.comm.Messaging.Message import Message
from upyiot.comm.Messaging.MessageTemplate import MessageTemplate
from upyiot.comm.Messaging.MessageExchange import MessageExchange
from upyiot.comm.Messaging.MessageFormatter import MessageFormatter
from upyiot.comm.Messaging.Protocol.LoraProtocol import LoraProtocol
from upyiot.comm.Messaging.Parser.CborParser import CborParser
from upyiot.middleware.Sensor import Sensor
from upyiot.middleware.StructFile import StructFile
from upyiot.drivers.Sensors.DummySensor import DummySensor
from upyiot.drivers.Sensors.InternalTemp import InternalTemp
from upyiot.drivers.Sensors.Mcp9700Temp import Mcp9700Temp
from upyiot.drivers.Sensors.Voltage import VoltageSensor
from upyiot.drivers.Sleep.DeepSleepBase import DeepSleepBase
from upyiot.drivers.Board.Supply import Supply

# LoRaSensor modules
from Schemas.SensorReport import MoistureSensorReport, \
    BatterySensorReport, TemperatureSensorReport
from Schemas.RegistrationInfo import RegistrationInfo
from Schemas import Metadata
from Config.Hardware import Pins
from MainApp.PowerManager import PowerManager
from .Registration import Registration

# micropython modules
from micropython import const
import machine
import utime
import uos


class NoSleep(DeepSleepBase):

    def DeepSleep(self, msec):
        print("[NoSleep] Idle for {}".format(msec))
        utime.sleep(int(msec/1000))
        machine.reset()

    def DeepSleepForever(self):
        while True:
            utime.sleep(10)


class MainApp:

    VER_MAJOR = const(0)
    VER_MINOR = const(2)
    VER_PATCH = const(0)

    DummySamples = [20, 30, 25, 11, -10, 40, 32]

    DIR_LOG     = const(0)
    DIR_LORA    = const(1)
    DIR_SENSOR  = const(2)
    DIR_MSG     = const(3)
    DIR_SYS     = const(4)
    DIR_TREE = {
        DIR_LOG: "/log",
        DIR_LORA: "/lora",
        DIR_SENSOR: "/sensor",
        DIR_MSG: "/msg",
        DIR_SYS: "/sys"
    }
    DIR_ROOT = "/"
    RETRIES = 1
    FILTER_DEPTH = const(5)
    DEEPSLEEP_THRESHOLD_SEC = const(5)
    SEND_LIMIT = const(1)

    SamplesPerMessage   = const(1)

    # Service intervals in seconds.
    MsgExInterval           = const(100)
    SensorReadInterval      = const(50)
    MoistReadInterval       = const(20)

    # TTN
    TtnAppEui = [0x70, 0xB3, 0xD5, 0x7E, 0xD0, 0x03, 0x2C, 0xDC]

    # OTAA Test node 01
    # TtnDevEui = [0x00, 0x3C, 0x8D, 0xB2, 0x88, 0x2D, 0xC4, 0x7C]
    # TtnAppKey = [0x38, 0x34, 0xF5, 0x1F, 0x04, 0xD0, 0x66, 0xF5,
    #              0xF8, 0x5B, 0x5F, 0xDD, 0xAD, 0x4F, 0xC0, 0xB9]

    # OTAA Test node 02
    # TtnDevEui = [0x00, 0x2B, 0xE3, 0x70, 0x72, 0xA5, 0x9E, 0xF0]
    # TtnAppKey = [0xD3, 0x07, 0xCF, 0xEC, 0x3E, 0x4B, 0x1D, 0xF4,
    #              0xE8, 0x70, 0xA7, 0x44, 0xED, 0x26, 0x8C, 0xF1]

    # OTAA Test node 03
    TtnDevEui = [0x00, 0x68, 0xE0, 0x3A, 0xB9, 0xF3, 0x5E, 0x7C]
    TtnAppKey = [0x37, 0xA2, 0x75, 0x26, 0x3C, 0xE8, 0xD6, 0x47,
                 0x2F, 0x3E, 0xCF, 0xF2, 0x08, 0x47, 0x27, 0x34]


    # ABP Test node 01
    DevAddr = [0x26, 0x01, 0x37, 0x47]
    NwkSKey = [0x13, 0x48, 0xA0, 0x44, 0x47, 0xC4, 0x3B, 0xC8,
               0x70, 0x9B, 0x2F, 0x5B, 0x5B, 0xAA, 0xE5, 0x7A]
    AppSKey = [0x5D, 0x5A, 0x38, 0x50, 0x41, 0xD9, 0xD5, 0x0B,
               0x14, 0x1D, 0xC5, 0x9A, 0xB4, 0xED, 0xFB, 0x59]


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
    KpnDevEui = [0x00, 0x59, 0xAC, 0x00, 0x00, 0x1B, 0x08, 0x08]
    KpnAppKey = [0x08, 0x9a, 0x03, 0x5f, 0xbe, 0xda, 0xad, 0x6c,
                 0x96, 0x72, 0xb5, 0x32, 0xb4, 0x11, 0x14, 0xf4]

    # Node 02
    # KpnDevEui = [0x00, 0x59, 0xAC, 0x00, 0x00, 0x1B, 0x07, 0xDB]
    # KpnAppKey = [0xc4, 0x91, 0xbc, 0xe0, 0xd9, 0x21, 0x84, 0x63,
    #              0x9a, 0x57, 0x63, 0xac, 0x87, 0x6b, 0xe4, 0x05]

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

    KPN = const(0)
    TTN = const(1)
    ABP = const(0)
    OTAA = const(1)

    NETWORK = TTN
    NETWORK_REG = OTAA

    def __init__(self):
        return

    def Setup(self):

        for dir in self.DIR_TREE.values():
            try:
                uos.mkdir(dir)
            except OSError:
                print("Cannot create directory '{}'".format(dir))

        # Configure the ExtLogging class.
        ExtLogging.ConfigGlobal(level=ExtLogging.DEBUG, stream=None, dir=self.DIR_TREE[self.DIR_LOG],
                                file_prefix="log_", line_limit=1000, file_limit=10)

        StructFile.SetLogger(ExtLogging.Create("SFile"))

        self.Log = ExtLogging.Create("Main")

        self.Log.info("Device ID: {}".format(DeviceId.DeviceId()))

        Version(self.DIR_TREE[self.DIR_SYS], self.VER_MAJOR, self.VER_MINOR, self.VER_PATCH)

        rst_reason = ResetReason.ResetReason()
        self.Log.debug("Reset reason: {}".format(ResetReason.ResetReasonToString(rst_reason)))

        # Create driver instances.
        self.DummySensorDriver = DummySensor(self.DummySamples)

        self.InternalTemp = InternalTemp()

        # TODO: Enable actual sensor drivers.
        # self.TempSensorDriver = Mcp9700Temp(temp_pin_nr=Pins.CFG_HW_PIN_TEMP,
        #                                     en_supply_obj=Supply(Pins.CFG_HW_PIN_TEMP_EN, 3.3, 300))
        #
        # self.VBatSensorDriver = VoltageSensor(pin_nr=Pins.CFG_HW_PIN_VBAT_LVL,
        #                                       en_supply_obj=Supply(Pins.CFG_HW_PIN_VBAT_LVL_EN, 3.3, 300))

        if self.NETWORK is self.KPN:
            self.LoraProtocol = LoraProtocol(self.KpnLoraConfig, directory=self.DIR_TREE[self.DIR_LORA])
        elif self.NETWORK is self.TTN:
            self.LoraProtocol = LoraProtocol(self.TtnLoraConfig, directory=self.DIR_TREE[self.DIR_LORA])
            if self.NETWORK_REG is self.ABP:
                self.LoraProtocol.Params.StoreSession(self.DevAddr, self.AppSKey, self.NwkSKey)
        else:
            raise Exception("No valid network LoRa selected.")

        self.DummySensor = Sensor.Sensor(self.DIR_TREE[self.DIR_SENSOR],
                                         "Dummy",
                                         self.FILTER_DEPTH,
                                         self.DummySensorDriver,
                                         samples_per_update=3,
                                         dec_round=True,
                                         store_data=True)

        self.TempSensor = Sensor.Sensor(self.DIR_TREE[self.DIR_SENSOR],
                                        "Temp",
                                        self.FILTER_DEPTH,
                                        self.InternalTemp, # TODO: Replace InternalTemp driver with TempSensorDriver
                                        samples_per_update=2,
                                        dec_round=True,
                                        store_data=True)

        # self.BatteryVoltageSensor = Sensor.Sensor(self.DIR_TREE[self.DIR_SENSOR],
        #                                           "BatLvl",
        #                                           self.FILTER_DEPTH,
        #                                           self.VBatSensorDriver,
        #                                           samples_per_update=2,
        #                                           dec_round=False,
        #                                           store_data=True)

        self.MsgEx = MessageExchange(directory=self.DIR_TREE[self.DIR_MSG],
                                     proto_obj=self.LoraProtocol,
                                     send_retries=self.RETRIES,
                                     msg_size_max=self.LoraProtocol.Mtu,
                                     msg_send_limit=self.SEND_LIMIT)

        # Create the registration info spec and Registration service.
        # Link the Registration service to the Message Exchange service. The Message Exchange
        # service will activate the Registration service when it connects to the LoRa network.
        self.RegistrationInfo = RegistrationInfo()
        self.Registration = Registration(self.MsgEx, self.RegistrationInfo)
        self.MsgEx.AttachConnectionStateObserver(self.Registration)

        self.Scheduler = ServiceScheduler(deepsleep_threshold_sec=self.DEEPSLEEP_THRESHOLD_SEC,
                                         # deep_sleep_obj=PowerManager.PowerManager(),
                                          directory=self.DIR_TREE[self.DIR_SYS])

        # Set service dependencies.
        # There are no hard dependencies between the services.

        # Register all services to the scheduler.
        self.Scheduler.ServiceRegister(self.DummySensor)
        self.Scheduler.ServiceRegister(self.TempSensor)
        # self.Scheduler.ServiceRegister(self.BatteryVoltageSensor)
        self.Scheduler.ServiceRegister(self.MsgEx)
        self.Scheduler.ServiceRegister(self.Registration)

        Message.SetParser(CborParser())
        MessageTemplate.SectionsSet(Metadata.MSG_SECTION_META,
                                    Metadata.MSG_SECTION_DATA)
        MessageTemplate.MetadataTemplateSet(Metadata.Metadata,
                                            Metadata.MetadataFuncs)

        # Create message specifications.
        self.MoistReport = MoistureSensorReport()
        self.BatteryReport = BatterySensorReport()
        self.TempReport = TemperatureSensorReport()

        # Create MessageFormatters and couple them with their message specs.
        moist_report_meta = {
            Metadata.MSG_META_TYPE: self.MoistReport.Type,
            Metadata.MSG_META_SUBTYPE: self.MoistReport.Subtype,
        }
        self.MoistFmt = MessageFormatter(self.MsgEx,
                                         MessageFormatter.SEND_ON_CHANGE,
                                         self.MoistReport,
                                         moist_report_meta)

        battery_report_meta = {
            Metadata.MSG_META_TYPE: self.BatteryReport.Type,
            Metadata.MSG_META_SUBTYPE: self.BatteryReport.Subtype,
        }
        self.BatteryFmt = MessageFormatter(self.MsgEx,
                                         MessageFormatter.SEND_ON_CHANGE,
                                         self.BatteryReport,
                                         battery_report_meta)

        temp_report_meta = {
            Metadata.MSG_META_TYPE: self.TempReport.Type,
            Metadata.MSG_META_SUBTYPE: self.TempReport.Subtype,
        }
        self.TempFmt = MessageFormatter(self.MsgEx,
                                         MessageFormatter.SEND_ON_CHANGE,
                                         self.TempReport,
                                         temp_report_meta)

        # Register message specs for exchange.
        self.MsgEx.RegisterMessageType(self.MoistReport)
        self.MsgEx.RegisterMessageType(self.BatteryReport)
        self.MsgEx.RegisterMessageType(self.TempReport)
        self.MsgEx.RegisterMessageType(self.RegistrationInfo)

        # Create observers for the sensor data.
        self.MoistObserver = self.MoistFmt.CreateObserver(MoistureSensorReport.DATA_KEY_MEASUREMENTS)
        self.BatteryObserver = self.BatteryFmt.CreateObserver(BatterySensorReport.DATA_KEY_MEASUREMENTS)
        self.TempObserver = self.TempFmt.CreateObserver(TemperatureSensorReport.DATA_KEY_MEASUREMENTS)

        # Link the observers to the sensors.
        self.DummySensor.ObserverAttachNewSample(self.MoistObserver)
        self.TempSensor.ObserverAttachNewSample(self.TempObserver)

        self.Scheduler.RegisterCallbackBeforeDeepSleep(MainApp.BeforeSleep)

        # Set intervals for all services.
        self.MsgEx.SvcIntervalSet(self.MsgExInterval)
        self.MsgEx.DefaultIntervalSet(self.MsgExInterval)
        self.DummySensor.SvcIntervalSet(self.MoistReadInterval)
        self.TempSensor.SvcIntervalSet(self.SensorReadInterval)

        # Activate the Message Exchange to attempt to connect to the LoRa network
        # if no LoRaWAN session exists yet.
        if self.LoraProtocol.HasSession() is False:
            self.MsgEx.SvcActivate()

        # self.BatteryObserver.Update(100)

        self.Log.info("Finished initialization.")

    def Reset(self):
        self.MsgEx.Reset()
        self.DummySensor.SamplesDelete()

    def Run(self):
        self.Log.info("Starting scheduler")
        self.Scheduler.Run()

    @staticmethod
    def BeforeSleep():
       ExtLogging.Stop()
       StructFile.ResetLogger()



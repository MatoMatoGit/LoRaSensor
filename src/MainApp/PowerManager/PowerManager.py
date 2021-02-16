from upyiot.drivers.Sleep.DeepSleepBase import DeepSleepExceptionFailed
from upyiot.drivers.Sleep.DeepSleepBase import DeepSleepBase
from MainApp.PowerManager import Protocol
from micropython import const
import utime


class PowerManager(DeepSleepBase):

    SLEEP_RETRY_MAX         = const(5)
    SLEEP_RETRY_DELAY_SEC   = const(10)

    def __init__(self):
        self.Protocol = Protocol.Protocol(2400)
        return

    def DeepSleep(self, msec):
        self._RetrySleep(int(msec / 1000))

    def DeepSleepForever(self):
        self._RetrySleep(65000)

    def Status(self):
        return

    def _RetrySleep(self, sec):
        for i in range(0, self.SLEEP_RETRY_MAX):
            self.Protocol.SendCommand(Protocol.PWR_CMD_SLEEP, sec)
            utime.sleep(self.SLEEP_RETRY_DELAY_SEC)
        raise DeepSleepExceptionFailed

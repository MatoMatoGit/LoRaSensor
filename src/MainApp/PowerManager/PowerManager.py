from MainApp.PowerManager import Protocol


class PowerManager:

    def __init__(self):
        self.Protocol = Protocol.Protocol(2400)
        return

    def Sleep(self, msec):
        self.Protocol.SendCommand(Protocol.PWR_CMD_SLEEP, int(msec / 1000))
        return

    def Status(self):
        return

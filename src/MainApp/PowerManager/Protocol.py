from machine import UART
from micropython import const


PWR_CMD_SLEEP = const(0)
PWR_CMD_STATUS = const(1)


class ProtocolCommand:

    def __init__(self, command):
        self.Command = command
        return

    def Build(self, *args):
        raise NotImplementedError


class CommandSleep(ProtocolCommand):

    CMD_LENGTH = const(5)
    CMD_ARG_SLEEP_TIME = const(0)
    CMD_CODE = const(97)

    def __init__(self):
        super().__init__(self.CMD_CODE)

    def Build(self, *args):
        sleep_time_sec = args[CommandSleep.CMD_ARG_SLEEP_TIME][0]
        message = bytearray(CommandSleep.CMD_LENGTH)
        message[0] = self.Command & 0xFF
        message[1] = (sleep_time_sec >> 24) & 0xFF
        message[2] = (sleep_time_sec >> 16) & 0xFF
        message[3] = (sleep_time_sec >> 8) & 0xFF
        message[4] = sleep_time_sec & 0xFF
        print(message)

        return message


class Protocol:

    def __init__(self, baudrate):
        self.Uart = UART(2, baudrate)
        self.Commands = dict()
        self.Commands[PWR_CMD_SLEEP] = CommandSleep()
        return

    def SendCommand(self, command, *args):
        if command in self.Commands.keys():
            sent = self.Uart.write(self.Commands[command].Build(args))
            print("Sent {} bytes to PowerMngr.".format(sent))
        return

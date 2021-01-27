import sys
import pyperclip

byte_string = sys.argv[1]
try:
    byte_cnt = int(sys.argv[2])
except:
    byte_cnt = 0

print(byte_string)

prefix = "0x"
suffix = ", "

i = 0

list_output = "["

while True:

    try:
        pair = byte_string[i:i+2]
        if pair is "":
            break
        if i > 0:
            list_output += suffix
            if byte_cnt > 0:
                if (i / 2) % byte_cnt == 0:
                    list_output += "\n"

        byte_output = "{}{}".format(prefix, pair)
        list_output += byte_output
        i += 2
    except:
        break




list_output += "]"
print(list_output)
pyperclip.copy(list_output)

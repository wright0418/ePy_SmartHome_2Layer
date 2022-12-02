from machine import UART
from utime import sleep as delay
import _thread


class MeshDevice:

    def __init__(self, uart):

        self.ble = uart
        self.ROLE = ''
        self.readBuf = []
        _thread.start_new_thread(self.uartRead, ())
        self._initMeshDevice()

    def uartRead(self):
        while True:
            msg = str(self.ble.readline(), 'utf-8')

            if msg != '':
                if len(self.readBuf) > 10:
                    dum = self.readBuf.pop(0)
                self.readBuf.append(msg)
                #print('readBuf=', self.readBuf)
            delay(0.02)

    def uartWriteCmd(self, atcmd, timeout=0.3):
        self.ble.read(self.ble.any())
        self.readBuf.clear()
        self.ble.write(atcmd+'\r\n')
        delay(timeout)
        if self.readBuf:
            response = self.readBuf.pop(0).strip()
            if 'SUCCESS' in response:
                return (response)

    def _initMeshDevice(self):
        msg = self.uartWriteCmd('AT+MRG')
        if msg:
            self.ROLE = msg.split(' ')[2]

    def SendData(self, data):
        if len(data) > 20:
            data = data[0:20]
        cmd = 'AT+MDTS 0 0x'
        for char in data:
            cmd = cmd+'{:02x}'.format(ord(char))
        msg = self.uartWriteCmd(cmd, timeout=0.5)
        self.readBuf.clear()

    def RecvData(self):
        if self.readBuf:
            msg = self.readBuf.pop(0).strip().split(' ')
            # print(msg)
            if (msg[0] == 'MDTS-MSG' or msg[0] == 'MDTGP-MSG') and len(msg) > 3:
                data = ''
                # print(msg[3])
                for idx in range(0, len(msg[3]), 2):
                    data = data + chr(int(msg[3][idx:idx+2], 16))
                # print(data)
                return (msg[1], data)


'''
uart = UART(0, 115200, timeout=20)
mesh = MeshDevice(uart)
mesh.SendData('{"T":10,"H":22}')

while True:
    recd = mesh.RecvData()
    if recd:
        print(recd[0],recd[1])
    delay(1)
'''

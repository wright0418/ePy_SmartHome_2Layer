"""
RL62M is UART AT command module ,baudrate = 115200
It can be set to PERIPHERAL(Server / Device ) mode.
also , It can be set to CENTRAL mode( Client / Master ) mode
How to use the Library
from machine import *
import RL62M
uart = UART(1,115200,timeout=200,read_buf_len=512)
BLE = RL62M.GATT(uart,role='PERIPHERAL') or 'CENTRAL'
PERIPHERAL/CENTRAL Mode --
    msg = BLE.RecvData() : recv data and check connect/disconnect status , msg is string type(UTF-8)
    BLE.SendData('ABC')
CENTRAL Mode --
    BLE.ScanConnect() # scan and select the most near device (scan 5sec)
    # don't need scan , use device mac address connect
    BLE.ScanConnect(mac='7002000008B6')
V1.000 = first release version
V1.001
    - fixed mac connect change data mode
V1.002
    - fixed data receve return issues
    - fixed change ROLE check message error
V1.004 (2021.9.27)
    - use utime for delay
    - tested by Raspberry Pi Pico uart0
V1.100 (2022.1.1)
    - 更改廣播接收 資料格式 for Richlink RPi Gateway ，max group 20 , data is 8bit ASCII code  

"""
from utime import sleep_ms as delay
import utime


class GATT:

    def __init__(self, uart, role='PERIPHERAL'):
        self.ROLE = ''
        self.MODE = ''
        self.mac = ''
        self.state = 'DISCONNECTED'
        self.Adv_Interval_ms = 200
        self.AdvState = 0
        self.AdvScanState = 0
        self.AdvData = []
        self.AdvDataHeader = '17FF5D00'
        self.AdvDeviceName = "0609524C36324D"
        self.ScanFilterName = ''
        self.ble = uart
        self._init_RL62M()
        self.ChangeRole(role)
        self.ble.deinit()
        self.ble.init(115200,timeout=20,read_buf_len=128)

    def __del__(self):
        self.ble.deinit()

    ''' init RL62M to Command mode and enable sysmsg'''

    def _init_RL62M(self):
        delay(500)
        msg = ''
        while "OK" not in msg:
            self.ble.write('!CCMD@')
            delay(200)
            self.ble.write('AT\r\n')
            delay(50)
            msg = self.ble.read(self.ble.any())
            if msg == None:
                msg = ''
        self.MODE = 'CMD'
        msg = str(self.WriteCMD_withResp('AT+ADDR=?'), 'utf-8')
        #print (msg)
        self.mac = msg.strip().split(' ')[1]

        msg = self.WriteCMD_withResp('AT+EN_SYSMSG=?')
        if "EN_SYSMSG 0" in msg:
            msg = self.WriteCMD_withResp('AT+EN_SYSMSG=1')

        msg = self.ble.read(self.ble.any())   # Clear all UART Buffer

    def writeCMD_respons(self, atcmd, datamode=True):
        if self.MODE == 'DATA':
            self.ChangeMode('CMD')
        self.ble.write(atcmd+'\r\n')
        delay(50)
        msg = self.ble.read(self.ble.any())
        if msg == None:
            msg = ''
        if 'SYS-MSG: CONNECTED OK' in msg:
            self.state = 'CONNECTED'
        elif 'SYS-MSG: DISCONNECTED OK' in msg:
            self.state = 'DISCONNECTED'
        if datamode == True:
            self.ChangeMode('DATA')
        return(msg)

    def WriteCMD_withResp(self, atcmd, timeout=50):
        self.ChangeMode('CMD')
        self.ble.write(atcmd+'\r\n')
        prvMills = utime.ticks_ms()
        resp = b""
        while (utime.ticks_ms()-prvMills) < timeout:
            if self.ble.any():
                resp = b"".join([resp, self.ble.read(self.ble.any())])
                #print('rep-', atcmd, resp, utime.ticks_ms()-prvMills)
            delay(10)
        return (resp)

    def ChangeMode(self, mode):
        if mode == self.MODE:

            return
        elif mode == 'CMD':
            delay(150)
            self.ble.write('!CCMD@')
            delay(200)
            msg = self.ble.readline()
            if msg == None:
                msg = ''
            while not 'SYS-MSG: CMD_MODE OK' in msg:
                msg = self.ble.readline()
                if msg == None:
                    msg = ''
                delay(50)
            self.MODE = 'CMD'
        elif mode == 'DATA':
            msg = self.WriteCMD_withResp('AT+MODE_DATA')
            while not 'SYS-MSG: DATA_MODE OK' in msg:
                print('change to data mode fail')
                delay(100)
            self.MODE = 'DATA'
        else:
            pass

    def SendData(self, data):
        self.ChangeMode('DATA')
        self.ble.write(data)
        return

    def RecvData(self):
        msg = self.ble.readline()
        if msg == None:
            msg = ''
        if len(msg) > 0:
            if 'SYS-MSG: CONNECTED OK' in msg:
                self.state = 'CONNECTED'
                msg = ''
            elif 'SYS-MSG: DISCONNECTED OK' in msg:
                self.state = 'DISCONNECTED'
                msg = ''
            else:
                return (str(msg, 'utf-8').strip())
        return (str(msg, 'utf-8').strip())
        
    

    def ChangeRole(self, role):
        if self.ROLE == '':
            msg = self.WriteCMD_withResp('AT+ROLE=?')

            if 'PERIPHERAL' in msg:
                self.ROLE = 'PERIPHERAL'
            elif 'CENTRAL' in msg:
                self.ROLE = 'CENTRAL'

        if role == self.ROLE:
            return
        else:

            if role == 'PERIPHERAL':
                # 1.5sec for epy ble v1.03
                msg = self.WriteCMD_withResp('AT+ROLE=P', timeout=1500)

            else:
                msg = self.WriteCMD_withResp(
                    'AT+ROLE=C', timeout=1500)  # 1.5sec for epy ble v1.03
            if 'READY OK' not in msg:
                print('Change Role fail ;', msg)

            self.ROLE = role
            self.ChangeMode('DATA')
            return

    def ScanConnect(self, mac='', name_header='EPY_', filter_rssi=100):
        device = []
        if self.ROLE != 'CENTRAL':
            self.ChangeRole("CENTRAL")
        if mac == '':
            msg = str(self.WriteCMD_withResp(
                'AT+SCAN_FILTER_RSSI={}'.format(filter_rssi)), 'utf-8')
            while len(device) == 0:
                msg = str(self.WriteCMD_withResp(
                    'AT+SCAN', timeout=5000), 'utf-8')
                msg = msg. split('\r\n')
                for dev in msg:
                    sdev = dev.split(' ')
                    if len(sdev) == 5:
                        device.append(sdev)
            sorted(device, key=lambda x: int(x[3]), reverse=True)
            msg = self.WriteCMD_withResp(
                'AT+CONN={}'.format(device[0][0]))
        else:
            msg = self.WriteCMD_withResp(
                'AT+CONN={}'.format(mac))

        for i in range(10):
            msg = self.RecvData()
            if self.state == 'CONNECTED':
                self.ChangeMode('DATA')
                break
            delay(200)
        return

    def disconnect(self):
        msg = self.WriteCMD_withResp('AT+DISC')
        #print ('disconn',msg)
        for i in range(10):
            msg = self.RecvData()
            if self.state == 'DISCONNECTED':
                break
            delay(100)
        return

    def SetAdvInterval_ms(self, time_ms=200):
        # 50/100/200/500/1000/2000/5000/10000/20000/50000
        self.EnableAdvMode(enable=0)

        if time_ms != self.Adv_Interval_ms and self.ROLE == 'PERIPHERAL':
            msg = self.WriteCMD_withResp('AT+ADV_INTERVAL={}'.format(time_ms))
            if "OK" in msg:
                self.Adv_Interval_ms = time_ms
        self.EnableAdvMode(enable=1)
        return

    def EnableAdvMode(self, enable=1):  # enable 廣播功能

        if self.ROLE == 'PERIPHERAL':
            msg = self.WriteCMD_withResp('AT+ADVERT={}'.format(enable))
            if "OK" in msg:
                self.AdvState = enable
        return

    def SetAdvData(self):
        data = self.AdvDataHeader+''.join(self.AdvData)+self.AdvDeviceName
        print(data)
        msg = self.WriteCMD_withResp(
            'AT+AD_SET=0,{}'.format(data))
        return

    def EnableAdvScan(self, enable=1):  # 開啟廣播接收
        if self.AdvScanState != enable and self.ROLE == 'CENTRAL':
            msg = self.WriteCMD_withResp(
                'AT+ADV_DATA_SCAN={}'.format(enable))
            if "OK" in msg:
                self.AdvScanState = enable
    def AdvSendData(self, group=1, data='0'):
        # need modify to new format
        if self.AdvData == []:
            self.AdvData = ['0']*40
        if self.ROLE != 'PERIPHERAL':
            self.ChangeRole("PERIPHERAL")
        if group >= 1 and group <= 20:
            self.AdvData[(group-1)*2] = hex(ord(data))[2]
            self.AdvData[(group-1)*2+1] = hex(ord(data))[3]
        self.EnableAdvMode(enable=0)
        self.SetAdvData()
        self.EnableAdvMode(enable=1)

    def AdvScanFilterName(self, name='rl'):
        if self.ScanFilterName != name:
            msg = self.WriteCMD_withResp('AT+SCAN_FILTER_NAME={}'.format(name))
            if "OK" in msg:
                self.ScanFilterName = name


    def AdvRecvData(self, group=0, who_mac='None'):
        if who_mac == 'None':
            return ('Error')
        str_data = ''
        if self.ROLE != 'CENTRAL':
            self.ChangeRole("CENTRAL")
        self.EnableAdvScan(enable=1)
        self.AdvScanFilterName()
        msg = str(self.ble.readline(), 'utf-8')
        if len(msg) > 0:
            msg = msg.strip()
            msg = str(msg).split(' ')

            # check ADV_DATA and mac address in ADV data
            # 代辦事項 +check header  過濾 name = rl
            # 廣播發送資料格式如下
            # 1709726c  42310000000000000000 00000000000000000000
            if len(msg) <4 :
                return (None)
            if 'ADV_DATA' in msg[0] and who_mac in msg[1]:
                msg = msg[3][8:48]
            else:
                return(None)
            group = int(group)

            if group < 1 or group > 20:
                str_data = ['']*20
                for i in range(20):
                    group_data = msg[i*2:i*2+2]
                    if group_data.isdigit():
                        str_data[i] = chr(int(group_data, 16))
                    else:
                        str_data[i] = '.'
                return ('Error')
            else:
                group_data = msg[(group-1)*2:(group-1)*2+2]
                if group_data.isdigit():
                    str_data = chr(int(group_data, 16))
                else:
                    str_data = '~'
                return (str_data)

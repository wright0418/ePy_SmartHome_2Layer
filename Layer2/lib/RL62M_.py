from machine import UART, LED
import uasyncio as asyncio
import utime

_debug = True


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
        self.recv_data = None
        self.ble = uart
        self.led_status = LED('ledy')
        self.ble.deinit()
        self.ble.init(115200, timeout=20, read_buf_len=128)
        asyncio.run(self._init_RL62M())
        asyncio.run(self.ChangeRole(role))
        asyncio.run(self.RecvData())

    def __del__(self):
        self.ble.deinit()

    ''' init RL62M to Command mode and enable sysmsg'''

    async def _init_RL62M(self):
        await asyncio.sleep_ms(500)
        msg = ''
        while "OK" not in msg:
            self.ble.write('!CCMD@')
            await asyncio.sleep_ms(200)
            self.ble.write('AT\r\n')
            await asyncio.sleep_ms(50)
            msg = self.ble.read(self.ble.any())
            if msg == None:
                msg = ''
        self.MODE = 'CMD'
        msg = str(await self.WriteCMD_withResp('AT+ADDR=?'), 'utf-8')
        if _debug:
            print(msg)
        self.mac = msg.strip().split(' ')[1]

        msg = await self.WriteCMD_withResp('AT+EN_SYSMSG=?')
        if "EN_SYSMSG 0" in msg:
            msg = await self.WriteCMD_withResp('AT+EN_SYSMSG=1')
        msg = self.ble.read(self.ble.any())   # Clear all UART Buffer

    async def WriteCMD_withResp(self, atcmd, timeout=50):
        await self.ChangeMode('CMD')
        msg = self.ble.read(self.ble.any())
        self.ble.write(atcmd+'\r\n')
        prvMills = utime.ticks_ms()
        resp = b""
        while (utime.ticks_ms()-prvMills) < timeout:
            if self.ble.any():
                resp = b"".join([resp, self.ble.read(self.ble.any())])
                if _debug:
                    print('rep-', atcmd, resp, utime.ticks_ms()-prvMills)
            await asyncio.sleep_ms(10)
        return (resp)

    async def ChangeMode(self, mode):
        if mode == self.MODE:
            return
        elif mode == 'CMD':
            await asyncio.sleep_ms(150)
            self.ble.write('!CCMD@')
            await asyncio.sleep_ms(200)
            msg = self.ble.readline()
            if msg == None:
                msg = ''
            while not 'SYS-MSG: CMD_MODE OK' in msg:
                msg = self.ble.readline()
                if msg == None:
                    msg = ''
                await asyncio.sleep_ms(50)
            self.MODE = 'CMD'
        elif mode == 'DATA':
            msg = await self.WriteCMD_withResp('AT+MODE_DATA')
            while not 'SYS-MSG: DATA_MODE OK' in msg:
                if _debug:
                    print('change to data mode fail')
                await asyncio.sleep_ms(100)
            self.MODE = 'DATA'
        else:
            pass

    async def senddata(self, _data):
        await self.ChangeMode('DATA')
        self.ble.write(_data)
        return

    def SendData(self, data):
        self.senddata(data)

    async def RecvData(self):
        while True:
            msg = str(self.ble.readline(), 'utf-8')
            if len(msg) > 0:
                print('msg=', msg)
                if 'SYS-MSG: CONNECTED OK' in msg:
                    self.state = 'CONNECTED'
                elif 'SYS-MSG: DISCONNECTED OK' in msg:
                    self.state = 'DISCONNECED'
                else:
                    self.recv_data = msg
                    print('ssss', msg)
            await asyncio.sleep_ms(20)

    async def ChangeRole(self, role):
        if self.ROLE == '':
            msg = await self.WriteCMD_withResp('AT+ROLE=?')

            if 'PERIPHERAL' in msg:
                self.ROLE = 'PERIPHERAL'
            elif 'CENTRAL' in msg:
                self.ROLE = 'CENTRAL'

        if role == self.ROLE:
            return
        else:

            if role == 'PERIPHERAL':
                # 1.5sec for epy ble v1.03
                msg = await self.WriteCMD_withResp('AT+ROLE=P', timeout=1500)

            else:
                msg = await self.WriteCMD_withResp(
                    'AT+ROLE=C', timeout=1500)  # 1.5sec for epy ble v1.03
            if 'READY OK' not in msg:
                if _debug:
                    print('Change Role fail ;', msg)

            self.ROLE = role
            await self.ChangeMode('DATA')
            return

    async def ScanConn(self, mac_='', name_header_='EPY_', filter_rssi_=40):

        if self.ROLE != 'CENTRAL':
            await self.ChangeRole("CENTRAL")
        if mac_ == '':
            msg = str(await self.WriteCMD_withResp(
                'AT+SCAN_FILTER_RSSI={}'.format(filter_rssi_)), 'utf-8')
            device = []
            while len(device) == 0:
                msg = str(await self.WriteCMD_withResp(
                    'AT+SCAN', timeout=5000), 'utf-8')
                if _debug:
                    print('scaned--> device ', msg)
                msg = msg. split('\r\n')
                for dev in msg:
                    sdev = dev.split(' ')
                    if len(sdev) == 5:
                        device.append(sdev)
            sorted(device, key=lambda x: int(x[3]), reverse=False)
            if _debug:
                print('sorted device', device)
            msg = await self.WriteCMD_withResp(
                'AT+CONN={}'.format(device[0][0]))
        else:
            msg = await self.WriteCMD_withResp(
                'AT+CONN={}'.format(mac_))
        if _debug:
            print('connected to Server ', msg)
        for i in range(10):
            msg = self.RecvData()
            if self.state == 'CONNECTED':
                await self.ChangeMode('DATA')
                break
            await asyncio.sleep_ms(200)
        return 'OK'

    async def disconnect(self):
        msg = await self.WriteCMD_withResp('AT+DISC')
        if _debug:
            print('disconn', msg)
        for i in range(10):
            msg = self.RecvData()
            if self.state == 'DISCONNECTED':
                break
            await asyncio.sleep_ms(100)
        return

    async def SetAdvInterval_ms(self, time_ms=200):
        # 50/100/200/500/1000/2000/5000/10000/20000/50000
        await self.EnableAdvMode(enable=0)

        if time_ms != self.Adv_Interval_ms and self.ROLE == 'PERIPHERAL':
            msg = await self.WriteCMD_withResp('AT+ADV_INTERVAL={}'.format(time_ms))
            if "OK" in msg:
                self.Adv_Interval_ms = time_ms
        await self.EnableAdvMode(enable=1)
        return

    async def EnableAdvMode(self, enable=1):  # enable 廣播功能

        if self.ROLE == 'PERIPHERAL':
            msg = await self.WriteCMD_withResp('AT+ADVERT={}'.format(enable))
            if "OK" in msg:
                self.AdvState = enable
        return

    async def SetAdvData(self):
        data = self.AdvDataHeader+''.join(self.AdvData)+self.AdvDeviceName
        print(data)
        msg = await self.WriteCMD_withResp(
            'AT+AD_SET=0,{}'.format(data))
        return

    async def EnableAdvScan(self, enable=1):  # 開啟廣播接收
        if self.AdvScanState != enable and self.ROLE == 'CENTRAL':
            msg = await self.WriteCMD_withResp(
                'AT+ADV_DATA_SCAN={}'.format(enable))
            if "OK" in msg:
                self.AdvScanState = enable

    async def AdvSendData(self, group=1, data='0'):
        # need modify to new format
        if self.AdvData == []:
            self.AdvData = ['0']*40
        if self.ROLE != 'PERIPHERAL':
            await self.ChangeRole("PERIPHERAL")
        if group >= 1 and group <= 20:
            self.AdvData[(group-1)*2] = hex(ord(data))[2]
            self.AdvData[(group-1)*2+1] = hex(ord(data))[3]
        await self.EnableAdvMode(enable=0)
        await self.SetAdvData()
        await self.EnableAdvMode(enable=1)

    async def AdvScanFilterName(self, name='rl'):
        if self.ScanFilterName != name:
            msg = await self.WriteCMD_withResp('AT+SCAN_FILTER_NAME={}'.format(name))
            if "OK" in msg:
                self.ScanFilterName = name

    async def AdvRecvData(self, group=0, who_mac='None'):
        if who_mac == 'None':
            return ('Error')
        str_data = ''
        if self.ROLE != 'CENTRAL':
            await self.ChangeRole("CENTRAL")
        await self.EnableAdvScan(enable=1)
        await self.AdvScanFilterName()
        msg = str(self.ble.readline(), 'utf-8')
        if len(msg) > 0:
            msg = msg.strip()
            msg = str(msg).split(' ')

            # check ADV_DATA and mac address in ADV data
            # 代辦事項 +check header  過濾 name = rl
            # 廣播發送資料格式如下
            # 1709726c  42310000000000000000 00000000000000000000
            if len(msg) < 4:
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

    def ScanConnect(self, mac='', filter_rssi=40):
        asyncio.run(self.ScanConn(mac_=mac, filter_rssi_=filter_rssi))

    def DisConnect(self):
        asyncio.run(BLE.disconnect())


if __name__ == '__main__':

    ble_port = UART(1, 115200)
    BLE = GATT(ble_port)

    '''for server mode '''

    while True:
        print('dddd')
        print(BLE.recv_data)
        BLE.recv_data = None
        utime.sleep(0.1)

    '''for Client mode '''

    # BLE.ScanConn(mac='70090000026F')
    BLE.ScanConnect(filter_rssi=40)
    print('connected')
    utime.sleep(3)
    for i in range(10):
        BLE.SendData('AAA\n')
        print('send AAAA')
    BLE.DisConnect()
    print('dis-connected')

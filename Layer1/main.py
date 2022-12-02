from machine import LED, ADC, UART, Pin, Switch, Timer
import epyBuzzerMusic as buzzer
import utime as time
from machine import PWM
from tp229bf import Keypad
import uasyncio as asyncio
import uheapq as heapq
import RL62M
import gc

_debug = False

sys_module = "L1"
FW_ver = "2.0.1"
event_q = []
rgbled = LED(LED.RGB)
ledy = LED('ledy')
ledr = LED('ledr')
rgbled.lightness(100)
m1 = PWM(Pin.epy.PWM2, freq=10000, duty=0)
m2 = PWM(Pin.epy.PWM3, freq=10000, duty=0)


class SmartHome():
    def __init__(self):
        self.password = '1234'
        self.in_door_key = False
        self.in_button1_key = False
        self.in_button2_key = False
        self.in_keypad_data = ''
        self.in_light_ctrl_value = 0
        self.in_light_sensor = 0
        self.in_mic_sensor_value = 0
        self.in_gas_sensor_value = 0
        self.key_in = []
        self.mode = 'board'
        self.inited_state = False

        self.light_state = 'OFF'
        self.mic_state = 'OFF'
        self.pwd_light_mode = False
        self.door_light_mode = False
        self.pwd_curtain_mode = False
        self.pwd_door_mode = 'Alarm'
        self.door_key = Pin(Pin.epy.P6, Pin.IN)  # Active "H"
        self.button1_key = Pin(Pin.epy.P8, Pin.IN)
        self.button2_key = Pin(Pin.epy.AIN4, Pin.IN)
        self.light_ctrl = ADC(Pin.epy.AIN0)
        self.light_sensor = ADC(Pin.epy.AIN1)
        self.mic_sensor = ADC(Pin.epy.AIN2)
        self.gas_sensor = ADC(Pin.epy.AIN3)
        scl = Pin(Pin.epy.P15, Pin.OUT)
        sdo = Pin(Pin.epy.P14, Pin.IN)
        self.keypad = Keypad(scl=scl, sdo=sdo, inputs=16, multi=True)

        ble1 = UART(1, 115200, timeout=20, read_buf_len=64)
        self.BLE = RL62M.GATT(ble1)

    async def read_all_sensor(self):
        while True:
            self.in_door_key = True if self.door_key.value() else False
            self.in_button1_key = True if not self.button1_key.value() else False
            self.in_button2_key = True if not self.button2_key.value() else False
            self.in_light_ctrl_value = self.light_ctrl.read()
            self.in_light_sensor = self.light_sensor.read()
            self.in_mic_sensor_value = self.mic_sensor.read()
            self.in_gas_sensor_value = self.gas_sensor.read()
            await asyncio.sleep_ms(200)

    async def read_keypad(self):
        global event_q
        while True:
            key = self.keypad.read_one_key()
            if key:
                if key != '#':
                    heapq.heappush(event_q, 'KeyTone')

                    self.key_in.append(key)
                    if len(self.key_in) == 5:
                        d = self.key_in.pop(0)
                else:
                    key_input = ''.join(self.key_in)
                    if len(self.key_in) < 4 or key_input != self.password:
                        heapq.heappush(event_q, 'KeyError')

                    elif key_input == self.password:
                        heapq.heappush(event_q, 'KeyPass')

            await asyncio.sleep_ms(100)

    async def process_task(self):
        global event_q
        while True:
            if self.in_door_key:
                heapq.heappush(event_q, 'Door')

            if self.mode != 'Phone1':
                if self.in_button1_key:
                    if self.light_state == 'OFF':
                        LV = self.in_light_ctrl_value
                        led_data = [[LV >> 3, LV >> 3, LV >> 3]]*12
                        rgbled.rgb_write(led_data)
                        self.light_state = 'ON'
                    else:
                        rgbled.off()
                        self.light_state = 'OFF'
                    #self.in_button1_key = False

                if self.light_state == 'OFF':
                    if self.in_light_sensor <= 500:
                        led_data = [[255, 255, 255 >> 3]]*12
                        rgbled.rgb_write(led_data)
                    elif self.in_light_sensor > 2000:
                        rgbled.off()
                else:  # light ON ,used VR control Light
                    LV = self.in_light_ctrl_value >> 3
                    led_data = [[LV, LV, LV]]*12
                    rgbled.rgb_write(led_data)
                if self.in_button2_key:
                    if self.mic_state == 'OFF':
                        self.mic_state = 'ON'
                        ledy.on()
                    else:
                        self.mic_state = 'OFF'
                        ledy.off()
                    #self.in_button2_key = False

                if self.mic_state == 'ON':
                    pass
                    # if self.in_mic_sensor_value >= 3000:
                    #     heapq.heappush(event_q, 'MIC')
                    # if self.in_gas_sensor_value > 500:
                    #     heapq.heappush(event_q, 'GAS')
            ledr.toggle()
            await asyncio.sleep_ms(100)

    async def action_task(self):
        global event_q
        # play my home song satrt
        music.play(['C4:2', 'D', 'E:6', 'F:2', 'F:4', 'G', 'G',
                   'R', 'E', 'G', 'F:6', 'E:2', 'F:4', 'D', 'E'])
        await asyncio.sleep(8)
        # gc.collect()

        while True:
            if event_q:
                if _debug:
                    print('event_len=', len(event_q))
                item = heapq.heappop(event_q)
                if _debug:
                    print('item=', item)

                if item == 'KeyTone':
                    music.play(['C7:2'], loop=False)

                elif item == 'KeyPass':
                    music.play(['C5', 'D', 'E', 'F', 'G'], loop=False)

                    if self.pwd_light_mode:
                        led_data = [[255, 255, 255]]*12
                        rgbled.rgb_write(led_data)
                    else:
                        rgbled.off()
                    if self.pwd_curtain_mode:
                        await self.Motor_Ctrl('ON')
                    else:
                        await self.Motor_Ctrl('OFF')
                        await asyncio.sleep(1)

                elif item == 'KeyError':
                    music.play(['C2:4', 'C2:4'], loop=False)
                    await asyncio.sleep(1.5)
                elif item == 'Door':
                    music.play(['C4:2', 'C7:8', 'C4:2', 'C7:8'], loop=False)

                    # for times in range(2):
                    #     await music.playFreq(400, 200)
                    #     await music.playFreq(2000, 500)
                    if _debug:
                        print('Door_Light')
                    if self.door_light_mode:
                        led_data = [[255, 255, 255]]*12
                        rgbled.rgb_write(led_data)
                        await asyncio.sleep(2)
                        rgbled.off()
                    else:
                        await asyncio.sleep(2)

                if self.mode == 'board':
                    pass
                    # if item == 'MIC':
                    #     music.play(['A', 'B', 'C'], loop=False)
                    #     await asyncio.sleep(2)
                    # elif item == 'GAS':
                    #     music.play(['C', 'D', 'A', 'E'], loop=False)
                    #     await asyncio.sleep(2)
                    # elif not self.door_light_mode:
                    #     rgbled.off()
                else:  # phone action
                    pass
            if len(event_q) >= 4:
                event_q.clear()

            await asyncio.sleep_ms(200)

    async def Motor_Ctrl(self, state):
        if state == "OFF":
            m1.duty(90)
            m2.duty(0)
        elif state == "ON":
            m1.duty(0)
            m2.duty(90)
        await asyncio.sleep(0.5)
        m1.duty(0)
        m2.duty(0)

    async def L3sec(self):
        led_data = [[255, 255, 255 >> 3]]*12
        rgbled.rgb_write(led_data)
        await asyncio.sleep(3)
        rgbled.off()

    async def BLE_task(self):
        global event_q, music
        while True:
            BLEData = self.BLE.RecvData()

            if self.BLE.state == 'CONNECTED' and self.mode == 'board':
                self.mode = 'Phone'
            elif self.BLE.state == 'DISCONNECTED':
                self.mode = 'board'

            if self.mode == 'Phone':
                if BLEData != '':
                    if _debug:
                        print('ble_data=', BLEData)
                    else:
                        await asyncio.sleep_ms(50)
                    if BLEData == 'GetBoard':
                        send = "Board,{},\n".format(sys_module)
                        if _debug:
                            print('send_data=', send)
                        else:
                            await asyncio.sleep_ms(50)
                        self.BLE.SendData(send)
                        await asyncio.sleep_ms(100)
                        self.mode = 'Phone1'
                    else:
                        pass
                        if _debug:
                            print('BLEData != GetBoard -->', BLEData)
            elif self.mode == 'Phone1':
                if BLEData != '':
                    if _debug:
                        print("BLE_recv_data==", BLEData)
                    data = BLEData.split(',')
                    if len(data) > 1 and data[0] == 'M':
                        dele_data = data.pop(0)
                    print('data==', data)  # for test
                    for BLEData in data:
                        if _debug:
                            print('cmd =', BLEData)
                        if BLEData == "LON":
                            led_data = [[255, 255, 255 >> 3]]*12
                            rgbled.rgb_write(led_data)
                        elif BLEData == "LOFF":
                            rgbled.off()
                        elif BLEData == "COFF":
                            await self.Motor_Ctrl('OFF')
                        elif BLEData == "CON":
                            await self.Motor_Ctrl('ON')
                        elif BLEData == "recover":
                            self.password = '1234'
                        elif BLEData == "ring":
                            heapq.heappush(event_q, 'Door')

                        elif BLEData == "SetDoor":
                            self.door_light_mode = True
                        elif BLEData == "ClrDoor":
                            self.door_light_mode = False

                        elif "L3sec" in BLEData:
                            await self.L3sec()
                        elif BLEData == "Set_PWD_L":
                            self.pwd_light_mode = True
                        elif BLEData == "Clr_PWD_L":
                            self.pwd_light_mode = False
                        elif BLEData == "Set_PWD_C":
                            self.pwd_curtain_mode = True
                        elif BLEData == "Clr_PWD_C":
                            self.pwd_curtain_mode = False

                        elif BLEData == 'GetBoard':
                            send = "Board,{},\n".format(sys_module)
                            if _debug:
                                print('send_data=', send)
                            else:
                                await asyncio.sleep_ms(50)
                            self.BLE.SendData(send)
                            await asyncio.sleep_ms(50)
                        elif BLEData == 'DisConnect':
                            self.BLE.disconnect()
                            await asyncio.sleep_ms(50)

                        elif BLEData[0] == "@":
                            self.password = BLEData[1:]

                send = "Air,{},\n".format(self.in_gas_sensor_value)
                self.BLE.SendData(send)
                await asyncio.sleep_ms(10)
                send = "Mic,{},\n".format(self.in_mic_sensor_value)
                self.BLE.SendData(send)
                await asyncio.sleep_ms(10)
                send = "Light,{},\n".format(self.in_light_sensor)
                self.BLE.SendData(send)
                # await asyncio.sleep_ms(100)
                # send = "VR,{},\n".format(self.in_light_ctrl_value)
                # self.BLE.SendData(send)
            if music.getState() == 'STOP':
                gc.collect()
            # print('free_mem=', gc.mem_free())
            await asyncio.sleep_ms(10)


timer = Timer(0)
music = buzzer.Music(timer)
sh = SmartHome()
loop = asyncio.get_event_loop()
loop.create_task(sh.read_all_sensor())
loop.create_task(sh.read_keypad())
loop.create_task(sh.action_task())
loop.create_task(sh.process_task())
loop.create_task(sh.BLE_task())
loop.create_task(music.play_music())
loop.run_forever()

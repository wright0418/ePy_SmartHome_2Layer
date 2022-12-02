from ePy4Digit import FourDigit
from machine import I2C, Pin, PWM, LED, UART
from htu21d import HTU21D
import utime as time
import RL62M
import gc
# import epyBuzzerMusic as buzzer
from machine import PWM
import uasyncio as asyncio
import uheapq as heapq

_debug = False

sys_module = "L2"
FW_ver = "1.0.0"
event_q = []

rgbled = LED(LED.RGB)
rgbled.lightness(100)
ledy = LED('ledy')
coolor_dict = {'Red': (255, 0, 0), 'Blue': (0, 0, 255), 'Green': (0, 0, 255)}


class Motor:
    def __init__(slef, pinA, pinB):
        slef.pwma = PWM(pinA, freq=10000, duty=0)
        slef.pwmb = PWM(pinB, freq=10000, duty=0)

    def CC(slef, speed):
        slef.pwma.duty(speed)
        slef.pwmb.duty(0)

    def CW(slef, speed):
        slef.pwma.duty(0)
        slef.pwmb.duty(speed)

    def Stop(slef):
        slef.pwma.duty(0)
        slef.pwmb.duty(0)


class SmartHome2F:
    def __init__(self):
        self.in_IR_detector = False
        self.in_temper = 0
        self.in_humi = 0
        self.motor_outside_speed = 0
        self.motor_inside_speed = 0
        self.level_up = 27
        self.level_down = 26
        self.mode = 'board'

        self.detecter_pin = Pin(Pin.epy.P6, Pin.IN)
        self.detecter_pin.irq(
            handler=self.IR_cb, trigger=self.detecter_pin.IRQ_FALLING | self.detecter_pin.IRQ_RISING)
        self.inside_fan = Motor(Pin.epy.PWM0, Pin.epy.PWM1)
        self.outside_fan = Motor(Pin.epy.PWM2, Pin.epy.PWM3)

        i2c1 = I2C(1, I2C.MASTER, baudrate=100000)
        self.four_digi = FourDigit(i2c1)
        i2c0 = I2C(0, I2C.MASTER, baudrate=100000)
        self.sensor = HTU21D(i2c0)
        ble1 = UART(1, 115200, timeout=20, read_buf_len=64)
        self.BLE = RL62M.GATT(ble1)

    def IR_cb(self, pin):
        if self.mode == 'board':
            if self.detecter_pin.value():
                heapq.heappush(event_q, 'IR_Event')
            else:
                heapq.heappush(event_q, 'IR_Cancel')

    async def read_all_sensor(self):
        while True:
            self.in_temper = self.sensor.readTemperatureData()
            self.in_humi = self.sensor.readHumidityData()
            self.four_digi.show_temper(self.in_temper)
            await asyncio.sleep_ms(500)

    async def L3sec(self):
        led_data = [[255, 255, 255 >> 3]]*12
        rgbled.rgb_write(led_data)
        await asyncio.sleep(3)
        rgbled.off()

    async def M1_3sec(self):
        self.inside_fan.CC(80)
        await asyncio.sleep(3)
        self.inside_fan.CC(0)

    async def process_task(self):
        global event_q, Color
        while True:
            if event_q:
                item = heapq.heappop(event_q)
                if _debug:
                    print(item)
                if self.mode == 'board':
                    if item == 'IR_Event':
                        color1 = [[coolor_dict['Red'][0], coolor_dict['Red']
                                   [1], coolor_dict['Red'][2]]] * 10
                        rgbled.rgb_write(color1)
                    if item == 'IR_Cancel':
                        rgbled.off()

                    if self.in_temper >= self.level_up:
                        self.inside_fan.CC(80)
                        self.outside_fan.CW(100)

                    if self.in_temper <= self.level_down:
                        self.inside_fan.CC(0)
                        self.outside_fan.CW(0)
                elif self.mode == 'Phone1':
                    if item == 'L3sec':
                        await self.L3sec()
                    elif item == 'M1_3sec':
                        await self.M1_3sec()
            if len(event_q) >= 4:
                event_q.clear()
            ledy.toggle()
            await asyncio.sleep_ms(500)

    async def BLE_task(self):
        global event_q
        while True:
            gc.collect()
            # if _debug:
            #     print(gc.mem_free())

            BLEData = self.BLE.RecvData()

            if self.BLE.state == 'CONNECTED' and self.mode == 'board':
                self.mode = 'Phone'
            elif self.BLE.state == 'DISCONNECTED':
                self.mode = 'board'

            if self.mode == 'Phone':
                if BLEData != '':
                    if _debug:
                        print(BLEData)
                    if BLEData == 'GetBoard':
                        send = "Board,{},\n".format(sys_module)
                        if _debug:
                            print(send)
                        await asyncio.sleep_ms(100)
                        self.BLE.SendData(send)
                        await asyncio.sleep_ms(50)
                        self.mode = 'Phone1'
            elif self.mode == 'Phone1':
                if BLEData != '':
                    if _debug:
                        print(BLEData)
                    else:
                        # print(BLEData)
                        pass
                        # await asyncio.sleep_ms(50)
                    if BLEData == "LON":
                        color1 = [
                            [coolor_dict['Green'][0], coolor_dict['Green'][1], coolor_dict['Green'][2]]] * 10
                        rgbled.rgb_write(color1)
                    elif BLEData == "LOFF":
                        rgbled.off()
                    elif BLEData == "M2OFF":
                        self.outside_fan.CW(0)
                    elif BLEData == "M2ON":
                        self.outside_fan.CW(100)
                    elif BLEData == "M1OFF":
                        self.inside_fan.CC(0)
                    elif BLEData == "M1ON":
                        self.inside_fan.CC(80)
                    elif BLEData == "L3sec":
                        heapq.heappush(event_q, 'L3sec')
                    elif BLEData == "M1_3sec":
                        heapq.heappush(event_q, 'M1_3sec')
                    elif BLEData == 'GetBoard':
                        send = "Board,{},\n".format(sys_module)
                        if _debug:
                            print(send)
                        self.BLE.SendData(send)
                        await asyncio.sleep_ms(50)
                    elif BLEData == 'DisConnect':
                        self.BLE.disconnect()

                send = "TEMP,{},\n".format(self.in_temper)
                if _debug:
                    print(send)
                self.BLE.SendData(send)
                await asyncio.sleep_ms(50)
                send = "HUMI,{},\n".format(self.in_humi)
                # if _debug:
                #     print(send)
                self.BLE.SendData(send)
                await asyncio.sleep_ms(50)
                send = "Det,{},\n".format(self.detecter_pin.value())
                # if _debug:
                #     print(send)
                self.BLE.SendData(send)
                await asyncio.sleep_ms(50)
            await asyncio.sleep_ms(10)


sh = SmartHome2F()
loop = asyncio.get_event_loop()
loop.create_task(sh.read_all_sensor())
loop.create_task(sh.process_task())
loop.create_task(sh.BLE_task())
loop.run_forever()

import utime


class Keypad:

    def __init__(self, scl, sdo, inputs=8, multi=False, raw=False):
        self._scl_pin = scl
        self._sdo_pin = sdo
        self._inputs = inputs
        self._multi_mode = multi
        self._raw_mode = raw
        self.pressed = False
        self.key_table = {0: "1", 1: '2', 2: "3", 3: 'A', 4: "4", 5: '5', 6: "6",
                          7: 'B', 8: '7', 9: '8', 10: '9', 11: 'C', 12: '*', 13: '0', 14: '#', 15: 'D'}
        self.pre_key = -1

    def read(self):
        key = [1] * self._inputs
        self._scl_pin.on()
        utime.sleep_ms(1)
        for i in range(self._inputs):
            self._scl_pin.off()
            utime.sleep_ms(1)
            key[i] = self._sdo_pin.value()
            self._scl_pin.on()
            utime.sleep_ms(1)
        utime.sleep_ms(1)
        if self._raw_mode:
            return tuple(key)
        else:
            if self._multi_mode:
                key_multi = []
                for i in range(self._inputs):
                    if key[i] == 0:
                        key_multi.append(i)
                return tuple(key_multi)
            else:
                key_single = -1
                for i in range(self._inputs):
                    if key[i] == 0:
                        key_single = i
                        break
                return key_single

    def read_one_key(self):
        key = self.read()
        if key:  # check pressed
            if self.pressed:
                if self.pre_key != key[0]:
                    self.pre_key = key[0]
                    return self.key_table[key[0]]
                else:
                    return None
            else:
                self.pre_key = key[0]
                self.pressed = True
                return self.key_table[key[0]]
        else:
            self.pressed = False


if __name__ == '__main__':
    from machine import Pin, LED

    # used I2C1 on ePy Lite
    scl = Pin(Pin.epy.P15, Pin.OUT)
    sdo = Pin(Pin.epy.P14, Pin.IN)
    # matrix keypad
    keypad = Keypad(scl=scl, sdo=sdo, inputs=16, multi=True)

    password = '3095'
    key_in = ''
    ledy = LED('ledy')
    ledr = LED('ledr')
    ledy.off()
    ledr.off()

    while True:
        key = keypad.read_one_key()
        while not key == '#':  # end of input key
            if key:
                key_in += key
                if key_in.isdigit():
                    print('key_in=', key_in)
            key = keypad.read_one_key()
        print('key =', key)
        if len(key_in) >= 4:
            aaa = key_in[len(key_in)-4:len(key_in)]
            if aaa == password:
                print("Pass")
                for i in range(4):
                    ledy.toggle()
                    utime.sleep(0.3)

            else:
                print("PWD Error")
                for i in range(4):
                    ledr.toggle()
                    utime.sleep(0.3)
        key_in = ''

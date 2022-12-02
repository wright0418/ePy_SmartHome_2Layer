import math


class FourDigit():
    def __init__(self, i2c_port):
        self._Seg7Addr = 0x3D
        self.i2c = i2c_port

    def i2c_write(self, write_data):
        try:
            self.i2c.send(bytearray(write_data), self._Seg7Addr)
        except OSError:
            # print('I2C_Error')
            self.i2c.init()

    def show4number(self, number):
        number = int(number)
        if 0 <= number <= 9999:
            self.i2c_write([0x03, 1, number//1000])
            self.i2c_write([0x03, 2, (number % 1000)//100])
            self.i2c_write([0x03, 3, (number % 100) // 10])
            self.i2c_write([0x03, 4, number % 10])
            self.i2c_write([0x04, 0])

    def show_temper(self, temper):
        tempe = int(temper * 10)

        if 0 <= tempe < 1000:
            self.i2c_write([0x03, 1, tempe//100])

            self.i2c_write([0x03, 2, ((tempe % 100) // 10) | 0x80])
            self.i2c_write([0x03, 3, tempe % 10])
            self.i2c_write([0x03, 4, 0x0C])
            self.i2c_write([0x04, 0])

    def show_time(self, hr, min):
        self.i2c_write([0x02, hr, min])
        self.i2c_write([0x04, 1])


if __name__ == '__main__':
    from machine import I2C
    i2c1 = I2C(1, I2C.MASTER, baudrate=100000)
    four_digi = FourDigit(i2c1)
    four_digi.show4number(1999)
    four_digi.show_temper(24.1)
    four_digi.show_time(24, 59)

from machine import Pin, Timer
import utime
import math
import uasyncio as asyncio


class Music:
    def __init__(self, tim, pin=Pin.epy.P9):
        self.tone_idx = {'R': 0, 'A': 0, 'Ab': -1, 'G#': -1, 'G': -2, 'Gb': -3, 'F#': -3, 'F': -4, 'E': -5,
                         'Eb': -6, 'D#': -6, 'D': -7, 'Db': -8, 'C#': -8, 'C': -9, 'B': 2, 'Bb': 1, 'A#': 1}
        self._freqA4 = 440  # Hz
        self._buzzer_pin = Pin(pin, Pin.OUT)
        self._timer = tim
        self._timer.init(freq=self._freqA4*2)
        self.ticks = 4
        self.bpm = 120
        self._lv = 4
        self._ticks = (60000/((self.bpm)*self.ticks))
        self._state = 'STOP'
        self.loop = False
        self.music = []

    async def play_music(self):
        while True:
            if self._state == "START":
                for play_tone in self.music:
                    if self._state == "STOP":
                        break
                    play_tone = play_tone.split(":")
                    try:
                        tone_ = None
                        if play_tone[0][0] != 'R':
                            tone_ = play_tone[0][0:2] if len(
                                play_tone[0]) == 3 else play_tone[0][0:1]
                            if play_tone[0][-1].isdigit():
                                self._lv = int(play_tone[0][-1])
                            playFreq = self._freqA4 * \
                                math.pow(1.059463, (4-self._lv) * -
                                         12+self.tone_idx[tone_])
                        else:
                            playFreq = 0
                        if(len(play_tone) == 2):
                            self._ticks = (60000/((self.bpm)*self.ticks)
                                           )*(int(play_tone[1]))
                        await self._playFreq(playFreq, int(self._ticks))
                    except KeyError:
                        #print("tone not find")
                        self._state = "STOP"
                        self.music = []
                if not self.loop or self._state == "STOP":
                    self._state = "STOP"
                    self.music = []
            else:
                self._state = "STOP"
                self.music = []
            await asyncio.sleep_ms(10)

    def tempo(self, ticks=4, bpm=120):
        self.ticks = ticks
        self.bpm = bpm

    def _buzzer_toggle(self, t):
        self._buzzer_pin.value(~self._buzzer_pin.value() & 0x0001)

    def stop(self):
        self._state = "STOP"
        self.music = []

    def getState(self):
        return self._state

    def play(self, music, loop=False):
        while self._state == "START":
            self.stop()
        self.music = music
        self.loop = loop
        self._state = "START"

    async def playFreq(self, playFreq, playtime_ms):
        if self._state == 'STOP':
            self._state = 'START'
            await self._playFreq(playFreq, playtime_ms)
            self._state = 'STOP'

    async def _playFreq(self, playFreq, playtime_ms):
        self._timer.init(freq=int(playFreq*2))
        self._timer.callback(self._buzzer_toggle)
        await asyncio.sleep_ms(playtime_ms)
        self._timer.callback(None)

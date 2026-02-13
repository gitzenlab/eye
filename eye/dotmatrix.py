from micropython import const
from framebuf import FrameBuffer, MONO_HLSB


_DIGIT_0 = const(0x1)
_DECODE_MODE = const(0x9)
_NO_DECODE = const(0x0)
_INTENSITY = const(0xa)
_INTENSITY_INIT = const(0x0)
_SCAN_LIMIT = const(0xb)
_DISPLAY_FULL_SCREEN = const(0x7)
_DISPLAY_TEST_MODE = const(0xf)
_DISPLAY_TEST_NORMAL = const(0x0)
_SHUTDOWN = const(0xc)
_SHUTDOWN_MODE = const(0x0)
_NORMAL_OPERATION = const(0x1)


class dotmatrix(FrameBuffer):
    def __init__(self, spi, cs, num, format=MONO_HLSB):
        self._spi = spi
        self._cs = cs
        self._cs.init(self._cs.OUT, True)
        self._num = num
        self._buffer = bytearray(8 * self._num)
        super().__init__(self._buffer, 8 * self._num, 8, format)
        self._screen_init()

    def _screen_write(self, command, data):
        self._cs(0)
        for _ in range(self._num):
            self._spi.write(bytearray([command, data]))
        self._cs(1)

    def _screen_init(self):
        for command, data in (
            (_SHUTDOWN, _SHUTDOWN_MODE),
            (_DISPLAY_TEST_MODE, _DISPLAY_TEST_NORMAL),
            (_SCAN_LIMIT, _DISPLAY_FULL_SCREEN),
            (_INTENSITY, _INTENSITY_INIT),
            (_DECODE_MODE, _NO_DECODE),
            (_SHUTDOWN, _NORMAL_OPERATION),
        ):
            self._screen_write(command, data)

    def brightness(self, value):
        if not 0 <= value <= 15:
            raise ValueError("Brightness out of range")
        self._screen_write(_INTENSITY, value)

    def text(self, s, x=0, y=0, c=1):
        super().text(s, x, y, c)

    def matrix(self, s, glyphs, x_offset=0, y_offset=0):
        col = 0
        for char in s:
            glyph = glyphs.get(char)

            if glyph:
                for y in range(8):
                    for x in range(8):
                        self.pixel(x+col+x_offset, y+y_offset, glyph[y][x])
            else:
                self.text(char, col+x_offset, y_offset)

            col += 8

    def show(self):
        for y in range(8):
            self._cs(0)
            for m in range(self._num):
                self._spi.write(bytearray([_DIGIT_0 + y, self._buffer[(y * self._num) + m]]))
            self._cs(1)

    def clear(self):
        self.fill(0)

    def shutdown(self):
        self._screen_write(_SHUTDOWN, _SHUTDOWN_MODE)

    def wakeup(self):
        self._screen_write(_SHUTDOWN, _NORMAL_OPERATION)

    def test(self, enable=True):
        self._screen_write(_DISPLAY_TEST_MODE, int(enable))

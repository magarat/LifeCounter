from machine import Pin, SPI, PWM
import framebuf
import time
import os

# Page numbers listed apply to the datasheet PDF available here:
#   https://www.mouser.com/datasheet/2/744/ST7789V2-3314280.pdf

# Values in supplier's example were wrong, possibly for endian reasons?
RED = 0x00f8  # (was 0x07E0)
GREEN = 0xe007  # (was 0x001f)
BLUE = 0x1f00  # (was 0xf800)

CYAN = BLUE | GREEN
MAGENTA = RED | BLUE
YELLOW = RED | GREEN

WHITE = RED | GREEN | BLUE


class LCD(framebuf.FrameBuffer):
    def __init__(self, resetPin, backlightPin, csPin, dcPin, spiCLK, spiMOSI, width=280, height=240):
        self.width = width
        self.height = height

        self.cs = Pin(csPin, Pin.OUT)
        self.rst = Pin(resetPin, Pin.OUT)

        self.cs(1)
        self.spi = SPI(0, 100_000_000, polarity=0, phase=0, sck=Pin(spiCLK), mosi=Pin(spiMOSI), miso=None)
        self.dc = Pin(dcPin, Pin.OUT)
        self.dc(1)

        self.backlight = PWM(Pin(backlightPin))
        self.backlight.freq(1000)
        self.backlight.duty_u16(24000)  # max 65535

        # 2 bytes per pixel
        self.buffer = bytearray(height * width * 2)
        super().__init__(self.buffer, width, height, framebuf.RGB565)
        self.init_display()

    def brightness(self, brightness):
        ''' Sets the brightness of the backlight (via PWM) in the range 0..65535
            Args:
                brightness: the desired brightness in the range from 0 (off) to 65535 (fully on)
        '''
        self.backlight.duty_u16(brightness)  # max 65535

    def send_cmd(self, cmd, data=None):
        ''' Sends the given command and any associated data
            Args:
                cmd: the command code to send
                data: any parameters for the command (defaults to None)
        '''
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytes([cmd]))
        if data is not None:
            self.dc(1)
            self.spi.write(bytes(data))
        self.cs(1)

    def init_display(self):
        """Initialize display"""
        self.rst(1)
        self.rst(0)
        self.rst(1)

        # Memory data access control (p.217)
        self.send_cmd(0x36, [0x70])

        # Interface pixel format (p.226)
        self.send_cmd(0x3a, [0x55])  # 16-bit per pixel, 65k pallette

        # Porch setting (p.265)
        self.send_cmd(0xb2, [0x0c, 0x0c, 0x00, 0x33, 0x33])

        # Gate control (p.269)
        self.send_cmd(0xb7, [0x35])

        # LCM Control (p.278)
        self.send_cmd(0xc0, [0x2c])

        # VDV and VRH Command Enable (p.280)
        self.send_cmd(0xc2, [0x01])

        # VRH set (p.281)
        self.send_cmd(0xc3, [0x13])

        # VDV set (p.283)
        self.send_cmd(0xc4, [0x20])

        # Frame rate control in normal mode (p.287)
        self.send_cmd(0xc6, [0x0f])

        # Power Control 1 (p.293)
        self.send_cmd(0xd0, [0xa4, 0xa1])

        # Positive voltage gamma control (p.297)
        self.send_cmd(0xe0, [
            0xf0, 0x00, 0x04, 0x04,
            0x05, 0x29, 0x33, 0x3e,
            0x38, 0x12, 0x12, 0x28,
            0x30
        ])

        # Negative voltage gamma control (p.299)
        self.send_cmd(0xe1, [
            0xF0, 0x07, 0x0A, 0x0D,
            0x0B, 0x07, 0x28, 0x33,
            0x3E, 0x36, 0x14, 0x14,
            0x29, 0x23
        ])

        # Display inversion on (p.192)
        self.send_cmd(0x21)

        # Sleep Out (p.186)
        self.send_cmd(0x11)

        # Display on (p.198)
        self.send_cmd(0x29)

    def show(self):
        # The 1.69" 280x240 module seems to have 20 "invisible" columns
        # down the left side, so we must allow for that when stating where
        # we want to transfer our frame buffer to.
        first_column = 20

        # Column address set (p.200)
        self.send_cmd(0x2a, [
            0x00,
            first_column,
            (self.width + first_column - 1) >> 8,
            (self.width + first_column - 1) & 0xff
        ])

        # Row address set (p.202)
        self.send_cmd(0x2b, [
            0x00,
            0x00,
            (self.height - 1) >> 8,
            (self.height - 1) & 0xff
        ])

        # Memory write (p.204)
        self.send_cmd(0x2C)

        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

    def write_text(self, text, x, y, size, color):
        ''' Method to write Text on OLED/LCD Displays
            with a variable font size
            Args:
                text: the string of chars to be displayed
                x: x co-ordinate of starting position
                y: y co-ordinate of starting position
                size: font size of text, as an integer multiple of the standard size
                color: color of text to be displayed
        '''
        background = self.pixel(x, y)
        info = []
        # Creating reference characters to read their values
        self.text(text, x, y, color)
        for i in range(x, x + (8 * len(text))):
            for j in range(y, y + 8):
                # Fetching amd saving details of pixels, such as
                # x co-ordinate, y co-ordinate, and color of the pixel
                px_color = self.pixel(i, j)
                info.append((i, j, px_color)) if px_color == color else None
        # Clearing the reference characters from the screen
        self.text(text, x, y, background)
        # Writing the custom-sized font characters on screen
        for px_info in info:
            self.fill_rect(size * px_info[0] - (size - 1) * x, size * px_info[1] - (size - 1) * y,
                           size, size, px_info[2])


# if __name__ == '__main__':
#     width = 280
#     height = 240
#     lcd = LCD(resetPin=14, backlightPin=10, csPin=17, dcPin=15, spiCLK=18, spiMOSI=19)
#     lcd.fill(0)
#
#     # 3 primary colourful stripes
#     lcd.fill_rect(190, 0, 10, height, RED)
#     lcd.fill_rect(200, 0, 10, height, GREEN)
#     lcd.fill_rect(210, 0, 10, height, BLUE)
#
#     # 3 secondary colourful stripes
#     lcd.fill_rect(220, 0, 10, height, CYAN)
#     lcd.fill_rect(230, 0, 10, height, MAGENTA)
#     lcd.fill_rect(240, 0, 10, height, YELLOW)
#
#     # Text in increasing sizes
#     for (size, colour) in [(1, RED), (2, GREEN), (3, BLUE),
#                            (4, CYAN), (5, MAGENTA), (6, YELLOW)]:
#         lcd.write_text("Pico!!!", 20, 20 + 8 * size * size >> 1, size, colour)
#
#     lcd.show()
#
# # Save alongside your 2.py, then `import Pico-LCD` from your `2.py`
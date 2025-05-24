import Pico_LCD
from machine import Pin, Timer
import time


# LCD setup
width = 280
height = 240
lcd = Pico_LCD.LCD(resetPin=14, backlightPin=10, csPin=17, dcPin=15, spiCLK=18, spiMOSI=19)

# Button pins
sw3 = Pin(2, Pin.IN, Pin.PULL_UP)
sw1 = Pin(3, Pin.IN, Pin.PULL_UP)
sw2 = Pin(4, Pin.IN, Pin.PULL_UP)

# Rotary encoder pins
clk = Pin(0, Pin.IN, Pin.PULL_UP)  # A (CLK)
dt = Pin(1, Pin.IN, Pin.PULL_UP)   # B (DT)

# Colors
RED = 0x00f8
GREEN = 0xe007
BLUE = 0x1f00
GOLD = 0xFEA0
WHITE = RED | GREEN | BLUE

# State variables
life = 20
poison = 0
energy = 0
experience = 0
increment = 0
delta = 1
button0_down = False
button1_down = False
button2_down = False
mode = 0
reset_pressed_time = None
both_pressed_time = None

# Encoder interrupt state
encoder_direction = 0
encoder_changed = False
encoder_last_time = 0
encoder_debounce_ms = 20

# Encoder ISR
def encoder_handler(pin):
    global encoder_direction, encoder_changed, encoder_last_time
    now = time.ticks_ms()
    if time.ticks_diff(now, encoder_last_time) > encoder_debounce_ms:
        if dt.value() != clk.value():
            encoder_direction = -1
        else:
            encoder_direction = 1
        encoder_changed = True
        encoder_last_time = now

# Attach encoder interrupt
clk.irq(trigger=Pin.IRQ_FALLING, handler=encoder_handler)

def update_display(label, value, color):
    lcd.fill(0)
    text_str = str(value)
    scale = 16 if len(text_str) == 1 else 256 // (len(text_str) * 8)
    text_width = len(text_str) * 8 * scale
    text_h = scale * 8
    avail_h = height - 48
    x = (width - text_width) // 2
    y = 48 + ((avail_h - text_h) // 2)
    lcd.write_text(label, 15, 15, 3, color)
    lcd.fill_rect(0, 43, 280, 2, color)
    lcd.write_text(text_str, x, y, scale, color)
    lcd.show()

update_display("LIFE", life, WHITE)

while True:
    # Debounce increment selector button
    if not sw3.value() and not button2_down:
        increment += 1
        if increment > 4:
            increment = 0
        button2_down = True
    elif sw3.value() and button2_down:
        button2_down = False

    # Set delta from increment setting
    delta = [1, 2, 5, 10, 100][increment]

    # Handle encoder updates
    if encoder_changed:
        if mode == 0:
            life += delta * encoder_direction
        elif mode == 1:
            poison += delta * encoder_direction
        elif mode == 2:
            energy += delta * encoder_direction
        elif mode == 3:
            experience += delta * encoder_direction
        encoder_changed = False

    # Optional: short sleep to reduce flicker/sensitivity
    time.sleep_ms(4)

    # Handle simultaneous press (sw2 + sw3) to reset current value
    if not sw2.value() and not sw3.value():
        if reset_pressed_time is None:
            reset_pressed_time = time.ticks_ms()
        elif time.ticks_diff(time.ticks_ms(), reset_pressed_time) > 1000:
            if mode == 0:
                life = 20
            elif mode == 1:
                poison = 0
            elif mode == 2:
                energy = 0
            elif mode == 3:
                experience = 0
    else:
        reset_pressed_time = None

    # Check for simultaneous hold (sw1 + sw2) to set life to infinity
    if not sw1.value() and not sw2.value():
        if both_pressed_time is None:
            both_pressed_time = time.ticks_ms()
        elif time.ticks_diff(time.ticks_ms(), both_pressed_time) > 1000:
            life = float('inf')
            mode = 0  # Switch to LIFE view
    else:
        both_pressed_time = None

    # Button 1 = cycle through modes
    if not sw1.value() and not button0_down:
        mode += 1
        if mode > 3:
            mode = 0
        increment = 0
        button0_down = True
    elif sw1.value() and button0_down:
        button0_down = False

    # Button 2 = reset to LIFE mode (only if sw3 is not pressed)
    if not sw2.value() and not button1_down:
        if sw3.value():
            mode = 0
            increment = 0
        button1_down = True
    elif sw2.value() and button1_down:
        button1_down = False

    # Update display
    if mode == 0:
        if life == float('inf'):
            update_display("LIFE", "INF", Pico_LCD.YELLOW)
        else:
            update_display("LIFE", life, WHITE)
    elif mode == 1:
        update_display("POISON", poison, GREEN)
    elif mode == 2:
        update_display("ENERGY", energy, BLUE)
    elif mode == 3:
        update_display("EXPERIENCE", experience, RED)

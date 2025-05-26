import Pico_LCD
from machine import Pin, Timer
from rotary_irq_rp2 import RotaryIRQ
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
encoder = RotaryIRQ(pin_num_clk=0,
                    pin_num_dt=1,
                    min_val=0,
                    max_val=100,
                    incr=1,
                    reverse=False,
                    range_mode=RotaryIRQ.RANGE_UNBOUNDED,
                    pull_up=True,
                    half_step=False,
                    invert=False)

# Colors
RED = 0x00f8
GREEN = 0xe007
BLUE = 0x1f00
GOLD = 0xFEA0
WHITE = RED | GREEN | BLUE

# State variables
val_old = encoder.value()

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
previous_value = True

def update_display(label, value, color):
    lcd.fill(0) #paint over our old picture
    text_str = str(value) #the name of what we are tracking
    scale = 16 if len(text_str) == 1 else 256 // (len(text_str) * 8)
    text_width = len(text_str) * 8 * scale
    text_h = scale * 8
    avail_h = height - 48
    x = (width - text_width) // 2 #centers our text horizontally
    y = 48 + ((avail_h - text_h) // 2) #centers our text vertically
    lcd.write_text(label, 15, 15, 3, color) #displays the name of what we are tracking
    lcd.fill_rect(0, 43, 280, 2, color) #dividing bar
    lcd.write_text(text_str, x, y, scale, color) #displays the value of what we are tracking
    lcd.show()

#initialize the display so there is something there on boot
update_display("LIFE", life, WHITE)

while True:
    # Selects increment
    if not sw3.value() and not button2_down:
        increment += 1
        if increment > 4:
            increment = 0
        button2_down = True
    # Debounce for the button
    elif sw3.value() and button2_down:
        button2_down = False

    # Set delta from increment setting
    delta = [1, 2, 5, 10, 100][increment]
    val_new = encoder.value()

    if val_old != val_new:
        if val_new > val_old:
            print("RIGHT")
            if mode == 0:
                life += delta
            elif mode == 1:
                poison += delta
            elif mode == 2:
                energy += delta
            elif mode == 3:
                experience += delta
        elif val_new < val_old:
            print("LEFT")
            if mode == 0:
                life -= delta
            elif mode == 1:
                poison -= delta
            elif mode == 2:
                energy -= delta
            elif mode == 3:
                experience -= delta
        val_old = val_new
    time.sleep_ms(100)


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

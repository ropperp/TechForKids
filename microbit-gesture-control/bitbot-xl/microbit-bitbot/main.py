"""
micro:bit auf dem BitBot XL (Motorsteuerung per Funk)
========================================================

Läuft auf dem micro:bit, der auf dem BitBot XL steckt (batteriebetrieben,
kein USB-Kabel während der Fahrt). Empfängt die Funk-Kommandos vom
Sender-micro:bit (siehe ../microbit-sender/main.py) und steuert damit
Motoren, LEDs und den Lautsprecher an.

Ein Kommando hat das Format "<Modus>,<linkes Rad>,<rechtes Rad>", z.B.
"L,150,600" (Kurve links, linkes Rad 150, rechtes Rad 600) oder
"B,-400,-400" (rückwärts). Negative Werte bedeuten rückwärts. Modus ist
nur für Anzeige/LEDs/Ton relevant (S=Stopp, B=Rückwärts, V=Vorwärts,
L=Kurve links, R=Kurve rechts) - die eigentliche Fahrbewegung kommt
komplett aus den beiden Radgeschwindigkeiten, die gesture_reader.py
berechnet (dort auch die Geschwindigkeiten einstellbar).

WICHTIG: RADIO_GROUP muss exakt mit microbit-sender/main.py
übereinstimmen, sonst kommen keine Kommandos an!

Motor-Pins für das BitBot-XL-Modell (aus dem offiziellen 4tronix
MakeCode-Paket https://github.com/4tronix/BitBot entnommen - 4tronix
bietet leider keine fertige MicroPython-Bibliothek an, deshalb steuern
wir die Pins hier direkt an):
    Linker Motor:  vorwärts = P16, rückwärts = P8
    Rechter Motor: vorwärts = P14, rückwärts = P12
Jeder Motor hat also zwei Pins - PWM (0-1023) auf dem einen dreht ihn
in die eine Richtung, auf dem anderen in die Gegenrichtung.

LEDs: 12 RGB-LEDs an P13 (ebenfalls aus dem 4tronix-Quellcode, Standard
WS2812/NeoPixel-Protokoll) - grün bei Vorwärts-/Kurvenfahrt, rot bei
Rückwärtsfahrt, aus bei Stopp.

Sicherheit: Kommt länger als WATCHDOG_MS kein neues Funkkommando an
(z.B. weil der Sender-micro:bit ausgeschaltet oder außer Reichweite
ist), wird automatisch gestoppt, statt einfach weiterzufahren.

Aufspielen z.B. über https://python.microbit.org (Python-Editor) oder Mu.
"""

from microbit import *
import radio
import music
import neopixel

RADIO_GROUP = 1
WATCHDOG_MS = 1000  # Sicherheits-Stopp, wenn so lange kein Kommando ankommt

NUM_LEDS = 12
LED_BRIGHTNESS = 150  # 0-255, voll aufgedreht (255) ist ziemlich grell

radio.config(group=RADIO_GROUP)
radio.on()

left_forward = pin16
left_reverse = pin8
right_forward = pin14
right_reverse = pin12

leds = neopixel.NeoPixel(pin13, NUM_LEDS)

GREEN = (0, LED_BRIGHTNESS, 0)
RED = (LED_BRIGHTNESS, 0, 0)
OFF = (0, 0, 0)


def set_leds(color):
    for i in range(NUM_LEDS):
        leds[i] = color
    leds.show()


def clamp_speed(value):
    return max(-1023, min(1023, value))


def drive_wheel(forward_pin, reverse_pin, speed):
    speed = clamp_speed(speed)
    if speed >= 0:
        forward_pin.write_analog(speed)
        reverse_pin.write_digital(0)
    else:
        forward_pin.write_digital(0)
        reverse_pin.write_analog(-speed)


def drive(left_speed, right_speed):
    drive_wheel(left_forward, left_reverse, left_speed)
    drive_wheel(right_forward, right_reverse, right_speed)


def stop():
    drive(0, 0)


DISPLAY_IMAGES = {
    "S": Image.NO,
    "B": Image.ARROW_S,
    "V": Image.ARROW_N,
    "L": Image.ARROW_W,
    "R": Image.ARROW_E,
}

stop()
set_leds(OFF)
display.show(Image.HAPPY)  # bereit und wartet auf Funksignale

BEEP_INTERVAL_MS = 1000  # beim Rückwärtsfahren alle X ms piepsen

last_mode = None
last_receive_time = running_time()
last_beep_time = running_time()

while True:
    msg = radio.receive()
    if msg:
        parts = msg.split(",")
        if len(parts) == 3 and parts[0] in DISPLAY_IMAGES:
            mode = parts[0]
            try:
                left_speed = int(parts[1])
                right_speed = int(parts[2])
            except ValueError:
                left_speed = right_speed = None

            if left_speed is not None:
                last_receive_time = running_time()
                drive(left_speed, right_speed)

                if mode != last_mode:
                    last_mode = mode
                    display.show(DISPLAY_IMAGES[mode])
                    if mode == "B":
                        set_leds(RED)
                        # Sofort piepsen, danach übernimmt die Wiederholung unten
                        last_beep_time = running_time() - BEEP_INTERVAL_MS
                    elif mode == "S":
                        set_leds(OFF)
                    else:  # V, L, R -> vorwärts unterwegs
                        set_leds(GREEN)

    # Beim Rückwärtsfahren alle BEEP_INTERVAL_MS erneut piepsen
    if last_mode == "B" and running_time() - last_beep_time >= BEEP_INTERVAL_MS:
        last_beep_time = running_time()
        music.pitch(880, 150, pin=pin0, wait=False)

    # Sicherheits-Stopp bei Funkausfall
    if last_mode != "S" and running_time() - last_receive_time > WATCHDOG_MS:
        last_mode = "S"
        stop()
        set_leds(OFF)
        display.show(Image.NO)

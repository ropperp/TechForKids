"""
micro:bit auf dem BitBot XL (Motorsteuerung per Funk)
========================================================

Läuft auf dem micro:bit, der auf dem BitBot XL steckt (batteriebetrieben,
kein USB-Kabel während der Fahrt). Empfängt die Funk-Kommandos vom
Sender-micro:bit (siehe ../microbit-sender/main.py) und steuert damit
die Motoren an.

Ein Kommando hat das Format "<Richtung><4-stellige Geschwindigkeit>",
z.B. "L0150" (links drehen, Geschwindigkeit 150) oder "V0600"
(vorwärts, Geschwindigkeit 600). Die Geschwindigkeit kommt direkt von
gesture_reader.py (dort beim Start abfragbar bzw. proportional zur
Kippung der Hand berechnet) - dieser micro:bit hat also selbst keine
festen Geschwindigkeits-Konstanten mehr.

WICHTIG: RADIO_GROUP muss exakt mit microbit-sender/main.py
übereinstimmen, sonst kommen keine Kommandos an!

Motor-Pins für das BitBot-XL-Modell (aus dem offiziellen 4tronix
MakeCode-Paket https://github.com/4tronix/BitBot entnommen - 4tronix
bietet leider keine fertige MicroPython-Bibliothek an, deshalb steuern
wir die Pins hier direkt an):
    Linker Motor:  vorwärts = P16, rückwärts = P8
    Rechter Motor: vorwärts = P14, rückwärts = P12
Jeder Motor hat also zwei Pins - PWM (0-1023) auf dem einen dreht ihn
in die eine Richtung, auf dem anderen in die Gegenrichtung. Für
"stopp" werden beide Pins auf 0 gesetzt (Motor läuft frei aus).

Sicherheit: Kommt länger als WATCHDOG_MS kein neues Funkkommando an
(z.B. weil der Sender-micro:bit ausgeschaltet oder außer Reichweite
ist), wird automatisch gestoppt, statt einfach weiterzufahren.

Aufspielen z.B. über https://python.microbit.org (Python-Editor) oder Mu.
"""

from microbit import *
import radio

RADIO_GROUP = 1
WATCHDOG_MS = 1000  # Sicherheits-Stopp, wenn so lange kein Kommando ankommt

radio.config(group=RADIO_GROUP)
radio.on()

left_forward = pin16
left_reverse = pin8
right_forward = pin14
right_reverse = pin12


def clamp_speed(speed):
    return max(0, min(1023, speed))


def stop(speed=0):
    left_forward.write_digital(0)
    left_reverse.write_digital(0)
    right_forward.write_digital(0)
    right_reverse.write_digital(0)


def forward(speed):
    speed = clamp_speed(speed)
    left_forward.write_analog(speed)
    left_reverse.write_digital(0)
    right_forward.write_analog(speed)
    right_reverse.write_digital(0)


def reverse(speed):
    speed = clamp_speed(speed)
    left_forward.write_digital(0)
    left_reverse.write_analog(speed)
    right_forward.write_digital(0)
    right_reverse.write_analog(speed)


def spin_left(speed):
    # Lenkrad nach links gekippt -> auf der Stelle nach links drehen
    speed = clamp_speed(speed)
    left_forward.write_digital(0)
    left_reverse.write_analog(speed)
    right_forward.write_analog(speed)
    right_reverse.write_digital(0)


def spin_right(speed):
    speed = clamp_speed(speed)
    left_forward.write_analog(speed)
    left_reverse.write_digital(0)
    right_forward.write_digital(0)
    right_reverse.write_analog(speed)


# Muss zu command_for_gesture() in gesture_reader.py passen!
ACTIONS = {
    "S": stop,
    "B": reverse,
    "V": forward,
    "L": spin_left,
    "R": spin_right,
}

DISPLAY_IMAGES = {
    "S": Image.NO,
    "B": Image.ARROW_S,
    "V": Image.ARROW_N,
    "L": Image.ARROW_W,
    "R": Image.ARROW_E,
}

stop()
display.show(Image.HAPPY)  # bereit und wartet auf Funksignale

last_direction = None
last_receive_time = running_time()

while True:
    msg = radio.receive()
    if msg and len(msg) == 5 and msg[0] in ACTIONS:
        direction = msg[0]
        try:
            speed = int(msg[1:5])
        except ValueError:
            speed = None

        if speed is not None:
            last_receive_time = running_time()
            ACTIONS[direction](speed)
            if direction != last_direction:
                last_direction = direction
                display.show(DISPLAY_IMAGES[direction])

    # Sicherheits-Stopp bei Funkausfall
    if last_direction != "S" and running_time() - last_receive_time > WATCHDOG_MS:
        last_direction = "S"
        stop()
        display.show(Image.NO)

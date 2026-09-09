"""
micro:bit auf dem BitBot XL (Motorsteuerung per Funk)
========================================================

Läuft auf dem micro:bit, der auf dem BitBot XL steckt (batteriebetrieben,
kein USB-Kabel während der Fahrt). Empfängt die Funk-Kommandos vom
Sender-micro:bit (siehe ../microbit-sender/main.py) und steuert damit
die Motoren an.

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
SPEED = 600          # Fahrgeschwindigkeit, 0 (langsam) bis 1023 (schnell)
WATCHDOG_MS = 1000    # Sicherheits-Stopp, wenn so lange kein Kommando ankommt

radio.config(group=RADIO_GROUP)
radio.on()

left_forward = pin16
left_reverse = pin8
right_forward = pin14
right_reverse = pin12


def stop():
    left_forward.write_digital(0)
    left_reverse.write_digital(0)
    right_forward.write_digital(0)
    right_reverse.write_digital(0)


def forward():
    left_forward.write_analog(SPEED)
    left_reverse.write_digital(0)
    right_forward.write_analog(SPEED)
    right_reverse.write_digital(0)


def spin_left():
    # Lenkrad nach links gekippt -> auf der Stelle nach links drehen
    left_forward.write_digital(0)
    left_reverse.write_analog(SPEED)
    right_forward.write_analog(SPEED)
    right_reverse.write_digital(0)


def spin_right():
    left_forward.write_analog(SPEED)
    left_reverse.write_digital(0)
    right_forward.write_digital(0)
    right_reverse.write_analog(SPEED)


# Muss zu GESTURE_TO_COMMAND in gesture_reader.py passen!
COMMANDS = {
    "S": stop,
    "L": spin_left,
    "R": spin_right,
    "V": forward,
}

stop()
display.show(Image.HAPPY)  # bereit und wartet auf Funksignale

last_cmd = None
last_receive_time = running_time()

while True:
    msg = radio.receive()
    if msg in COMMANDS:
        last_receive_time = running_time()
        if msg != last_cmd:
            last_cmd = msg
            COMMANDS[msg]()
            display.show(Image.ARROW_N if msg == "V" else
                         Image.ARROW_W if msg == "L" else
                         Image.ARROW_E if msg == "R" else
                         Image.NO)

    # Sicherheits-Stopp bei Funkausfall
    if last_cmd != "S" and running_time() - last_receive_time > WATCHDOG_MS:
        last_cmd = "S"
        stop()
        display.show(Image.NO)

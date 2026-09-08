"""
micro:bit "Empfänger"
=======================

Dieser micro:bit läuft unabhängig (z.B. an einer Batterie), ohne
Verbindung zum Mac. Er empfängt die Funk-Kommandos vom
"Sender"-micro:bit und zeigt den passenden Pfeil auf der LED-Matrix an.

WICHTIG: RADIO_GROUP muss exakt mit microbit/sender/main.py
übereinstimmen, sonst hört dieser micro:bit nicht mit!

Aufspielen z.B. über https://python.microbit.org (Python-Editor) oder Mu.
"""

from microbit import *
import radio

RADIO_GROUP = 1

radio.config(group=RADIO_GROUP)
radio.on()

ARROWS = {
    "L": Image.ARROW_W,
    "R": Image.ARROW_E,
    "U": Image.ARROW_N,
    "D": Image.ARROW_S,
    "N": Image.HAPPY,
}

display.show(Image.HAPPY)  # bereit und wartet auf Funksignale

while True:
    msg = radio.receive()
    if msg in ARROWS:
        display.show(ARROWS[msg])

"""
micro:bit "Sender"
===================

Dieser micro:bit bleibt per USB-Kabel mit dem Mac verbunden. Er empfängt
die Buchstaben-Kommandos (L, R, U, D, N), die das Python-Skript
webcam/gesture_control.py über die USB-Serielle-Verbindung schickt, und
funkt sie an den "Empfänger"-micro:bit weiter.

WICHTIG: RADIO_GROUP muss exakt mit microbit/receiver/main.py
übereinstimmen, sonst hört der Empfänger nicht mit!

Aufspielen z.B. über https://python.microbit.org (Python-Editor) oder Mu.
"""

from microbit import *
import radio

RADIO_GROUP = 1

radio.config(group=RADIO_GROUP)
radio.on()

# Die USB-Serielle-Verbindung neu konfigurieren, damit unser Programm sie
# nutzen kann (auf dem micro:bit läuft standardmäßig hier die REPL).
uart.init(baudrate=115200)

ARROWS = {
    "L": Image.ARROW_W,
    "R": Image.ARROW_E,
    "U": Image.ARROW_N,
    "D": Image.ARROW_S,
    "N": Image.HAPPY,
}

display.show(Image.HAPPY)  # bereit und wartet auf Kommandos

last_cmd = None

while True:
    if uart.any():
        data = uart.read()
        if data:
            # Nur das zuletzt empfangene Zeichen verwenden
            cmd = chr(data[-1])

            if cmd in ARROWS and cmd != last_cmd:
                last_cmd = cmd
                radio.send(cmd)
                display.show(ARROWS[cmd])

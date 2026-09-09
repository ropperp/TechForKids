"""
micro:bit "Sender" (für die BitBot-XL-Gestensteuerung)
=========================================================

Bleibt per USB-Kabel mit dem Mac verbunden. Empfängt die
Kommando-Zeichen (S/L/R/V), die gesture_reader.py über die
USB-Serielle-Verbindung schickt, und funkt sie an den micro:bit auf
dem BitBot XL weiter (siehe ../microbit-bitbot/main.py).

WICHTIG: RADIO_GROUP muss exakt mit microbit-bitbot/main.py
übereinstimmen, sonst hört der BitBot nicht mit!

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

VALID_COMMANDS = "SLRV"

display.show(Image.HAPPY)  # bereit und wartet auf Kommandos

while True:
    if uart.any():
        data = uart.read()
        if data:
            # Nur das zuletzt empfangene Zeichen verwenden und weiterfunken
            cmd = chr(data[-1])
            if cmd in VALID_COMMANDS:
                radio.send(cmd)

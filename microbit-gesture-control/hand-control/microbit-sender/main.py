"""
micro:bit "Sender" (für die BitBot-XL-Gestensteuerung)
=========================================================

Bleibt per USB-Kabel mit dem Mac verbunden. Empfängt Kommandos von
gesture_reader.py über die USB-Serielle-Verbindung und funkt sie an
den micro:bit auf dem BitBot XL weiter (siehe ../microbit-bitbot/main.py).

Ein Kommando hat das Format "<Richtung><4-stellige Geschwindigkeit>",
z.B. "L0150" oder "V0600", abgeschlossen mit einem Zeilenumbruch. Da
die USB-Verbindung ein Bytestrom ohne feste Nachrichtengrenzen ist,
wird hier zeilenweise gepuffert (bis "\\n") und erst dann komplett per
Funk weitergeschickt.

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

display.show(Image.HAPPY)  # bereit und wartet auf Kommandos

buffer = ""

while True:
    if uart.any():
        data = uart.read()
        if data:
            try:
                buffer += data.decode("utf-8")
            except ValueError:
                buffer = ""  # ungültige Bytes empfangen -> Puffer verwerfen

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line:
                    radio.send(line)

            # Puffer nicht unbegrenzt wachsen lassen, falls mal Datenmüll kommt
            if len(buffer) > 32:
                buffer = ""

"""
micro:bit "Gestenanzeige"
===========================

Dieser micro:bit hängt per USB am Computer. Er wartet auf ein einzelnes
Buchstaben-Kommando über die USB-Serielle-Verbindung (geschickt von der
Webseite in web/app.js, die ein selbst trainiertes Teachable-Machine-
Modell nutzt) und zeigt dazu einmalig das passende Bild an.

Aufspielen z.B. über https://python.microbit.org (Python-Editor) oder Mu.
"""

from microbit import *

# ---------------------------------------------------------------------
# HIER ANPASSEN: Zuordnung Kommando-Buchstabe -> anzuzeigendes Bild.
# Für neue Gesten/Kommandos einfach eine weitere Zeile hinzufügen - der
# Buchstabe muss zu GESTURE_CONFIG in web/app.js passen!
# ---------------------------------------------------------------------
COMMANDS = {
    "L": Image.ARROW_W,
    "R": Image.ARROW_E,
    "U": Image.ARROW_N,
    "D": Image.ARROW_S,
    "N": Image.HAPPY,
}

# Die USB-Serielle-Verbindung neu konfigurieren, damit unser Programm sie
# nutzen kann (auf dem micro:bit läuft standardmäßig hier die REPL).
uart.init(baudrate=115200)

display.show(Image.HAPPY)  # bereit und wartet auf ein Kommando

last_cmd = None

while True:
    if uart.any():
        data = uart.read()
        if data:
            # Nur das zuletzt empfangene Zeichen verwenden
            cmd = chr(data[-1])

            if cmd in COMMANDS and cmd != last_cmd:
                last_cmd = cmd
                display.show(COMMANDS[cmd])

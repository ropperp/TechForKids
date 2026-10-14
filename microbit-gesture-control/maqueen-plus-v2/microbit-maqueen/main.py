"""
micro:bit auf dem Maqueen Plus V2 (Motorsteuerung per Funk)
==============================================================

Läuft auf dem micro:bit, der im Maqueen Plus V2 steckt (batteriebetrieben,
kein USB-Kabel während der Fahrt). Empfängt die Funk-Kommandos vom
Sender-micro:bit (siehe ../microbit-sender/main.py) und steuert damit
Motoren, eingebaute Lichter und den Lautsprecher an.

Ein Kommando hat das Format "<Modus>,<linkes Rad>,<rechtes Rad>", z.B.
"L,150,600" (Kurve links, linkes Rad 150, rechtes Rad 600) oder
"B,-400,-400" (rückwärts). Negative Werte bedeuten rückwärts. Modus ist
nur für Anzeige/Lichter/Ton relevant (S=Stopp, B=Rückwärts, V=Vorwärts,
L=Kurve links, R=Kurve rechts) - die eigentliche Fahrbewegung kommt
komplett aus den beiden Radgeschwindigkeiten, die gesture_reader.py
berechnet (dort auch die Geschwindigkeiten einstellbar). Die Werte von
gesture_reader.py liegen im Bereich -1023..1023 (wie beim BitBot XL),
der Maqueen versteht aber nur -255..255 - das Umrechnen übernimmt
dieses Programm (siehe scale_speed), damit gesture_reader.py für beide
Roboter unverändert gleich bleibt.

WICHTIG: RADIO_GROUP muss exakt mit microbit-sender/main.py
übereinstimmen, sonst kommen keine Kommandos an!

Motoransteuerung beim Maqueen Plus V2 (aus dem offiziellen DFRobot-
MakeCode-Paket https://github.com/DFRobot/pxt-DFRobot_MaqueenPlus_v20
entnommen - DFRobot bietet leider keine fertige MicroPython-Bibliothek
an, deshalb sprechen wir den eingebauten Motor-Controller hier direkt
per I2C an):
    I2C-Adresse: 0x10
    Linker Motor:  Register 0x00, dann [Richtung (0=vor,1=zurück), Tempo 0-255]
    Rechter Motor: Register 0x02, gleiches Format
Im Gegensatz zum BitBot XL gibt es hier also keine einzelnen GPIO-Pins
für die Motoren - alles läuft über diese zwei I2C-Register.

Eingebaute Lichter: ebenfalls per I2C, Register 11 (links) und 12
(rechts), ein Byte mit Farbcode (0=aus, 1=rot, 2=grün, ...). Grün bei
Vorwärts-/Kurvenfahrt, rot bei Rückwärtsfahrt, aus bei Stopp.

Sicherheit: Kommt länger als WATCHDOG_MS kein neues Funkkommando an
(z.B. weil der Sender-micro:bit ausgeschaltet oder außer Reichweite
ist), wird automatisch gestoppt, statt einfach weiterzufahren.

Aufspielen z.B. über https://python.microbit.org (Python-Editor) oder Mu.
"""

from microbit import *
import radio
import music

RADIO_GROUP = 1
WATCHDOG_MS = 1000  # Sicherheits-Stopp, wenn so lange kein Kommando ankommt

I2C_ADDR = 0x10
LEFT_MOTOR_REG = 0x00
RIGHT_MOTOR_REG = 0x02
LEFT_LIGHT_REG = 11
RIGHT_LIGHT_REG = 12

BLACK = 0
RED = 1
GREEN = 2

radio.config(group=RADIO_GROUP)
radio.on()


def scale_speed(speed):
    """Rechnet den Bereich -1023..1023 von gesture_reader.py auf den
    vom Maqueen verstandenen Bereich -255..255 um."""
    scaled = speed // 4
    if scaled > 255:
        return 255
    if scaled < -255:
        return -255
    return scaled


def set_motor(register, speed):
    speed = scale_speed(speed)
    direction = 0 if speed >= 0 else 1
    magnitude = abs(speed)
    i2c.write(I2C_ADDR, bytes([register, direction, magnitude]))


def drive(left_speed, right_speed):
    set_motor(LEFT_MOTOR_REG, left_speed)
    set_motor(RIGHT_MOTOR_REG, right_speed)


def stop():
    drive(0, 0)


def set_lights(color):
    i2c.write(I2C_ADDR, bytes([LEFT_LIGHT_REG, color]))
    i2c.write(I2C_ADDR, bytes([RIGHT_LIGHT_REG, color]))


DISPLAY_IMAGES = {
    "S": Image.NO,
    "B": Image.ARROW_S,
    "V": Image.ARROW_N,
    "L": Image.ARROW_W,
    "R": Image.ARROW_E,
}

stop()
set_lights(BLACK)
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
                        set_lights(RED)
                        # Sofort piepsen, danach übernimmt die Wiederholung unten
                        last_beep_time = running_time() - BEEP_INTERVAL_MS
                    elif mode == "S":
                        set_lights(BLACK)
                    else:  # V, L, R -> vorwärts unterwegs
                        set_lights(GREEN)

    # Beim Rückwärtsfahren alle BEEP_INTERVAL_MS erneut piepsen
    if last_mode == "B" and running_time() - last_beep_time >= BEEP_INTERVAL_MS:
        last_beep_time = running_time()
        music.pitch(880, 150, pin=pin0, wait=False)

    # Sicherheits-Stopp bei Funkausfall
    if last_mode != "S" and running_time() - last_receive_time > WATCHDOG_MS:
        last_mode = "S"
        stop()
        set_lights(BLACK)
        display.show(Image.NO)

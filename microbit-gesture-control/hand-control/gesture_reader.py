"""
Handgesten-Erkennung -> micro:bit -> BitBot XL
=================================================

Erkennt per Webcam fünf Gesten und schickt sie als Kommando (Richtung +
Geschwindigkeit) über die USB-Serielle-Verbindung an den
"Sender"-micro:bit (siehe microbit-sender/main.py), der es per Funk an
den micro:bit auf dem BitBot XL weiterleitet (siehe
microbit-bitbot/main.py):

- Faust (0-1 Finger gestreckt)            -> STOPP      -> "S"
- Zwei Finger gestreckt ("Peace-Zeichen")  -> RUECKWAERTS -> "B"
- Offene Hand, nicht gekippt (neutral)     -> VORWAERTS   -> "V"
- Offene Hand, nach links gekippt          -> LINKS       -> "L"
- Offene Hand, nach rechts gekippt         -> RECHTS      -> "R"
- Keine Hand im Bild                       -> STOPP (Sicherheit!)

Die "Kippung" wird über die Rotation der Hand gemessen (wie ein
Lenkrad), nicht über die Position im Bild. Beim Lenken (LINKS/RECHTS)
wird die Geschwindigkeit **proportional** zur Kippung gesendet: leicht
gekippt -> langsame Drehung, stark gekippt -> schnelle Drehung.

Die Fahrgeschwindigkeiten (vorwärts/Lenken/rückwärts) werden beim Start
abgefragt (Enter = Standardwert übernehmen), damit man sie nicht im
Code ändern muss. Mit --no-prompt werden die Standardwerte direkt ohne
Nachfrage verwendet.

Damit der Roboter nicht einfach weiterfährt, falls ein Funkpaket
verloren geht, wird das aktuelle Kommando nicht nur bei Änderung,
sondern regelmäßig (HEARTBEAT_INTERVAL_S) erneut gesendet. Der
micro:bit auf dem BitBot stoppt automatisch, wenn länger keine
Nachricht mehr ankommt.

Voraussetzungen:
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Benutzung:
    python gesture_reader.py --list-ports           # verfügbare Ports anzeigen
    python gesture_reader.py --port /dev/tty.usbmodemXXXX
    python gesture_reader.py --port /dev/tty.usbmodemXXXX --no-prompt
    python gesture_reader.py --dry-run               # ohne micro:bit testen
    'q' im Kamerafenster beendet das Programm.
"""

import argparse
import math
import sys
import time

import cv2
import mediapipe as mp

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

# ---------------------------------------------------------------------
# HIER ANPASSEN, falls die Erkennung nicht gut passt:
# ---------------------------------------------------------------------
FIST_MAX_EXTENDED = 1         # so viele gestreckte Finger gelten noch als Faust
REVERSE_EXTENDED = 2          # so viele gestreckte Finger gelten als "Rückwärts"-Geste
ROTATION_THRESHOLD_DEG = 20   # ab dieser Neigung (in Grad) gilt die Hand als "gekippt"
MAX_TILT_ANGLE_DEG = 60       # ab dieser Neigung wird mit voller Geschwindigkeit gedreht
STABLE_FRAMES = 3             # so viele Frames hintereinander für eine stabile Erkennung
HEARTBEAT_INTERVAL_S = 0.3    # aktuelles Kommando spätestens alle X Sekunden erneut senden

# Standard-Geschwindigkeiten (0-1023), können beim Start angepasst werden
DEFAULT_FORWARD_SPEED = 600
DEFAULT_REVERSE_SPEED = 400
DEFAULT_MIN_TURN_SPEED = 150   # Drehgeschwindigkeit bei leichter Kippung
DEFAULT_MAX_TURN_SPEED = 900   # Drehgeschwindigkeit bei starker Kippung

FINGER_TIPS = [8, 12, 16, 20]  # Zeige-, Mittel-, Ring-, kleiner Finger
FINGER_MCPS = [5, 9, 13, 17]   # jeweilige Grundgelenke (Knöchel)


def count_extended_fingers(landmarks):
    """Zählt, wie viele der vier Finger (ohne Daumen) gestreckt sind.

    Nutzt den Abstand zum Handgelenk statt der reinen y-Koordinate,
    damit die Erkennung auch bei gekippter/rotierter Hand funktioniert.
    """
    wrist = landmarks[0]
    extended = 0
    for tip_idx, mcp_idx in zip(FINGER_TIPS, FINGER_MCPS):
        tip = landmarks[tip_idx]
        mcp = landmarks[mcp_idx]
        dist_tip = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
        dist_mcp = math.hypot(mcp.x - wrist.x, mcp.y - wrist.y)
        if dist_tip > dist_mcp * 1.3:
            extended += 1
    return extended


def hand_tilt_degrees(landmarks, w, h):
    """Berechnet die Neigung der Hand wie bei einem Lenkrad.

    Nutzt die Linie zwischen den Grundgelenken von Zeigefinger und
    kleinem Finger - bei aufrechter, neutraler Hand ist diese Linie
    ungefähr waagrecht (0 Grad).
    """
    index_mcp = landmarks[5]
    pinky_mcp = landmarks[17]
    dx = (pinky_mcp.x - index_mcp.x) * w
    dy = (pinky_mcp.y - index_mcp.y) * h
    angle = math.degrees(math.atan2(dy, dx))
    # In den Bereich -90..90 Grad normalisieren
    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180
    return angle


def classify(landmarks, w, h):
    extended = count_extended_fingers(landmarks)
    if extended <= FIST_MAX_EXTENDED:
        return "STOPP", extended, None
    if extended == REVERSE_EXTENDED:
        return "RUECKWAERTS", extended, None

    angle = hand_tilt_degrees(landmarks, w, h)
    if angle > ROTATION_THRESHOLD_DEG:
        return "LINKS", extended, angle
    if angle < -ROTATION_THRESHOLD_DEG:
        return "RECHTS", extended, angle
    return "VORWAERTS", extended, angle


def turn_speed_for_angle(angle, min_speed, max_speed):
    """Rechnet einen Kippwinkel proportional in eine Drehgeschwindigkeit um."""
    if angle is None:
        return min_speed
    magnitude = min(abs(angle), MAX_TILT_ANGLE_DEG)
    span = MAX_TILT_ANGLE_DEG - ROTATION_THRESHOLD_DEG
    ratio = max(0.0, (magnitude - ROTATION_THRESHOLD_DEG) / span) if span > 0 else 1.0
    return int(round(min_speed + ratio * (max_speed - min_speed)))


def command_for_gesture(gesture, angle, speeds):
    """Übersetzt eine erkannte Geste in ein (Richtung, Geschwindigkeit)-Paar."""
    if gesture == "STOPP":
        return "S", 0
    if gesture == "RUECKWAERTS":
        return "B", speeds["reverse"]
    if gesture == "VORWAERTS":
        return "V", speeds["forward"]
    if gesture == "LINKS":
        return "L", turn_speed_for_angle(angle, speeds["min_turn"], speeds["max_turn"])
    if gesture == "RECHTS":
        return "R", turn_speed_for_angle(angle, speeds["min_turn"], speeds["max_turn"])
    return "S", 0


def prompt_int(label, default):
    try:
        raw = input(f"{label} [Standard {default}, Enter = übernehmen]: ").strip()
    except EOFError:
        raw = ""
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"Ungültige Eingabe, verwende Standardwert {default}.")
        return default
    return max(0, min(1023, value))


def prompt_speeds():
    print("\nGeschwindigkeiten einstellen (0-1023, Enter = Standardwert):")
    forward = prompt_int("  Vorwärts", DEFAULT_FORWARD_SPEED)
    reverse = prompt_int("  Rückwärts", DEFAULT_REVERSE_SPEED)
    min_turn = prompt_int("  Drehen (leichte Kippung)", DEFAULT_MIN_TURN_SPEED)
    max_turn = prompt_int("  Drehen (starke Kippung)", DEFAULT_MAX_TURN_SPEED)
    print()
    return {"forward": forward, "reverse": reverse, "min_turn": min_turn, "max_turn": max_turn}


def open_serial(port, baudrate):
    if serial is None:
        print("pyserial ist nicht installiert. Bitte 'pip install pyserial' ausführen.")
        sys.exit(1)
    return serial.Serial(port, baudrate=baudrate, timeout=0)


def list_serial_ports():
    if list_ports is None:
        print("pyserial ist nicht installiert. Bitte 'pip install pyserial' ausführen.")
        sys.exit(1)
    ports = list(list_ports.comports())
    if not ports:
        print("Keine seriellen Ports gefunden. Ist der Sender-micro:bit per USB verbunden?")
        return
    for p in ports:
        print(f"{p.device}  -  {p.description}")


def send_command(ser, direction, speed):
    # Format: 1 Zeichen Richtung + 4-stellige Geschwindigkeit + Zeilenumbruch,
    # z.B. "L0150\n" - der Zeilenumbruch markiert das Nachrichtenende für den
    # Sender-micro:bit (siehe microbit-sender/main.py).
    ser.write(f"{direction}{speed:04d}\n".encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port",
        help="Serieller Port des Sender-micro:bit, z.B. /dev/tty.usbmodem1102 (siehe --list-ports)",
    )
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--camera", type=int, default=0, help="Index der Webcam (Standard: 0)")
    parser.add_argument(
        "--list-ports", action="store_true", help="Verfügbare serielle Ports anzeigen und beenden"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Nur Vorschau anzeigen, nichts an micro:bit senden"
    )
    parser.add_argument(
        "--no-prompt", action="store_true", help="Beim Start nicht nach Geschwindigkeiten fragen"
    )
    args = parser.parse_args()

    if args.list_ports:
        list_serial_ports()
        return

    ser = None
    if not args.dry_run:
        if not args.port:
            print("Bitte --port angeben (siehe --list-ports) oder --dry-run zum Testen verwenden.")
            sys.exit(1)
        ser = open_serial(args.port, args.baudrate)
        time.sleep(2)  # micro:bit Zeit zum Neustarten nach Verbindungsaufbau geben

    if args.no_prompt or args.dry_run:
        speeds = {
            "forward": DEFAULT_FORWARD_SPEED,
            "reverse": DEFAULT_REVERSE_SPEED,
            "min_turn": DEFAULT_MIN_TURN_SPEED,
            "max_turn": DEFAULT_MAX_TURN_SPEED,
        }
    else:
        speeds = prompt_speeds()

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print("Webcam konnte nicht geöffnet werden.")
        if ser is not None:
            ser.close()
        return

    candidate = None
    candidate_count = 0
    last_shown = None
    last_sent_time = 0.0

    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5,
        max_num_hands=1,
    ) as hands:
        print("Gestenerkennung läuft. 'q' im Kamerafenster beendet das Programm.")
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)  # Spiegeln, damit "links" auch im Bild links ist
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            # Ohne erkannte Hand ist STOPP die sichere Vorgabe (z.B. wenn die
            # Hand aus dem Bild geht, soll der Roboter nicht weiterfahren).
            gesture, extended, angle = "STOPP", 0, None
            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                gesture, extended, angle = classify(hand_landmarks.landmark, w, h)

            # Für Konsole/Overlay: erst nach STABLE_FRAMES gleichen Frames
            # übernehmen, damit es nicht zwischen Zuständen flackert.
            if gesture == candidate:
                candidate_count += 1
            else:
                candidate = gesture
                candidate_count = 1
            if candidate_count >= STABLE_FRAMES and candidate != last_shown:
                last_shown = candidate
                winkel_text = f", Winkel: {angle:.0f}°" if angle is not None else ""
                print(f"Erkannt: {last_shown} (Finger gestreckt: {extended}{winkel_text})")

            # Für den Roboter: die *aktuelle* Geste direkt verwenden (nicht
            # entprellt), damit das Lenken sofort auf die Kippung reagiert -
            # STOPP als Vorgabe ohne erkannte Hand bleibt dabei die sichere
            # Grundeinstellung.
            direction, speed = command_for_gesture(gesture, angle, speeds)

            now = time.time()
            if ser is not None and now - last_sent_time >= HEARTBEAT_INTERVAL_S:
                last_sent_time = now
                send_command(ser, direction, speed)

            cv2.putText(
                frame, f"Geste: {last_shown or '-'} ({direction}{speed:04d})", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
            )
            if angle is not None:
                cv2.putText(
                    frame, f"Winkel: {angle:.0f}  Finger: {extended}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2,
                )

            cv2.imshow("Handgesten-Erkennung (q = beenden)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    if ser is not None:
        send_command(ser, "S", 0)  # zum Schluss sicher stoppen
        ser.close()


if __name__ == "__main__":
    main()

"""
Handgesten-Erkennung -> micro:bit -> BitBot XL
=================================================

Erkennt per Webcam vier Gesten und schickt sie als einzelnes
Kommando-Zeichen über die USB-Serielle-Verbindung an den
"Sender"-micro:bit (siehe microbit-sender/main.py), der sie per Funk
an den micro:bit auf dem BitBot XL weiterleitet
(siehe microbit-bitbot/main.py):

- Faust (Hand geschlossen)              -> STOPP        -> "S"
- Offene Hand, nach links gekippt       -> LINKS         -> "L"
- Offene Hand, nach rechts gekippt      -> RECHTS        -> "R"
- Offene Hand, nicht gekippt (neutral)  -> VORWAERTS      -> "V"
- Keine Hand im Bild                    -> STOPP (Sicherheit!)

Die "Kippung" wird über die Rotation der Hand gemessen (wie ein
Lenkrad), nicht über die Position im Bild - du kannst deine Hand also
an beliebiger Stelle vor der Kamera halten.

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
FIST_MAX_EXTENDED = 1        # so viele gestreckte Finger gelten noch als Faust
ROTATION_THRESHOLD_DEG = 20  # ab dieser Neigung (in Grad) gilt die Hand als "gekippt"
STABLE_FRAMES = 3            # so viele Frames hintereinander für eine stabile Erkennung
HEARTBEAT_INTERVAL_S = 0.3   # aktuelles Kommando spätestens alle X Sekunden erneut senden

FINGER_TIPS = [8, 12, 16, 20]  # Zeige-, Mittel-, Ring-, kleiner Finger
FINGER_MCPS = [5, 9, 13, 17]   # jeweilige Grundgelenke (Knöchel)

# Muss zu COMMANDS in microbit-bitbot/main.py passen!
GESTURE_TO_COMMAND = {
    "STOPP": "S",
    "LINKS": "L",
    "RECHTS": "R",
    "VORWAERTS": "V",
}


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

    angle = hand_tilt_degrees(landmarks, w, h)
    if angle > ROTATION_THRESHOLD_DEG:
        return "RECHTS", extended, angle
    if angle < -ROTATION_THRESHOLD_DEG:
        return "LINKS", extended, angle
    return "VORWAERTS", extended, angle


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

            if gesture == candidate:
                candidate_count += 1
            else:
                candidate = gesture
                candidate_count = 1

            if candidate_count >= STABLE_FRAMES:
                if candidate != last_shown:
                    last_shown = candidate
                    winkel_text = f", Winkel: {angle:.0f}°" if angle is not None else ""
                    print(f"Erkannt: {last_shown} (Finger gestreckt: {extended}{winkel_text})")

                now = time.time()
                if ser is not None and now - last_sent_time >= HEARTBEAT_INTERVAL_S:
                    last_sent_time = now
                    command = GESTURE_TO_COMMAND[last_shown]
                    ser.write(command.encode("utf-8"))

            cv2.putText(
                frame, f"Geste: {last_shown or '-'}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2,
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
        # Zum Schluss sicher stoppen
        ser.write(GESTURE_TO_COMMAND["STOPP"].encode("utf-8"))
        ser.close()


if __name__ == "__main__":
    main()

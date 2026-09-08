"""
Gestensteuerung für micro:bit per Webcam
=========================================

Dieses Skript nutzt die Webcam, um zu erkennen, in welche Richtung du mit
dem Zeigefinger zeigst (links, rechts, hoch, runter). Die erkannte Geste
wird als einzelner Buchstabe über die USB-Serielle-Verbindung an den
"Sender"-micro:bit geschickt. Der Sender-micro:bit funkt das Kommando
dann an einen zweiten "Empfänger"-micro:bit weiter, der einen passenden
Pfeil auf seiner LED-Matrix anzeigt.

Voraussetzungen (siehe requirements.txt):
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Benutzung:
    python gesture_control.py --list-ports        # verfügbare Ports anzeigen
    python gesture_control.py --port /dev/tty.usbmodemXXXX
    python gesture_control.py --dry-run            # ohne micro:bit testen
"""

import argparse
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


# Kommandos, die an den micro:bit geschickt werden.
# Müssen zu den Buchstaben in microbit/sender/main.py und
# microbit/receiver/main.py passen!
GESTURE_LEFT = "L"
GESTURE_RIGHT = "R"
GESTURE_UP = "U"
GESTURE_DOWN = "D"
GESTURE_NONE = "N"

# Wie weit die Fingerspitze vom Handgelenk entfernt sein muss (relativ zur
# Bildbreite), damit es überhaupt als "Zeigegeste" gilt.
MIN_POINT_DISTANCE_RATIO = 0.12

# Wie viele Frames hintereinander die gleiche Geste erkannt werden muss,
# bevor sie als "stabil" gilt und gesendet wird. Verhindert Flackern durch
# einzelne Fehlerkennungen.
STABLE_FRAMES = 5


def classify_direction(dx, dy):
    """Ordnet einen Richtungsvektor (dx, dy) einer der vier Richtungen zu.

    Der Bildursprung liegt oben links, d.h. dy > 0 bedeutet "nach unten".
    """
    if abs(dx) >= abs(dy):
        return GESTURE_RIGHT if dx > 0 else GESTURE_LEFT
    return GESTURE_DOWN if dy > 0 else GESTURE_UP


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
        print("Keine seriellen Ports gefunden. Ist der micro:bit per USB verbunden?")
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

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print("Webcam konnte nicht geöffnet werden. Auf macOS ggf. Kamera-Berechtigung erteilen.")
        sys.exit(1)

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    last_sent = None
    candidate = GESTURE_NONE
    candidate_count = 0

    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5,
        max_num_hands=1,
    ) as hands:
        print("Steuerung läuft. 'q' im Kamerafenster drücken zum Beenden.")
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)  # Spiegeln, damit "links zeigen" auch im Bild links ist
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            gesture = GESTURE_NONE
            h, w, _ = frame.shape

            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(frame, landmarks, mp_hands.HAND_CONNECTIONS)

                wrist = landmarks.landmark[0]
                tip = landmarks.landmark[8]  # Zeigefingerspitze

                dx = (tip.x - wrist.x) * w
                dy = (tip.y - wrist.y) * h
                distance = (dx**2 + dy**2) ** 0.5

                if distance >= MIN_POINT_DISTANCE_RATIO * w:
                    gesture = classify_direction(dx, dy)

            # Geste erst nach STABLE_FRAMES gleichen Frames übernehmen (Entprellen)
            if gesture == candidate:
                candidate_count += 1
            else:
                candidate = gesture
                candidate_count = 1

            if candidate_count >= STABLE_FRAMES and candidate != last_sent:
                last_sent = candidate
                print(f"Geste erkannt: {last_sent}")
                if ser is not None:
                    ser.write(last_sent.encode("utf-8"))

            cv2.putText(
                frame,
                f"Geste: {last_sent or '-'}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv2.imshow("Gestensteuerung (q = beenden)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    if ser is not None:
        ser.close()


if __name__ == "__main__":
    main()

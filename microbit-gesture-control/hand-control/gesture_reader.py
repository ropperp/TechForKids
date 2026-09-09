"""
Handgesten-Erkennung (Testprogramm, Schritt 1)
=================================================

Erkennt per Webcam vier Gesten und gibt sie in der Konsole und im
Kamerafenster aus - noch OHNE micro:bit/BitBot-Anbindung:

- Faust (Hand geschlossen)              -> STOPP
- Offene Hand, nach links gekippt       -> LINKS
- Offene Hand, nach rechts gekippt      -> RECHTS
- Offene Hand, nicht gekippt (neutral)  -> VORWAERTS

Die "Kippung" wird über die Rotation der Hand gemessen (wie ein
Lenkrad), nicht über die Position im Bild - du kannst deine Hand also
an beliebiger Stelle vor der Kamera halten.

Ziel dieses Programms: die Erkennung in Ruhe ausprobieren und bei
Bedarf FIST_MAX_EXTENDED / ROTATION_THRESHOLD_DEG anpassen, bevor
daraus die Ansteuerung des BitBot XL gebaut wird.

Voraussetzungen:
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Benutzung:
    python gesture_reader.py
    'q' im Kamerafenster beendet das Programm.
"""

import math

import cv2
import mediapipe as mp

# ---------------------------------------------------------------------
# HIER ANPASSEN, falls die Erkennung nicht gut passt:
# ---------------------------------------------------------------------
FIST_MAX_EXTENDED = 1        # so viele gestreckte Finger gelten noch als Faust
ROTATION_THRESHOLD_DEG = 20  # ab dieser Neigung (in Grad) gilt die Hand als "gekippt"
STABLE_FRAMES = 3            # so viele Frames hintereinander für eine stabile Erkennung

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

    angle = hand_tilt_degrees(landmarks, w, h)
    if angle > ROTATION_THRESHOLD_DEG:
        return "RECHTS", extended, angle
    if angle < -ROTATION_THRESHOLD_DEG:
        return "LINKS", extended, angle
    return "VORWAERTS", extended, angle


def main():
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Webcam konnte nicht geöffnet werden.")
        return

    candidate = None
    candidate_count = 0
    last_shown = None

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

            gesture, extended, angle = None, 0, None
            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                gesture, extended, angle = classify(hand_landmarks.landmark, w, h)

            if gesture == candidate:
                candidate_count += 1
            else:
                candidate = gesture
                candidate_count = 1

            if candidate_count >= STABLE_FRAMES and candidate != last_shown:
                last_shown = candidate
                if last_shown:
                    winkel_text = f", Winkel: {angle:.0f}°" if angle is not None else ""
                    print(f"Erkannt: {last_shown} (Finger gestreckt: {extended}{winkel_text})")

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


if __name__ == "__main__":
    main()

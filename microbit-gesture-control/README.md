# Gestensteuerung: Webcam → micro:bit → micro:bit (Funk)

Zeig mit der Webcam am Mac nach links, rechts, oben oder unten – ein
zweiter micro:bit zeigt dann per Funk den passenden Pfeil an!

## Wie funktioniert das?

```
  Webcam (Mac)                micro:bit "Sender"        micro:bit "Empfänger"
  ┌───────────────┐   USB     ┌─────────────────┐  Funk  ┌─────────────────┐
  │ Python-Skript  │ ───────▶ │ liest Kommando   │ ─────▶ │ zeigt Pfeil an  │
  │ erkennt Geste  │  Kabel   │ und funkt weiter │        │ auf LED-Matrix  │
  └───────────────┘           └─────────────────┘        └─────────────────┘
```

1. Das Python-Skript `webcam/gesture_control.py` erkennt über die Webcam,
   in welche Richtung dein Zeigefinger zeigt.
2. Es schickt einen Buchstaben (`L`, `R`, `U`, `D`) über das USB-Kabel an
   den ersten micro:bit (den "Sender").
3. Der Sender-micro:bit (`microbit/sender/main.py`) funkt diesen
   Buchstaben an einen zweiten micro:bit weiter.
4. Der Empfänger-micro:bit (`microbit/receiver/main.py`) zeigt den
   passenden Pfeil auf seiner LED-Matrix an.

## Was du brauchst

- 2× micro:bit (mit den neueren Modellen inkl. Funk/`radio`-Modul –
  funktioniert mit allen micro:bit-Versionen)
- 2× USB-Kabel (mindestens für den Sender-micro:bit während des Betriebs
  nötig; für den Empfänger reicht danach auch eine Batteriehalterung)
- Einen Mac mit Webcam
- Python 3.9–3.12

## Schritt 1: micro:bits programmieren

1. Öffne den [micro:bit Python-Editor](https://python.microbit.org) (oder
   die [Mu-Editor-App](https://codewith.mu)).
2. Kopiere den Inhalt von `microbit/sender/main.py` hinein, verbinde den
   **ersten** micro:bit per USB und lade das Programm hoch ("Flash" bzw.
   "Send to micro:bit").
3. Wiederhole das mit `microbit/receiver/main.py` für den **zweiten**
   micro:bit.
4. Beide micro:bits müssen dieselbe `RADIO_GROUP` haben (Standard: `1`).
   Wenn ihr in der Klasse mehrere Teams seid, gebt jedem Team eine
   eigene Gruppennummer (z.B. Team A = 1, Team B = 2, …), damit ihr euch
   nicht gegenseitig stört!

Danach zeigt jeder micro:bit ein lachendes Gesicht 🙂 – er ist bereit.

## Schritt 2: Python-Umgebung einrichten (am Mac)

```bash
cd webcam
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Beim ersten Start fragt macOS nach Kamera-Zugriff für dein Terminal /
> deine Python-App – das bitte erlauben (Systemeinstellungen →
> Datenschutz & Sicherheit → Kamera).

## Schritt 3: Sender-micro:bit anschließen und Port finden

Verbinde den **Sender**-micro:bit per USB mit dem Mac und finde seinen
seriellen Port:

```bash
python gesture_control.py --list-ports
```

Das gibt z.B. `/dev/tty.usbmodem1102` aus.

## Schritt 4: Gestensteuerung starten

```bash
python gesture_control.py --port /dev/tty.usbmodem1102
```

Ein Kamerafenster öffnet sich. Halte deine Hand vor die Kamera und
strecke den Zeigefinger deutlich in eine Richtung:

- Nach **links** zeigen → Empfänger zeigt `⬅`
- Nach **rechts** zeigen → Empfänger zeigt `➡`
- Nach **oben** zeigen → Empfänger zeigt `⬆`
- Nach **unten** zeigen → Empfänger zeigt `⬇`

Mit `q` im Kamerafenster beendest du das Skript.

Zum Ausprobieren ohne angeschlossenen micro:bit kannst du auch
`python gesture_control.py --dry-run` verwenden – dann wird die Geste
nur im Kamerabild angezeigt, aber nicht gesendet.

## Troubleshooting

- **"Webcam konnte nicht geöffnet werden"** → Kamera-Berechtigung für das
  Terminal / die IDE in den macOS-Systemeinstellungen prüfen.
- **Kein Port bei `--list-ports`** → USB-Kabel prüfen (manche Kabel können
  nur laden, nicht Daten übertragen), micro:bit neu einstecken.
- **Empfänger reagiert nicht** → `RADIO_GROUP` in beiden `main.py`-Dateien
  vergleichen, sie müssen identisch sein.
- **Geste wird nicht erkannt** → Für gute Erkennung auf helles Licht und
  einen möglichst einfarbigen Hintergrund hinter der Hand achten, Hand
  nah genug an die Kamera halten.

## Weiterbauen (Ideen für Kids)

- Statt Pfeilen eigene Bilder anzeigen (z.B. `Image.HAPPY` /
  `Image.SAD`, oder ein selbst gemaltes Icon mit `Image("...")`).
- Zusätzliche Gesten erkennen (z.B. Faust = Stopp) und ein fünftes
  Kommando einbauen.
- Den Empfänger-micro:bit einen kleinen Motor oder ein Rad steuern
  lassen, das sich je nach Pfeilrichtung dreht.

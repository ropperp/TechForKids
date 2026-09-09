# Gestensteuerung für micro:bit

Dieses Projekt enthält zwei Ansätze:

- **`web/`** – Trainiere ein KI-Modell mit [Teachable Machine](https://teachablemachine.withgoogle.com/)
  im Browser und lass einen micro:bit dazu einmalig einen Pfeil
  anzeigen. Kein Python nötig, aber durch die Bild-Erkennung spürbar
  verzögert (1-2 Sekunden) – gut zum Ausprobieren, für eine flüssige
  **Echtzeit-Robotersteuerung** aber zu langsam.
- **`hand-control/`** – Schnelle, trainingsfreie Erkennung per
  Hand-Landmarken (Faust = Stopp, Hand nach links/rechts gekippt =
  Lenken, neutral = geradeaus) in Python. Reagiert praktisch ohne
  Verzögerung und ist der Ausgangspunkt für die Steuerung des
  **BitBot XL**. Siehe Abschnitt weiter unten.

## Ansatz 1: Teachable Machine → micro:bit (`web/`)

Trainiere dein eigenes KI-Modell mit [Teachable Machine](https://teachablemachine.withgoogle.com/)
(z.B. "links zeigen", "rechts zeigen", ...) und lass einen micro:bit
dazu einmalig den passenden Pfeil anzeigen.

### Wie funktioniert das?

```
  Webcam (im Browser)              micro:bit
  ┌──────────────────────┐   USB   ┌───────────────────┐
  │ Teachable-Machine-    │ ──────▶ │ zeigt einmalig den │
  │ Modell erkennt Geste  │  Kabel  │ passenden Pfeil an │
  └──────────────────────┘         └───────────────────┘
```

1. Du trainierst im Browser auf teachablemachine.withgoogle.com ein
   Bild-Modell, das deine Gesten unterscheiden kann (z.B. "links",
   "rechts", "oben", "unten", "nichts").
2. Die Seite `web/index.html` lädt dieses Modell, erkennt über die
   Webcam laufend deine Geste und schickt bei einer stabilen Erkennung
   **ein einzelnes Kommando** über die USB-Serielle-Verbindung
   ([Web Serial API](https://developer.chrome.com/docs/capabilities/serial))
   an den micro:bit.
3. Der micro:bit (`microbit/main.py`) zeigt dazu einmalig das passende
   Bild an.

Es wird **kein Python** und **kein zweiter micro:bit** benötigt – alles
läuft direkt im Browser.

> Web Serial funktioniert nur in **Chrome** oder **Edge** (Chromium-Browser),
> nicht in Safari oder Firefox.

### Schritt 1: Modell mit Teachable Machine trainieren

1. Öffne [teachablemachine.withgoogle.com/train/image](https://teachablemachine.withgoogle.com/train/image).
2. Lege für jede Geste eine eigene Klasse an, z.B.:
   - `links` – nach links zeigen
   - `rechts` – nach rechts zeigen
   - `oben` – nach oben zeigen
   - `unten` – nach unten zeigen
   - `nichts` – keine Geste / leeres Bild
3. Nimm pro Klasse mehrere Beispielbilder über die Webcam auf (Knopf
   gedrückt halten), am besten aus leicht unterschiedlichen Positionen
   und mit unterschiedlichem Hintergrund/Licht.
4. Klicke auf **"Train Model"**.
5. Nach dem Training: **"Export Model"** → Tab **"Tensorflow.js"** →
   **"Upload my model"** → auf **Upload** klicken → den angezeigten
   Link (z.B. `https://teachablemachine.withgoogle.com/models/AbC123xyz/`)
   kopieren.

> Tipp: Nutzt ihr andere Klassennamen als oben, müsst ihr sie in
> `web/app.js` in `GESTURE_CONFIG` anpassen (siehe Schritt 3).

### Schritt 2: micro:bit programmieren

1. Öffne den [micro:bit Python-Editor](https://python.microbit.org) (oder
   die [Mu-Editor-App](https://codewith.mu)).
2. Kopiere den Inhalt von `microbit/main.py` hinein.
3. Verbinde den micro:bit per USB und lade das Programm hoch ("Flash"
   bzw. "Send to micro:bit").

Der micro:bit zeigt danach ein lachendes Gesicht 🙂 – er ist bereit.

### Schritt 3: Webseite öffnen und verbinden

1. Öffne `web/index.html` in **Google Chrome** oder **Microsoft Edge**
   (Doppelklick reicht, oder per `File → Open File...`).
2. Füge den in Schritt 1 kopierten Modell-Link in das Textfeld ein und
   klicke auf **"Modell laden"**. Erlaube der Seite den Kamerazugriff.
3. Klicke auf **"micro:bit verbinden"** und wähle in der erscheinenden
   Liste den micro:bit aus.
4. Zeig eine deiner trainierten Gesten – sobald sie stabil erkannt
   wird, zeigt der micro:bit einmalig den passenden Pfeil an.

### Für Weiterentwicklung: Kommandos anpassen/erweitern

Alle Zuordnungen zwischen Geste und Anzeige sind an **zwei zentralen
Stellen** definiert – dort einfach neue Zeilen hinzufügen:

- **`web/app.js`** → `GESTURE_CONFIG`: Teachable-Machine-Klassenname →
  Kommando-Buchstabe, der an den micro:bit gesendet wird.
- **`microbit/main.py`** → `COMMANDS`: Kommando-Buchstabe → Bild, das
  der micro:bit anzeigt (z.B. `Image.ARROW_W` für den Pfeil nach links,
  oder ein selbst gemaltes Icon mit `Image("...")`).

Wichtig: Der Kommando-Buchstabe muss an beiden Stellen **gleich**
geschrieben sein.

### Weitere Ideen

- Eine zusätzliche Geste trainieren (z.B. Faust = "Stopp") und in
  beiden Konfigurationen ein neues Kommando ergänzen.
- Statt eines Pfeils eine kleine Animation anzeigen
  (`display.show([Image1, Image2, ...], delay=100)`).
- Den micro:bit einen Motor oder ein Rad steuern lassen, das sich je
  nach erkannter Geste dreht.

### Troubleshooting (Teachable-Machine-Ansatz)

- **"micro:bit verbinden" zeigt keinen Port an** → USB-Kabel prüfen
  (manche Kabel können nur laden, nicht Daten übertragen), micro:bit
  neu einstecken.
- **Web Serial funktioniert nicht** → Nur Chrome/Edge werden
  unterstützt, Safari und Firefox können das (noch) nicht.
- **Kamera startet nicht** → Kamera-Berechtigung für den Browser in den
  macOS-Systemeinstellungen prüfen (Systemeinstellungen → Datenschutz &
  Sicherheit → Kamera).
- **Geste wird nicht/falsch erkannt** → Mehr und vielfältigere
  Trainingsbilder pro Klasse in Teachable Machine aufnehmen, auf gutes
  Licht achten, Modell neu trainieren. Die Webseite nimmt die Webcam
  bewusst quadratisch auf (wie Teachable Machine selbst) – bei einem
  rechteckigen Kamerabild würde die Erkennung durch Verzerrung deutlich
  schlechter werden.
- **micro:bit reagiert gar nicht** → Prüfen, ob `microbit/main.py`
  erfolgreich aufgespielt wurde (micro:bit sollte ein Smiley zeigen).
- **Reaktion fühlt sich verzögert an** → Das Modell selbst läuft nach
  dem Laden komplett lokal im Browser (kein Netzzugriff pro Bild), die
  Verzögerung kommt von der Entprellung gegen Fehlerkennungen. In
  `web/app.js` lässt sich das über `STABLE_FRAMES` (Anzahl gleicher
  Vorhersagen hintereinander) und `PREDICTION_INTERVAL_MS` (Abstand
  zwischen Vorhersagen) feinjustieren – kleinere Werte reagieren
  schneller, sind aber anfälliger für kurze Fehlerkennungen. Für eine
  **spürbar** schnellere, quasi verzögerungsfreie Steuerung (z.B. für
  einen Roboter) nutze stattdessen `hand-control/` (siehe unten).
- **Nach neuem Training ändert sich nichts** → Falls dein Teachable-
  Machine-Link nach dem Re-Upload gleich bleibt, holt die Seite sich
  Modell und Metadaten inzwischen bewusst ohne Browser-Cache
  (`cache: "no-store"` in `web/app.js`) – einfach erneut auf "Modell
  laden" klicken, ein Neuladen der Seite ist nicht nötig.
- **Eine Geste wird erkannt, aber am micro:bit passiert nichts** → Der
  Status-Text unter der Webcam zeigt jetzt an, wenn eine Klasse zwar
  erkannt wurde, aber kein Kommando dafür konfiguriert ist (z.B. weil
  deine Klasse in Teachable Machine anders heißt als `links`/`rechts`/
  `oben`/`unten`/`nichts`). Den dort angezeigten Klassennamen einfach 1:1
  in `GESTURE_CONFIG` in `web/app.js` ergänzen.

## Ansatz 2: Schnelle Handgesten-Erkennung für den BitBot XL (`hand-control/`)

Für eine **flüssige Echtzeit-Robotersteuerung** ist ein Bild-Klassifizierer
wie Teachable Machine zu langsam (jedes Bild muss komplett durch ein
neuronales Netz). Stattdessen nutzt `hand-control/` **Hand-Landmarken**
(21 Punkte an Handgelenk/Fingern, per [MediaPipe](https://developers.google.com/mediapipe)) –
reine Geometrie-Rechnung, kein Training nötig, reagiert praktisch ohne
Verzögerung.

### Erkannte Gesten

- **Faust** (Hand geschlossen) → `STOPP`
- **Offene Hand, nach links gekippt** (wie ein Lenkrad gedreht) → `LINKS`
- **Offene Hand, nach rechts gekippt** → `RECHTS`
- **Offene Hand, nicht gekippt** (neutral, aufrecht) → `VORWAERTS`

Die Kippung wird über die **Rotation** der Hand gemessen, nicht über
ihre Position im Bild – du kannst die Hand also an beliebiger Stelle
vor der Kamera halten, wie beim Drehen eines Lenkrads.

### Schritt 1 (aktueller Stand): Nur die Erkennung testen

Noch **ohne** micro:bit/BitBot-Anbindung – zum Ausprobieren und
Feinjustieren der Erkennung:

```bash
cd hand-control
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python gesture_reader.py
```

Ein Kamerafenster öffnet sich, zeigt die erkannten Hand-Landmarken und
oben links die aktuell erkannte Geste sowie den gemessenen Winkel. In
der Konsole wird jede neu erkannte Geste zusätzlich als Text ausgegeben
(z.B. `Erkannt: LINKS (Finger gestreckt: 4, Winkel: -34°)`). Mit `q` im
Kamerafenster beenden.

Passt die Erkennung nicht gut (z.B. Faust wird nicht erkannt, oder die
Lenk-Schwelle ist zu empfindlich/unempfindlich), können am Kopf von
`gesture_reader.py` die Werte `FIST_MAX_EXTENDED` und
`ROTATION_THRESHOLD_DEG` angepasst werden – der im Kamerafenster
angezeigte Winkel hilft dabei, einen guten Schwellenwert zu finden.

> **Fehler `AttributeError: module 'mediapipe' has no attribute 'solutions'`?**
> Dann wurde beim Installieren eine zu neue mediapipe-Version geladen
> (ab Version 1.0 wurde die hier genutzte Schnittstelle entfernt). Im
> aktivierten `.venv` einmal ausführen: `pip install "mediapipe==0.10.14"`
> und `gesture_reader.py` erneut starten.

### Schritt 2 (nächster Schritt): BitBot XL ansteuern

Sobald die Erkennung zuverlässig läuft, verbinden wir `gesture_reader.py`
mit einem micro:bit auf dem BitBot XL. Der BitBot XL hat eine offizielle
MicroPython-Bibliothek (`bitbot`) mit fertigen Fahrfunktionen wie
`bitbot.forward(speed)`, `bitbot.spinLeft(speed)`, `bitbot.spinRight(speed)`
und `bitbot.stop()` – die vier erkannten Gesten werden dann jeweils auf
eine dieser Funktionen abgebildet, ähnlich wie schon bei Ansatz 1 über
eine USB-Serielle-Verbindung. Dieser Teil folgt, sobald Schritt 1 bei
euch zuverlässig funktioniert.

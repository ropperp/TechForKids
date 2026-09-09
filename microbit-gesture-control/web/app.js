/*
 * Gestensteuerung für micro:bit mit Teachable Machine
 * =====================================================
 *
 * 1. Bild-Modell auf https://teachablemachine.withgoogle.com trainieren
 *    (z.B. Klassen "links", "rechts", "oben", "unten", "nichts").
 * 2. "Export Model" -> Tab "Tensorflow.js" -> "Upload my model" -> Link
 *    kopieren und in index.html im Textfeld einfügen.
 * 3. micro:bit mit microbit/main.py bespielen und per USB anschließen.
 * 4. Diese Seite in Google Chrome oder Microsoft Edge öffnen (Web Serial
 *    API wird nur dort unterstützt, nicht in Safari/Firefox), Modell
 *    laden, micro:bit verbinden, fertig!
 */

// ---------------------------------------------------------------------
// HIER ANPASSEN: Zuordnung Teachable-Machine-Klasse -> micro:bit-Kommando.
// Groß-/Kleinschreibung und Leerzeichen werden ignoriert. Für neue
// Gesten einfach eine weitere Zeile hinzufügen - der Buchstabe (rechts)
// muss zu COMMANDS in microbit/main.py passen. Falls deine Klasse für
// "keine Geste" anders heißt als hier gelistet, einfach eine weitere
// Zeile mit deinem Namen -> "N" ergänzen.
// ---------------------------------------------------------------------
const GESTURE_CONFIG = {
  "links": "L",
  "rechts": "R",
  "oben": "U",
  "unten": "D",
  "nichts": "N",
  "mitte": "N",
  "neutral": "N",
};

// Schlägt ein Kommando für eine Teachable-Machine-Klasse nach, dabei
// werden Groß-/Kleinschreibung und Leerzeichen ignoriert.
function lookupCommand(className) {
  if (!className) return null;
  return GESTURE_CONFIG[className.trim().toLowerCase()] || null;
}

const STABLE_FRAMES = 4; // so viele gleiche Vorhersagen hintereinander, bevor gesendet wird
const PREDICTION_INTERVAL_MS = 100;
const MIN_CONFIDENCE = 0.8; // Vorhersage muss mindestens so sicher sein

let model, webcam, maxPredictions;
let port, writer;
let candidate = null;
let candidateCount = 0;
let lastSent = null;
let lastPredictTime = 0;

const statusEl = document.getElementById("status");
const labelContainer = document.getElementById("label-container");

document.getElementById("loadModelBtn").addEventListener("click", loadModel);
document.getElementById("connectBtn").addEventListener("click", connectMicrobit);

async function loadModel() {
  const base = document.getElementById("modelUrl").value.trim();
  if (!base) {
    alert("Bitte zuerst die Modell-URL aus Teachable Machine eintragen.");
    return;
  }
  const dir = base.endsWith("/") ? base : base + "/";
  const modelURL = dir + "model.json";
  // Zeitstempel anhängen, damit bei gleichbleibendem Link nach dem
  // Neu-Trainieren wirklich die neuen metadata.json geladen werden und
  // nicht eine im Browser zwischengespeicherte alte Version.
  const metadataURL = dir + "metadata.json?v=" + Date.now();

  statusEl.textContent = "Status: Modell wird geladen ...";
  try {
    // "cache: no-store" sorgt dafür, dass model.json und die
    // zugehörigen weights.bin ebenfalls nicht aus dem Browser-Cache
    // kommen, sondern nach jedem erneuten Training frisch geladen werden.
    const modelSource = tf.io.browserHTTPRequest(modelURL, {
      requestInit: { cache: "no-store" },
    });
    model = await tmImage.load(modelSource, metadataURL);
  } catch (err) {
    console.error(err);
    statusEl.textContent = "Status: Modell konnte nicht geladen werden. Link prüfen.";
    return;
  }
  maxPredictions = model.getTotalClasses();

  // Quadratisches Format (wie bei Teachable Machine selbst) verwenden!
  // Ein rechteckiges Bild würde beim Umrechnen auf die quadratische
  // Eingabegröße des Modells verzerrt und die Erkennung verschlechtern.
  webcam = new tmImage.Webcam(224, 224, true); // Breite, Höhe, spiegeln
  await webcam.setup();
  await webcam.play();
  document.getElementById("webcam-container").innerHTML = "";
  document.getElementById("webcam-container").appendChild(webcam.canvas);

  labelContainer.innerHTML = "";
  for (let i = 0; i < maxPredictions; i++) {
    labelContainer.appendChild(document.createElement("div"));
  }

  statusEl.textContent = "Status: Modell geladen. Jetzt micro:bit verbinden.";
  requestAnimationFrame(loop);
}

async function loop() {
  webcam.update();
  await predict();
  requestAnimationFrame(loop);
}

async function predict() {
  const now = performance.now();
  if (now - lastPredictTime < PREDICTION_INTERVAL_MS) return;
  lastPredictTime = now;

  const predictions = await model.predict(webcam.canvas);
  predictions.sort((a, b) => b.probability - a.probability);

  for (let i = 0; i < predictions.length; i++) {
    labelContainer.childNodes[i].innerHTML =
      `${predictions[i].className}: ${(predictions[i].probability * 100).toFixed(0)}%`;
  }

  const top = predictions[0];
  const className = top.probability >= MIN_CONFIDENCE ? top.className : null;
  handlePrediction(className);
}

function handlePrediction(className) {
  if (className === candidate) {
    candidateCount++;
  } else {
    candidate = className;
    candidateCount = 1;
  }

  if (candidateCount >= STABLE_FRAMES && candidate !== lastSent) {
    lastSent = candidate;
    const command = lookupCommand(candidate);
    if (command) {
      sendCommand(command);
      statusEl.textContent = `Status: Geste "${candidate}" erkannt -> sende "${command}"`;
    } else {
      // Klasse erkannt, aber kein Eintrag in GESTURE_CONFIG dafür -
      // sichtbar machen statt einfach nichts zu tun, damit man den
      // exakten Klassennamen sieht und in web/app.js ergänzen kann.
      statusEl.textContent = `Status: Geste "${candidate}" erkannt, aber kein Kommando dafür konfiguriert (GESTURE_CONFIG in web/app.js ergänzen).`;
    }
  }
}

async function connectMicrobit() {
  if (!("serial" in navigator)) {
    alert("Web Serial API wird von diesem Browser nicht unterstützt. Bitte Chrome oder Edge verwenden.");
    return;
  }
  try {
    port = await navigator.serial.requestPort();
    await port.open({ baudRate: 115200 });
    writer = port.writable.getWriter();
    statusEl.textContent = "Status: micro:bit verbunden.";
  } catch (err) {
    console.error(err);
    statusEl.textContent = "Status: Verbindung zum micro:bit fehlgeschlagen.";
  }
}

async function sendCommand(command) {
  if (!writer) {
    console.warn("micro:bit ist noch nicht verbunden.");
    return;
  }
  const data = new TextEncoder().encode(command);
  await writer.write(data);
}

# Ollama Murder Mystery Prototyp (Fall: Detective Keller)

Willkommen beim KI-gesteuerten Mordfall-Prototypen! Du übernimmst die Rolle des Detektivs und verhörst die Verdächtigen, die jeweils von einem lokalen Large Language Model (LLM) gesteuert werden.

---

## ⚙️ Quick Start (Voraussetzungen)

Um dieses Spiel zu starten, sind folgende Abhängigkeiten auf deinem Linux-System erforderlich:

1.  **Ollama** (Installiert und im Systempfad verfügbar)
2.  **Python 3.8+**
3.  **Git** (zum Klonen des Repositories)

### Schritt 1: Code klonen & Umgebung vorbereiten

Öffne dein Terminal und führe die folgenden Befehle aus:

```bash
# 1. Repository klonen
git clone [https://github.com/E-Geraet/Ollama_Murder_Mystery_Keller.git](https://github.com/E-Geraet/Ollama_Murder_Mystery_Keller.git)
cd Ollama_Murder_Mystery_Keller

# 2. Virtuelle Umgebung erstellen und aktivieren (Optional, aber empfohlen)
python3 -m venv .venv
source .venv/bin/activate

# 3. Python-Abhängigkeiten installieren
pip install -r requirements.txt

Schritt 2: Ollama KI-Modell bereitstellen (Server starten)

Wir nutzen ministral-3:3b als KI-Gehirn der Agenten.

Führe diesen Befehl aus, um das Modell herunterzuladen (falls noch nicht geschehen) und den KI-Server zu starten. Das ministral-3:3b Modell wird dabei in den Speicher geladen.

    WICHTIG: Lass dieses Terminalfenster geöffnet! Es dient als unser KI-Server.

Bash

ollama run ministral-3:3b

(Warte, bis der >>> Prompt erscheint).
Schritt 3: Spiel starten (Client starten)

Öffne ein zweites Terminalfenster und navigiere in das Projektverzeichnis (aktiviere dort ebenfalls die virtuelle Umgebung, falls verwendet).
Bash

# App starten
python3 app.py

Öffne den angezeigten lokalen Link (http://127.0.0.1:7860) in deinem Browser.


###

Wie spiele ich???

    Ziel: Finde den wahren Mörder, indem du die drei Verdächtigen befragst und Widersprüche aufdeckst.

    Zeitlimit: Du hast 30 Tage Zeit und 5 Aktionen pro Tag (eine Frage/Aktion verbraucht eine Aktion).

    Spezialaktionen: Du kannst Laboruntersuchungen (z.B. DNS) anfordern. Nutze dazu den Befehl im Eingabefeld: /dna [Verdächtiger Name] [Objektname] (Beispiel: /dna Daniel Weber Pistole)

    Anklage: Wenn du dir sicher bist, wähle den Verdächtigen im Anklage-Dropdown und klicke auf Anklagen! (Das beendet das Spiel).



# Ollama_Murder_Mystery

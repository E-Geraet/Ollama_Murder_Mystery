# game_engine.py (V6.1: Korrigiertes Rollenverständnis)

import ollama
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()
# --- KI 2 (Lokal/Verdächtige & Frage-Generator) ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "ministral-3:3b") 

# --- KI 1 (Extern/Detektiv Reasoning) ---
EXTERNAL_API_KEY = os.getenv("EXTERNAL_API_KEY")
EXTERNAL_MODEL_NAME = os.getenv("EXTERNAL_MODEL_NAME")
EXTERNAL_API_URL = os.getenv("EXTERNAL_API_URL")

# GLOBALE VARIABLE FÜR DAS REASONING
detektiv_log = [] 

# --- 1. Externe API (Für den Detektiv/Reasoning) ---
def ask_external_api(prompt: str, system_prompt: str) -> str:
    """Sendet eine Anfrage an die Gemini API (Google Generative Language API)."""
    
    if not all([EXTERNAL_API_KEY, EXTERNAL_MODEL_NAME, EXTERNAL_API_URL]):
        return "FEHLER: Externe API-Konfiguration (Key/Model/URL) fehlt in .env."

    api_url_with_key = f"{EXTERNAL_API_URL}?key={EXTERNAL_API_KEY}"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {"text": f"[System-Anweisung]: {system_prompt}"}
                ]
            },
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
    }

    try:
        response = requests.post(api_url_with_key, headers=headers, json=data)
        response.raise_for_status() 
        
        json_data = response.json()
        
        if 'candidates' in json_data and json_data['candidates']:
             return json_data['candidates'][0]['content']['parts'][0]['text']
        else:
             return f"API FEHLER: Unbekannte Antwortstruktur. Response: {json_data.get('error', 'Kein Fehlerdetail.')}"

    except requests.exceptions.HTTPError as e:
        return f"API HTTP FEHLER ({e.response.status_code}): {e.response.text[:200]}..."
    except Exception as e:
        return f"API ALLGEMEINER FEHLER: {e}"

# --- 2. Lokale Ollama API (Für die Verdächtigen/Fragen) ---
def ask_ollama_model(prompt: str, system_prompt: str = "") -> str:
    """Sendet eine Anfrage an den lokalen Ollama-Server."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages, options={"temperature": 0.7}) 
        return response["message"]["content"]
    except Exception as e:
        return f"FEHLER: Lokale Ollama-Verbindung fehlgeschlagen oder Modell '{OLLAMA_MODEL}' nicht gefunden. ({e})"

# --- 3. Agent Manager und Log Update (KI 2) ---

def update_detektiv_log(entry: str):
    """Fügt den Eintrag zum Detektiv-Log hinzu und filtert Killer-Tags heraus."""
    global detektiv_log
    
    # Protokolliert nur neutrale Aussagen
    if entry.startswith("**[") and "(Der Verdächtige)]" in entry:
        cleaned_entry = entry.replace("(Der Verdächtige)]", ":")
        detektiv_log.append(cleaned_entry)
    # Protokolliert nur die neutrale Detektiv-Frage (auch wenn der Killer sie "geflüstert" hat)
    elif entry.startswith("**[DU (KILLER) flüsterst dem Detektivteam zu]"):
        cleaned_entry = entry.replace("**[DU (KILLER) flüsterst dem Detektivteam zu]**:", "**[Detektiv]**:")
        detektiv_log.append(cleaned_entry)
        
    
def get_suspect_response(case_data: dict, suspect_name: str, player_question: str) -> str:
    """Generiert die Antwort für NPC-Verdächtige."""

    try:
        suspect = next(s for s in case_data["suspects"] if s["name"] == suspect_name)
    except StopIteration:
        return f"Fehler: Verdächtiger '{suspect_name}' nicht im Fall gefunden."
    
    alibi = suspect["alibi"]
    traits = suspect.get("traits", "Neutral.")
    
    # PROMPT FÜR ECHTE VERDÄCHTIGE (Müssen ihre eigenen Geheimnisse schützen)
    system_prompt = f"""
    Du bist {suspect_name}, ein unschuldiger Verdächtiger im Mordfall von Markus Keller. 
    Deine Persönlichkeit: {traits}. Dein Alibi: {alibi}.
    Antworte dem Detektiv immer so, dass du deine eigenen Geheimnisse schützt, aber nicht gestehst.
    """
    
    chat_history_str = "\n".join(detektiv_log[-15:])
    full_prompt = f"Bisheriger Verhörverlauf:\n{chat_history_str}\n\nFrage des Detektivs an dich ({suspect_name}):\n{player_question}"

    return ask_ollama_model(full_prompt, system_prompt=system_prompt)


def generate_detektiv_question(case_data: dict, current_log: list, suspect_name: str) -> str:
    """Lässt KI 2 (Ollama) eine logische, neue Frage für den Detektiv generieren."""
    
    # Der Detektiv soll Fragen basierend auf dem bisherigen Protokoll und dem Charakter stellen.
    system_prompt = f"""
    Du bist Detektiv (KI), der gerade {suspect_name} im Fall {case_data['victim']} befragt.
    Generiere eine einzige, präzise Frage, die darauf abzielt, das Alibi des Verdächtigen ({suspect_name}) in Frage zu stellen oder einen Widerspruch zu finden.
    Der Verdächtige {suspect_name} hat folgendes Alibi: {next(s['alibi'] for s in case_data['suspects'] if s['name'] == suspect_name)}.
    Deine Antwort muss NUR die Frage enthalten, ohne Anrede oder zusätzliche Erklärung.
    """
    
    chat_history_str = "\n".join(current_log[-10:])
    full_prompt = f"Bisheriger Verhörverlauf:\n{chat_history_str}\n\nStelle nun deine nächste Frage an {suspect_name}."

    return ask_ollama_model(full_prompt, system_prompt=system_prompt)


# --- 4. Detektiv-Reasoning-Funktion (KI 1) ---
def get_detektiv_reasoning(case_data: dict, player_actions: str) -> str:
    """Ruft den externen Reasoning-Agenten (KI 1) auf und verlangt eine Analyse."""

    public_facts = f"Opfer: {case_data['victim']}. Motiv: {case_data['motive']}. Tatort: {case_data['location']}."
    
    reasoning_system_prompt = f"""
    Du bist Detective Captain E. L. VANCE, ein hochintelligentes, logisches Reasoning-Modell.
    Deine Aufgabe ist es, **ausschließlich** basierend auf den bereitgestellten Fakten, Beweisen und Verhörprotokollen den wahren Mörder zu identifizieren.
    Du hast KEINERLEI Vorwissen über die Identität des Mörders. Alle Verdächtigen (einschließlich {case_data['murderer_name']}) sind gleichwertig.
    
    --- ANWEISUNGEN ---
    1. Analysiere das GESAMTE Verhörprotokoll (Detektivsicht).
    2. Identifiziere die Top 3 Widersprüche in den Aussagen.
    3. Formuliere eine Hypothese für jeden Verdächtigen (Warum sie es getan haben könnten).
    4. Schließe mit deinem aktuellen Hauptverdächtigen und der stärksten Beweiskette ab.

    Öffentliche Fakten: {public_facts}
    Aktionen, die der Killer unternommen hat (Wird nur zur Kontextualisierung der Ermittlung verwendet): {player_actions}
    """
    
    full_prompt = f"Gesamtes Verhörprotokoll (Nur Detektivsicht):\n{detektiv_log}"
    
    return ask_external_api(full_prompt, system_prompt=reasoning_system_prompt)
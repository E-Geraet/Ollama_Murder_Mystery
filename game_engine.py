# game_engine.py (V7.1: Claude API Support)

import ollama
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# --- KI-Konfiguration ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "ministral-3:3b")
EXTERNAL_API_KEY = os.getenv("EXTERNAL_API_KEY")
EXTERNAL_MODEL_NAME = os.getenv("EXTERNAL_MODEL_NAME")
EXTERNAL_API_TYPE = os.getenv("EXTERNAL_API_TYPE", "claude")  # "claude" oder "gemini"

# --- Globales Detektiv-Log (neutral, nur für Detektiv-KI) ---
detective_log = []


# ========================================
# 1. CLAUDE API (Detektiv)
# ========================================

def ask_claude(prompt: str, system_prompt: str) -> str:
    """Sendet eine Anfrage an die Claude API (Anthropic)."""
    
    if not EXTERNAL_API_KEY:
        return "FEHLER: Claude API Key fehlt in .env"

    api_url = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": EXTERNAL_API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": EXTERNAL_MODEL_NAME,
        "max_tokens": 2000,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        
        json_data = response.json()
        
        if 'content' in json_data and json_data['content']:
            return json_data['content'][0]['text']
        else:
            return f"CLAUDE FEHLER: Unbekannte Response-Struktur"

    except requests.exceptions.HTTPError as e:
        return f"CLAUDE HTTP FEHLER: {e.response.text[:200]}"
    except Exception as e:
        return f"CLAUDE FEHLER: {e}"


# ========================================
# 2. GEMINI API (Fallback)
# ========================================

def ask_gemini(prompt: str, system_prompt: str) -> str:
    """Sendet eine Anfrage an die Gemini API."""
    
    GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent")
    
    if not EXTERNAL_API_KEY:
        return "FEHLER: Gemini API Key fehlt in .env"

    api_url = f"{GEMINI_API_URL}?key={EXTERNAL_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "contents": [
            {"parts": [{"text": f"[System-Anweisung]: {system_prompt}"}]},
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        
        json_data = response.json()
        
        if 'candidates' in json_data and json_data['candidates']:
            return json_data['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"GEMINI FEHLER: Unbekannte Response-Struktur"

    except requests.exceptions.HTTPError as e:
        return f"GEMINI HTTP FEHLER: {e.response.text[:200]}"
    except Exception as e:
        return f"GEMINI FEHLER: {e}"


# ========================================
# 3. GROQ API (Schnell & Kostenlos)
# ========================================

def ask_groq(prompt: str, system_prompt: str) -> str:
    """Sendet eine Anfrage an die Groq API."""
    
    if not EXTERNAL_API_KEY:
        return "FEHLER: Groq API Key fehlt in .env"

    api_url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {EXTERNAL_API_KEY}"
    }
    
    data = {
        "model": EXTERNAL_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        
        json_data = response.json()
        
        if 'choices' in json_data and json_data['choices']:
            return json_data['choices'][0]['message']['content']
        else:
            return f"GROQ FEHLER: Unbekannte Response-Struktur"

    except requests.exceptions.HTTPError as e:
        return f"GROQ HTTP FEHLER: {e.response.text[:200]}"
    except Exception as e:
        return f"GROQ FEHLER: {e}"


# ========================================
# 4. UNIFIED EXTERNAL API CALL
# ========================================

def ask_external_api(prompt: str, system_prompt: str) -> str:
    """Ruft die konfigurierte externe API auf (Groq, Claude oder Gemini)."""
    
    if EXTERNAL_API_TYPE == "groq":
        return ask_groq(prompt, system_prompt)
    elif EXTERNAL_API_TYPE == "claude":
        return ask_claude(prompt, system_prompt)
    elif EXTERNAL_API_TYPE == "gemini":
        return ask_gemini(prompt, system_prompt)
    else:
        return f"FEHLER: Unbekannter EXTERNAL_API_TYPE: {EXTERNAL_API_TYPE}"


# ========================================
# 4. OLLAMA API (NPCs)
# ========================================

def ask_ollama(prompt: str, system_prompt: str = "") -> str:
    """Sendet eine Anfrage an den lokalen Ollama-Server."""
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL, 
            messages=messages, 
            options={"temperature": 0.7}
        )
        return response["message"]["content"]
    except Exception as e:
        return f"OLLAMA FEHLER: {e}"


# ========================================
# 5. DETEKTIV-LOG VERWALTUNG
# ========================================

def update_detective_log(entry: str):
    """Fuegt neutralen Eintrag zum detective_log hinzu."""
    global detective_log
    detective_log.append(entry)


def clear_detective_log():
    """Loescht das detective_log (fuer Spielstart)."""
    global detective_log
    detective_log = []


def get_detective_log():
    """Gibt das komplette detective_log zurueck."""
    return "\n".join(detective_log)


# ========================================
# 6. DETEKTIV-AKTION (Externe API)
# ========================================

def get_detective_action(case_data: dict) -> dict:
    """
    Detektiv-KI waehlt Verdaechtigen und stellt Frage (JSON-Response).
    
    Returns:
        {
            "success": True/False,
            "type": "question" / "accusation" / "error",
            "suspect": "Name",
            "question": "Frage",
            "accusation": "Name",
            "reason": "Begruendung",
            "raw_response": "Original-Text",
            "error": "Fehlermeldung"
        }
    """
    
    suspect_names = [s["name"] for s in case_data["suspects"]]
    
    system_prompt = f"""
Du bist Detective AI, ein brillanter Ermittler in einem Mordfall.

FALL-INFORMATIONEN:
- Opfer: {case_data['victim']}
- Tatort: {case_data['location']}
- Motiv: {case_data['motive']}

VERDAECHTIGE: {', '.join(suspect_names)}

DEINE AUFGABE:
1. Waehle EINEN Verdaechtigen zum Befragen
2. Stelle EINE praezise Frage, um Widerspruече aufzudecken
3. ODER klage jemanden an, wenn du dir absolut sicher bist

WICHTIG:
- Du kennst die Identitaet des Killers NICHT
- Alle Verdaechtigen sind gleichwertig verdaechtig
- Analysiere bisherige Aussagen auf Widerspruече

ANTWORT-FORMAT (NUR JSON, kein anderer Text):
Bei Befragung:
{{"suspect": "Name des Verdaechtigen", "question": "Deine Frage"}}

Bei Anklage:
{{"accusation": "Name des Verdaechtigen", "reason": "Deine Begruendung"}}
"""
    
    log_content = get_detective_log()
    prompt = f"Bisheriges Verhoer:\n{log_content if log_content else '[Noch keine Verhoere]'}\n\nDeine naechste Aktion:"
    
    raw_response = ask_external_api(prompt, system_prompt)
    
    # JSON extrahieren (falls in Markdown-Codeblock)
    json_str = raw_response.strip()
    if json_str.startswith("```json"):
        json_str = json_str.split("```json")[1].split("```")[0].strip()
    elif json_str.startswith("```"):
        json_str = json_str.split("```")[1].split("```")[0].strip()
    
    # JSON parsen
    try:
        data = json.loads(json_str)
        
        # Validierung: Befragung
        if "suspect" in data and "question" in data:
            suspect_name = data["suspect"]
            
            # Pruefen ob Verdaechtiger existiert
            if suspect_name not in suspect_names:
                return {
                    "success": False,
                    "type": "error",
                    "error": f"Ungueltiger Verdaechtiger: {suspect_name}",
                    "raw_response": raw_response
                }
            
            return {
                "success": True,
                "type": "question",
                "suspect": suspect_name,
                "question": data["question"],
                "raw_response": raw_response
            }
        
        # Validierung: Anklage
        elif "accusation" in data and "reason" in data:
            accused_name = data["accusation"]
            
            # Pruefen ob Verdaechtiger existiert
            if accused_name not in suspect_names:
                return {
                    "success": False,
                    "type": "error",
                    "error": f"Ungueltiger Verdaechtiger in Anklage: {accused_name}",
                    "raw_response": raw_response
                }
            
            return {
                "success": True,
                "type": "accusation",
                "accusation": accused_name,
                "reason": data["reason"],
                "raw_response": raw_response
            }
        
        else:
            return {
                "success": False,
                "type": "error",
                "error": "JSON enthaelt weder 'suspect'+'question' noch 'accusation'+'reason'",
                "raw_response": raw_response
            }
    
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "type": "error",
            "error": f"Ungueltiges JSON: {e}",
            "raw_response": raw_response
        }


# ========================================
# 7. NPC-ANTWORT (OLLAMA)
# ========================================

def get_npc_response(case_data: dict, suspect_name: str, question: str) -> str:
    """Generiert Antwort fuer unschuldige Verdaechtige via Ollama."""
    
    try:
        suspect = next(s for s in case_data["suspects"] if s["name"] == suspect_name)
    except StopIteration:
        return f"FEHLER: Verdaechtiger '{suspect_name}' nicht gefunden."
    
    alibi = suspect["alibi"]
    traits = suspect.get("traits", "Neutral")
    
    system_prompt = f"""
Du bist {suspect_name}, ein unschuldiger Verdaechtiger im Mordfall.

DEINE INFORMATIONEN:
- Persoenlichkeit: {traits}
- Dein Alibi: {alibi}

REGELN:
- Du bist UNSCHULDIG und sagst die Wahrheit (basierend auf deinem Alibi)
- Antworte glaubwuerdig und deinem Charakter entsprechend
- Bleibe bei deiner Geschichte, auch unter Druck
"""
    
    log_content = get_detective_log()
    prompt = f"Bisheriges Verhoer:\n{log_content}\n\nFrage des Detektivs an dich:\n{question}\n\nDeine Antwort:"
    
    return ask_ollama(prompt, system_prompt)


# ========================================
# 8. DETEKTIV-POWER (REASONING-ANALYSE)
# ========================================

def get_detective_reasoning(case_data: dict) -> str:
    """Detektiv-KI analysiert den Fall (Detektiv-Power)."""
    
    suspect_names = [s["name"] for s in case_data["suspects"]]
    
    system_prompt = f"""
Du bist Detective Captain E. L. VANCE, ein hochintelligentes Reasoning-Modell.

FALL-INFORMATIONEN:
- Opfer: {case_data['victim']}
- Tatort: {case_data['location']}
- Motiv: {case_data['motive']}
- Verdaechtige: {', '.join(suspect_names)}

DEINE AUFGABE:
Analysiere das bisherige Verhoerprotokoll und gib eine strukturierte Analyse:

1. Top 3 Widerspruече: Welche Aussagen passen nicht zusammen?
2. Verdaechtigkeits-Ranking: Wer ist am verdaechtigsten und warum?
3. Naechste Schritte: Welche Fragen sollten noch gestellt werden?
4. Haupt-Verdaechtiger: Wer ist dein aktueller Top-Verdaechtiger?

WICHTIG:
- Du kennst die Identitaet des Killers NICHT
- Alle Verdaechtigen sind gleichwertig (keine Vorurteile)
- Basiere deine Analyse NUR auf den Fakten im Protokoll
"""
    
    log_content = get_detective_log()
    prompt = f"Verhoer-Protokoll:\n{log_content if log_content else '[Noch keine Verhoere]'}\n\nDeine Analyse:"
    
    return ask_external_api(prompt, system_prompt)
import ollama
import json
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()
MODEL = os.getenv("OLLAMA_MODEL", "mistral-3:3b") 

# Ollama API Wrapper
def ask_model(prompt: str, system_prompt: str = "") -> str:
    """Sendet eine Anfrage an den Ollama-Server."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
        
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = ollama.chat(
            model=MODEL, 
            messages=messages,
            options={"temperature": 0.7} # Für konsistente, aber lebendige Antworten
        )
        return response["message"]["content"]
    except Exception as e:
        return f"FEHLER: Verbindung zu Ollama fehlgeschlagen oder Modell '{MODEL}' nicht gefunden. ({e})"


# Rollen-Prompts
ROLE_PROMPTS = {
    "detective": "Du bist ein professioneller, analytischer Detektiv.",
    "murderer": "Du bist der Täter. Dein Ziel ist es, den Verdacht erfolgreich abzulenken und zu lügen.",
    "innocent": "Du bist unschuldig und hast nichts zu verbergen. Dein Ziel ist es, die Wahrheit zu sagen."
}


# Agent Manager
def get_agent_response(case_data: dict, suspect_name: str, player_question: str, conversation_history: list) -> str:
    """Formuliert den finalen Prompt und befragt den spezifischen Agenten."""
    
    # 1. Finde den Verdächtigen und seine Daten
    try:
        suspect = next(s for s in case_data["suspects"] if s["name"] == suspect_name)
    except StopIteration:
        return f"Fehler: Verdächtiger '{suspect_name}' nicht im Fall gefunden."

    role = suspect["role"]
    alibi = suspect["alibi"]
    traits = suspect.get("traits", "Neutral.")
    
    # 2. Setze den System-Prompt (Die Rolle)
    base_role_prompt = ROLE_PROMPTS[role]
    
    # 3. Spezifische Anweisungen und Kontext für den Agenten
    system_prompt = f"""
    {base_role_prompt}
    
    --- DEINE ROLLE ---
    Dein Name: {suspect_name}. 
    Deine Persönlichkeit: {traits}
    Dein Alibi (wahr oder gelogen): {alibi}
    
    --- FALLKONTEXT ---
    Opfer: {case_data['victim']}, Tatort: {case_data['location']}, Motiv: {case_data['motive']}.
    
    --- ANWEISUNG ---
    Beantworte die Detektiv-Frage basierend auf deiner Rolle und deinem Alibi. 
    Lüge als Mörder, aber verstricke dich nicht. Sei ehrlich als Unschuldiger. Bleibe deinem Charakterzug treu.
    """
    
    # 4. Den bisherigen Chat-Verlauf hinzufügen (Wichtig für Memory)
    chat_history_str = "\n".join(conversation_history[-10:]) # Nur die letzten 10 Einträge als "Kurzzeitgedächtnis"
    
    # 5. Die aktuelle Frage
    full_prompt = f"Bisherige Ermittlung: \n{chat_history_str}\n\n**Deine Antwort auf die aktuelle Detektiv-Frage:**\n{player_question}"

    # 6. Ollama aufrufen
    return ask_model(full_prompt, system_prompt=system_prompt)

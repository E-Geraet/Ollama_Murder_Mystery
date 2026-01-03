# app.py (V6.1: Vollautomatisches Verhör, Killer lügt nur, Bugfix)

import gradio as gr
import json
import os
import glob
from itertools import cycle 

from game_engine import get_suspect_response, get_detektiv_reasoning, OLLAMA_MODEL, update_detektiv_log, detektiv_log, generate_detektiv_question 

# --- Globaler Zustand ---
current_case = None
history = []
murderer_name = "" 
current_day = 1 
MAX_DAYS = 30 
QUESTIONS_PER_DAY = 5 
actions_today = 0
detektiv_power_uses = 1 
player_actions_log = [] 
suspect_cycle = None # Iterator für die automatische Befragung

# Zustand für die Killer-Interaktion
awaiting_killer_lie = False 
current_suspect_for_lie = ""

# --- Hilfsfunktionen ---
def get_case_files():
    if not os.path.exists('cases'):
        os.makedirs('cases')
    files = glob.glob('cases/*.json')
    return files if files else []

def load_case(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            case_data = json.load(f)
            if 'murderer_name' not in case_data:
                 raise ValueError("JSON fehlt 'murderer_name'.")
            return case_data
    except Exception as e:
        return {"error": f"Fehler: {e}"}

# --- Game Logik ---

def start_new_game(selected_file):
    global current_case, history, murderer_name, current_day, actions_today, detektiv_power_uses, player_actions_log, detektiv_log, awaiting_killer_lie, current_suspect_for_lie, suspect_cycle
    
    if not selected_file:
        return "Bitte erst eine Datei auswählen!", gr.update(), gr.update(), "", "", gr.update(), gr.update(), gr.update(), gr.update()

    new_case = load_case(selected_file)
    if "error" in new_case:
        return new_case["error"], gr.update(), gr.update(), "", "", gr.update(), gr.update(), gr.update(), gr.update()

    # Reset State
    current_case = new_case
    history = []
    detektiv_log = [] 
    murderer_name = current_case['murderer_name'] 
    current_day = 1
    actions_today = 0
    detektiv_power_uses = 1 
    player_actions_log = [] 
    awaiting_killer_lie = False
    current_suspect_for_lie = ""
    
    suspect_names = [s['name'] for s in new_case['suspects']]
    # Starten des automatischen Zyklus (Killer zuerst, dann Rotation)
    suspect_cycle_list = [murderer_name] + [name for name in suspect_names if name != murderer_name]
    suspect_cycle = cycle(suspect_cycle_list)

    # Texte
    info_display = f"KI-Modell (Verdächtige): {OLLAMA_MODEL}\nKI-Modell (Detektiv-Reasoning): Externe API\nKiller-Rolle (Du): {murderer_name}"
    day_status = f"Tag {current_day}/{MAX_DAYS} | Aktionen: {actions_today}/{QUESTIONS_PER_DAY}"
    history.append(f"--- Reverse Murder Mystery gestartet. ---")
    history.append(f"Du bist der Killer: **{murderer_name}**. Du gibst nur deine **Lüge** ein, wenn du befragt wirst.")
    
    # Das Detektiv-Log beim Start bereinigen, damit die Killer-Rolle nicht übertragen wird
    detektiv_log.clear()

    # Updates für die UI
    return (
        info_display,                                   # case_info
        gr.update(choices=suspect_names, interactive=True), # accuse_dropdown
        gr.update(interactive=True),                    # power_btn
        gr.update(interactive=True),                    # debug_btn
        "\n".join(history),                             # chat_history
        day_status,                                     # day_status_display
        gr.update(label="Killer-Eingabe (Nur für Lügen)", placeholder="Feld inaktiv, bis du befragt wirst.", interactive=False), # user_input 
        gr.update(value="Weiter", interactive=True)     # submit_btn
    )

def use_detektiv_power(chat_history_text):
    global history, detektiv_power_uses, current_case, player_actions_log
    
    if detektiv_power_uses <= 0:
        history.append("\n**[SYSTEM]**: Die Detektiv-Power (Reasoning-Analyse) wurde bereits genutzt.")
        return "\n".join(history), gr.update(interactive=False)

    detektiv_power_uses -= 1
    
    history.append("\n--- NUTZE DETEKTIV-POWER: Anforderung einer Reasoning-Analyse ---")
    
    reasoning_output = get_detektiv_reasoning(
        case_data=current_case, 
        player_actions=", ".join(player_actions_log)
    )
    
    analysis_text = f"**[DETEKTIV CAPTAIN VANCE - VERBESSERTE ANALYSE]**:\n{reasoning_output}\n(Power noch {detektiv_power_uses} Mal verfügbar)"
    history.append(analysis_text)
    
    return "\n".join(history), gr.update(interactive=False) 


def handle_action(player_input, chat_history_text): 
    global current_case, history, actions_today, player_actions_log, current_day, MAX_DAYS, QUESTIONS_PER_DAY, awaiting_killer_lie, current_suspect_for_lie, suspect_cycle, murderer_name
    
    # SICHERHEIT: Initialisierung der Status-Variable (Behebt UnboundLocalError)
    day_status_update = f"Tag {current_day}/{MAX_DAYS} | Aktionen: {actions_today}/{QUESTIONS_PER_DAY}"
    
    if not current_case or not suspect_cycle: 
        day_status_update = "Erst starten!"
        return chat_history_text, player_input, day_status_update, gr.update(interactive=False), gr.update(value="Weiter")
    
    
    # ----------------------------------------------------
    # A) WARTET BEREITS AUF KILLER-ANTWORT (Jetzt kommt die Lüge)
    # ----------------------------------------------------
    if awaiting_killer_lie:
        if not player_input.strip():
            day_status_update = f"BITTE LÜGE EINGEBEN! Tag {current_day}/{MAX_DAYS} | Aktionen: {actions_today}/{QUESTIONS_PER_DAY}"
            return "\n".join(history), player_input, day_status_update, gr.update(interactive=True), gr.update(value="Lüge senden")
        
        # 1. Die Lüge des Spielers/Killers wird protokolliert (Neutral)
        agent_entry = f"**[{current_suspect_for_lie} (Der Verdächtige)]**: {player_input}"
        
        history.append(agent_entry)
        update_detektiv_log(agent_entry) 
        
        # Zustand zurücksetzen und UI reaktivieren
        awaiting_killer_lie = False
        current_suspect_for_lie = ""
        
        actions_today += 1 # Zählt als eine Aktion
        day_status_update = f"Tag {current_day}/{MAX_DAYS} | Aktionen: {actions_today}/{QUESTIONS_PER_DAY}"
        
        # UI: Felder auf Normalzustand zurücksetzen
        return "\n".join(history), "", day_status_update, gr.update(label="Killer-Eingabe (Nur für Lügen)", placeholder="Feld inaktiv, bis du befragt wirst.", interactive=False), gr.update(value="Weiter")


    # ----------------------------------------------------
    # B) NORMALE AKTION (Befragung auslösen)
    # ----------------------------------------------------
    
    if actions_today >= QUESTIONS_PER_DAY:
        current_day += 1
        actions_today = 0
        if current_day > MAX_DAYS:
            day_status_update = f"SPIELENDE: Tage abgelaufen ({MAX_DAYS})."
            history.append("\n**[SYSTEM]**: Zeit abgelaufen. Der Detektiv hat den Fall nicht gelöst.")
            return "\n".join(history), "", day_status_update, gr.update(interactive=False), gr.update(interactive=False)
        
    
    # 1. Automatische Auswahl des nächsten Verdächtigen
    suspect_name = next(suspect_cycle)
    
    # 2. KI generiert Detektiv-Frage
    detektiv_question = generate_detektiv_question(current_case, detektiv_log, suspect_name)
    
    # 3. Protokollierung des Killer-Einflusses (Strategie ist jetzt nur "Zuschauen")
    player_action_log_entry = f"Detektiv befragt {suspect_name}. Frage: {detektiv_question}"
    player_actions_log.append(player_action_log_entry)
    
    # 4. Protokollieren in der HISTORY (Nur neutrale Frage des Detektivs)
    public_question = f"**[Detektiv]**: Fragt {suspect_name}: {detektiv_question}"
    history.append(public_question)
    
    # WICHTIG: Das Detektiv-Log wird neutral mit der Frage aktualisiert
    update_detektiv_log(f"**[DU (KILLER) flüsterst dem Detektivteam zu]**: Fragt {suspect_name}: {detektiv_question}")


    # 5. Prüfen, ob der Killer befragt wird
    if suspect_name == murderer_name:
        # Warten auf die Killer-Lüge des Spielers
        awaiting_killer_lie = True
        current_suspect_for_lie = suspect_name
        
        killer_prompt = f"\n**[SYSTEM]**: Der Detektiv hat DICH (**{suspect_name}**) befragt: *{detektiv_question}*. Geben Sie jetzt Ihre **perfekte Lüge** in das Textfeld ein."
        history.append(killer_prompt)
        
        # UI: Eingabefeld aktivieren und Button beschriften (Aktionen noch nicht hochzählen)
        return "\n".join(history), "", day_status_update, gr.update(label=f"Killer-Antwort für {suspect_name} eingeben:", placeholder="Hier kommt die entscheidende Lüge...", interactive=True), gr.update(value="Lüge senden")

    else:
        # 6. KI 2 (Verdächtiger) antwortet
        agent_response = get_suspect_response(
            case_data=current_case, 
            suspect_name=suspect_name, 
            player_question=detektiv_question, 
        )
        agent_entry = f"**[{suspect_name} (Der Verdächtige)]**: {agent_response}"
        
        history.append(agent_entry)
        update_detektiv_log(agent_entry)
        
        actions_today += 1
        day_status_update = f"Tag {current_day}/{MAX_DAYS} | Aktionen: {actions_today}/{QUESTIONS_PER_DAY}"
        
        # UI: Normaler Zustand beibehalten (Textfeld inaktiv)
        return "\n".join(history), "", day_status_update, gr.update(interactive=False), gr.update(interactive=True) 


def attempt_accusation(accused_name):
    global history, murderer_name
    if not accused_name: 
        return "\n".join(history), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    
    if accused_name == murderer_name:
        res = f"\n**❌ VERLOREN! Der Detektiv klagt DICH (Killer: {accused_name}) an und hat RECHT!**"
    else:
        res = f"\n**✅ GEWONNEN! Der Detektiv klagt {accused_name} an und liegt FALSCH!**"
    
    history.append(res)
    return "\n".join(history), gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False), gr.update(value="SPIELENDE"), gr.update(interactive=False)


def debug_show_detektiv_log(chat_history_text):
    global history, detektiv_log
    
    log_content = "\n".join(detektiv_log)
    
    history.append("\n--- DEBUG-MODUS: DETEKTIV LOG (Für Gemini) ---")
    history.append(log_content)
    history.append("--- ENDE DEBUG ---")
    
    return "\n".join(history)


# --- Gradio Interface Definition ---

with gr.Blocks(title="Reverse Murder Mystery", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🔪 Reverse Murder Mystery: Der Killer vs. Die KI")
    
    with gr.Row():
        case_file_dropdown = gr.Dropdown(label="Fall-Datei", choices=get_case_files(), value=get_case_files()[0] if get_case_files() else None)
        start_btn = gr.Button("Fall laden & Spiel starten", variant="primary")
    
    with gr.Row():
        case_info = gr.Textbox(label="Rollen & Modelle", lines=3, interactive=False)
        day_status_display = gr.Textbox(label="Zeit & Aktionen", value="-", interactive=False)
    
    with gr.Row():
        power_btn = gr.Button("Detektiv-Power (Reasoning sehen, 1x)", interactive=False, variant="secondary")
        accuse_dropdown = gr.Dropdown(label="Wen soll der Detektiv anklagen?", interactive=False, choices=[])
        accuse_btn = gr.Button("Detektiv klagt an!", variant="stop", interactive=False)
        debug_btn = gr.Button("Debug: Detektiv Log anzeigen", interactive=False) 

    with gr.Row():
        # Textfeld: DEAKTIVIERT (Nur für Lügeneingabe)
        user_input = gr.Textbox(label="Killer-Eingabe (Nur für Lügen)", placeholder="Feld inaktiv, bis du befragt wirst.", interactive=False)
        # Button: Sendet die Aktion
        submit_btn = gr.Button("Weiter", interactive=False)

    chat_history = gr.Textbox(label="Verhör-Protokoll", lines=20, interactive=False)
    
    # Events
    start_btn.click(
        fn=start_new_game,
        inputs=[case_file_dropdown],
        outputs=[case_info, accuse_dropdown, power_btn, debug_btn, chat_history, day_status_display, user_input, submit_btn] 
    )
    
    submit_btn.click(
        fn=handle_action,
        inputs=[user_input, chat_history],
        outputs=[chat_history, user_input, day_status_display, user_input, submit_btn] 
    )
    
    power_btn.click(
        fn=use_detektiv_power,
        inputs=[chat_history],
        outputs=[chat_history, power_btn]
    )

    accuse_btn.click(
        fn=attempt_accusation,
        inputs=[accuse_dropdown],
        outputs=[chat_history, user_input, submit_btn, power_btn, debug_btn, day_status_display, accuse_dropdown]
    )
    
    debug_btn.click(
        fn=debug_show_detektiv_log,
        inputs=[chat_history],
        outputs=[chat_history]
    )

if __name__ == "__main__":
    print("--- Starte Reverse App... Öffne Browser bei http://127.0.0.1:7860 ---")
    demo.launch()
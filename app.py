import gradio as gr
import json
import os
import glob
from game_engine import get_agent_response, MODEL

# Globaler Zustand
current_case = None
history = []
murderer_name = ""
current_day = 1 
MAX_DAYS = 30 
QUESTIONS_PER_DAY = 5 
actions_today = 0
dns_uses_left = 3 

# Hilfsfunktionen
def get_case_files():
    if not os.path.exists('cases'):
        os.makedirs('cases')
    files = glob.glob('cases/*.json')
    return files if files else []

def load_case(file_path):
    print(f"DEBUG: Versuche Datei zu laden: {file_path}") # DEBUG
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            case_data = json.load(f)
            # Validierung
            if 'murderer_name' not in case_data:
                 raise ValueError("JSON fehlt 'murderer_name'.")
            print("DEBUG: Fall erfolgreich geladen.") # DEBUG
            return case_data
    except Exception as e:
        print(f"DEBUG: Fehler beim Laden: {e}") # DEBUG
        return {"error": f"Fehler: {e}"}

# Game Logik

def start_new_game(selected_file):
    global current_case, history, murderer_name, current_day, actions_today, dns_uses_left
    
    if not selected_file:
        return "Bitte erst eine Datei auswählen!", gr.update(), gr.update(), "", "", gr.update(), gr.update(), gr.update()

    new_case = load_case(selected_file)
    if "error" in new_case:
        return new_case["error"], gr.update(), gr.update(), "", "", gr.update(), gr.update(), gr.update()

    # Reset State
    current_case = new_case
    history = []
    murderer_name = current_case['murderer_name']
    current_day = 1
    actions_today = 0
    dns_uses_left = 3
    
    # Listen erstellen
    suspect_names = [s['name'] for s in new_case['suspects']]
    print(f"DEBUG: Gefundene Verdächtige: {suspect_names}") # DEBUG - Hier sehen wir im Terminal, ob die Liste voll ist

    # Texte
    info_display = f"Modell: {MODEL}\nFall: {current_case['title']}\nOpfer: {new_case['victim']}"
    day_status = f"Tag {current_day}/{MAX_DAYS}"
    history.append(f"--- Fall geladen. {len(suspect_names)} Verdächtige gefunden. ---")


    return (
        info_display,                                   # case_info
        gr.update(choices=suspect_names, value=suspect_names[0] if suspect_names else None, interactive=True), # suspect_dropdown
        gr.update(choices=suspect_names, interactive=True), # accuse_dropdown
        "\n".join(history),                             # chat_history
        day_status,                                     # day_status_display
        gr.update(interactive=True),                    # user_input
        gr.update(interactive=True),                    # submit_btn
        gr.update(interactive=True)                     # accuse_btn
    )

def handle_detection(player_input, suspect_name, chat_history_text):
    global current_case, history, actions_today
    if not current_case: return chat_history_text, player_input, "Erst starten!", gr.update()
    
    # Leere Eingabe
    if not player_input.strip():
        return chat_history_text, "", "Bitte Frage eingeben.", gr.update()

    print(f"DEBUG: Frage an {suspect_name}: {player_input}") # DEBUG

    # Agenten Antwort
    try:
        agent_response = get_agent_response(current_case, suspect_name, player_input, history)
    except Exception as e:
        agent_response = f"(Systemfehler bei KI-Antwort: {e})"
        print(f"DEBUG ERROR: {e}")

    history.append(f"**[Du fragst {suspect_name}]**: {player_input}")
    history.append(f"**[{suspect_name}]**: {agent_response}")
    
    actions_today += 1
    day_status = f"Tag {current_day}/{MAX_DAYS} | Aktionen: {actions_today}/{QUESTIONS_PER_DAY}"
    
    return "\n".join(history), "", day_status, day_status

def attempt_accusation(accused_name):
    global history
    if not accused_name: return "\n".join(history), gr.update(), gr.update(), gr.update()
    
    if accused_name == murderer_name:
        res = f"\n**✅ GEWONNEN! {accused_name} war der Täter!**"
    else:
        res = f"\n**❌ FALSCH! {accused_name} ist unschuldig.**"
    
    history.append(res)
    return "\n".join(history), gr.update(interactive=False), gr.update(interactive=False), gr.update(value="SPIELENDE")

# --- GUI Aufbau ---
with gr.Blocks(title="Murder Mystery V2") as demo:
    gr.Markdown("# 🕵️ Ollama Detective")
    
    with gr.Row():
        case_file_dropdown = gr.Dropdown(label="Fall-Datei", choices=get_case_files(), value=get_case_files()[0] if get_case_files() else None)
        start_btn = gr.Button("Fall laden & Spiel starten", variant="primary")
    
    with gr.Row():
        # Die Dropdowns
        suspect_dropdown = gr.Dropdown(label="Wen befragen?", choices=[], interactive=False)
        accuse_dropdown = gr.Dropdown(label="Wen anklagen?", choices=[], interactive=False)
        accuse_btn = gr.Button("Anklagen", variant="stop", interactive=False)

    case_info = gr.Textbox(label="Akte", lines=4, interactive=False)
    day_status_display = gr.Textbox(label="Zeit", value="-", interactive=False)
    
    chat_history = gr.Textbox(label="Protokoll", lines=15, interactive=False)
    
    with gr.Row():
        user_input = gr.Textbox(label="Deine Frage", placeholder="...", interactive=False)
        submit_btn = gr.Button("Senden", interactive=False)

    # Events
    start_btn.click(
        fn=start_new_game,
        inputs=[case_file_dropdown],
        outputs=[case_info, suspect_dropdown, accuse_dropdown, chat_history, day_status_display, user_input, submit_btn, accuse_btn]
    )
    
    submit_btn.click(
        fn=handle_detection,
        inputs=[user_input, suspect_dropdown, chat_history],
        outputs=[chat_history, user_input, day_status_display, day_status_display]
    )
    
    accuse_btn.click(
        fn=attempt_accusation,
        inputs=[accuse_dropdown],
        outputs=[chat_history, user_input, submit_btn, day_status_display]
    )


if __name__ == "__main__":
    print("--- Starte App... Öffne Browser bei http://127.0.0.1:7860 ---")
    

    demo.launch(
    
        theme=gr.themes.Soft(), 

    )
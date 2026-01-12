# app.py (V7.0: Komplett neu - Gemini als Detektiv)

import gradio as gr
import json
import os
import glob

from game_engine import (
    get_detective_action,
    get_npc_response,
    get_detective_reasoning,
    update_detective_log,
    clear_detective_log,
    get_detective_log,
    OLLAMA_MODEL,
    EXTERNAL_MODEL_NAME,
    EXTERNAL_API_TYPE
)

# ========================================
# GLOBALER SPIEL-ZUSTAND
# ========================================

current_case = None
history = []  # Vollständiges Protokoll (für UI)
murderer_name = ""
current_day = 1
MAX_DAYS = 30
QUESTIONS_PER_DAY = 5
actions_today = 0
detective_power_uses = 1
game_over = False

# Killer-Befragungs-Zustand
awaiting_killer_response = False
current_question = ""


# ========================================
# HILFSFUNKTIONEN
# ========================================

def get_case_files():
    """Gibt Liste aller Case-Dateien zurück."""
    if not os.path.exists('cases'):
        os.makedirs('cases')
    files = glob.glob('cases/*.json')
    return files if files else []


def load_case(file_path):
    """Lädt Case-Datei."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            case_data = json.load(f)
            if 'murderer_name' not in case_data:
                raise ValueError("JSON fehlt 'murderer_name'")
            return case_data
    except Exception as e:
        return {"error": f"Fehler beim Laden: {e}"}


# ========================================
# SPIEL-LOGIK
# ========================================

def start_new_game(selected_file):
    """Initialisiert neues Spiel."""
    global current_case, history, murderer_name, current_day, actions_today
    global detective_power_uses, game_over, awaiting_killer_response, current_question
    
    if not selected_file:
        return (
            "⚠️ Bitte erst eine Case-Datei auswählen!",
            gr.update(),
            gr.update(),
            gr.update(),
            "",
            "",
            gr.update(interactive=False),
            gr.update(interactive=False)
        )
    
    new_case = load_case(selected_file)
    if "error" in new_case:
        return (
            new_case["error"],
            gr.update(),
            gr.update(),
            gr.update(),
            "",
            "",
            gr.update(interactive=False),
            gr.update(interactive=False)
        )
    
    # Zustand zurücksetzen
    current_case = new_case
    history = []
    clear_detective_log()
    murderer_name = current_case['murderer_name']
    current_day = 1
    actions_today = 0
    detective_power_uses = 1
    game_over = False
    awaiting_killer_response = False
    current_question = ""
    
    # UI-Texte
    case_info = f"""**FALL GELADEN**
    
Opfer: {current_case['victim']}
Tatort: {current_case['location']}
Motiv: {current_case['motive']}

**DEINE ROLLE: {murderer_name}**
Du bist der Killer! Luege ueberzeugend, wenn du befragt wirst.

KI-Modelle:
- Detektiv ({EXTERNAL_API_TYPE.upper()}): {EXTERNAL_MODEL_NAME}
- NPCs (Ollama): {OLLAMA_MODEL}
"""
    
    day_status = f"Tag {current_day}/{MAX_DAYS} | Fragen heute: {actions_today}/{QUESTIONS_PER_DAY}"
    
    history.append("═" * 60)
    history.append("🔪 REVERSE MURDER MYSTERY 🔪")
    history.append("═" * 60)
    history.append(f"\n**DU BIST DER KILLER: {murderer_name}**")
    history.append("Deine Aufgabe: Lüge überzeugend und komm davon!")
    history.append("\nKlicke auf 'Gemini, befrage jemanden' um das Verhör zu starten.\n")
    
    return (
        case_info,
        gr.update(interactive=True),   # detective_btn
        gr.update(interactive=True),   # power_btn
        gr.update(interactive=True),   # debug_btn
        "\n".join(history),
        day_status,
        gr.update(interactive=False, placeholder="Wartet auf deine Befragung..."),  # killer_input
        gr.update(interactive=False)   # killer_submit_btn
    )


def handle_detective_action():
    """Gemini befragt einen Verdächtigen."""
    global current_case, history, actions_today, current_day, game_over
    global awaiting_killer_response, current_question
    
    if not current_case:
        return (
            "\n".join(history),
            f"Tag {current_day}/{MAX_DAYS} | Fragen heute: {actions_today}/{QUESTIONS_PER_DAY}",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=True)
        )
    
    if game_over:
        return (
            "\n".join(history),
            "SPIEL BEENDET",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False)
        )
    
    # Tages-Limit prüfen
    if actions_today >= QUESTIONS_PER_DAY:
        current_day += 1
        actions_today = 0
        
        if current_day > MAX_DAYS:
            game_over = True
            history.append("\n" + "═" * 60)
            history.append("⏰ ZEIT ABGELAUFEN! ⏰")
            history.append("═" * 60)
            history.append(f"\n✅ **GEWONNEN!** Der Detektiv hat dich ({murderer_name}) nicht überführt!")
            history.append("Du bist ein Meister der Täuschung! 🎭")
            
            return (
                "\n".join(history),
                "SPIEL BEENDET",
                gr.update(interactive=False),
                gr.update(interactive=False),
                gr.update(interactive=False)
            )
        
        history.append(f"\n--- Tag {current_day} ---")
    
    # Gemini aufrufen
    history.append("\n🔍 **Detektiv Gemini denkt nach...**")
    
    result = get_detective_action(current_case)
    
    # FEHLER: Ungültiges JSON
    if not result["success"]:
        history.append(f"\n⚠️ **[DEBUG]** Gemini-Fehler: {result['error']}")
        history.append(f"Raw Response: {result['raw_response'][:200]}...")
        history.append("\n➡️ Sende Fehler zurück an Gemini...")
        
        # TODO: Hier könnte man Gemini nochmal mit Fehlerhinweis aufrufen
        # Für jetzt: Einfach Fehler anzeigen
        
        return (
            "\n".join(history),
            f"Tag {current_day}/{MAX_DAYS} | Fragen heute: {actions_today}/{QUESTIONS_PER_DAY}",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=True)
        )
    
    # ANKLAGE
    if result["type"] == "accusation":
        accused = result["accusation"]
        reason = result["reason"]
        
        history.append("\n" + "═" * 60)
        history.append("⚖️ ANKLAGE! ⚖️")
        history.append("═" * 60)
        history.append(f"\n**Detektiv Gemini klagt an: {accused}**")
        history.append(f"Begründung: {reason}")
        
        # Protokollieren
        update_detective_log(f"**[Detektiv]**: Ich klage {accused} des Mordes an. Begründung: {reason}")
        
        # Prüfen ob richtig
        if accused == murderer_name:
            history.append(f"\n❌ **VERLOREN!** Du ({murderer_name}) wurdest überführt!")
            history.append("Der Detektiv hat dich durchschaut! 🕵️")
        else:
            history.append(f"\n✅ **GEWONNEN!** Der Detektiv liegt falsch!")
            history.append(f"Du ({murderer_name}) kommst davon! 🎭")
        
        game_over = True
        
        return (
            "\n".join(history),
            "SPIEL BEENDET",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False)
        )
    
    # BEFRAGUNG
    suspect_name = result["suspect"]
    question = result["question"]
    
    history.append(f"\n**[Detektiv Gemini]**: Ich befrage **{suspect_name}**")
    history.append(f"**Frage**: {question}")
    
    # Protokollieren (neutral)
    update_detective_log(f"**[Detektiv]**: Fragt {suspect_name}: {question}")
    
    actions_today += 1
    
    # KILLER BEFRAGT?
    if suspect_name == murderer_name:
        awaiting_killer_response = True
        current_question = question
        
        history.append(f"\n🎯 **DU WIRST BEFRAGT!**")
        history.append("Gib jetzt deine Lüge ins Textfeld ein und klicke 'Lüge senden'.")
        
        day_status = f"Tag {current_day}/{MAX_DAYS} | Fragen heute: {actions_today}/{QUESTIONS_PER_DAY}"
        
        return (
            "\n".join(history),
            day_status,
            gr.update(interactive=True, placeholder="Schreibe deine perfekte Lüge..."),  # killer_input
            gr.update(interactive=True),   # killer_submit_btn
            gr.update(interactive=False)   # detective_btn
        )
    
    # NPC BEFRAGT
    else:
        history.append(f"\n💬 **{suspect_name} antwortet...**")
        
        npc_answer = get_npc_response(current_case, suspect_name, question)
        
        history.append(f"**[{suspect_name}]**: {npc_answer}")
        
        # Protokollieren (neutral)
        update_detective_log(f"**[{suspect_name}]**: {npc_answer}")
        
        day_status = f"Tag {current_day}/{MAX_DAYS} | Fragen heute: {actions_today}/{QUESTIONS_PER_DAY}"
        
        return (
            "\n".join(history),
            day_status,
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=True)
        )


def handle_killer_response(killer_answer):
    """Spieler gibt Lüge ein."""
    global history, awaiting_killer_response, current_question
    
    if not awaiting_killer_response:
        return (
            "\n".join(history),
            gr.update(),
            "",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=True)
        )
    
    if not killer_answer.strip():
        history.append("\n⚠️ Bitte gib eine Antwort ein!")
        return (
            "\n".join(history),
            f"Tag {current_day}/{MAX_DAYS} | Fragen heute: {actions_today}/{QUESTIONS_PER_DAY}",
            killer_answer,
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=False)
        )
    
    # Protokollieren
    history.append(f"**[{murderer_name}]**: {killer_answer}")
    
    # Neutral ins detective_log
    update_detective_log(f"**[{murderer_name}]**: {killer_answer}")
    
    # Zustand zurücksetzen
    awaiting_killer_response = False
    current_question = ""
    
    day_status = f"Tag {current_day}/{MAX_DAYS} | Fragen heute: {actions_today}/{QUESTIONS_PER_DAY}"
    
    return (
        "\n".join(history),
        day_status,
        "",  # Textfeld leeren
        gr.update(interactive=False, placeholder="Wartet auf deine Befragung..."),
        gr.update(interactive=False),
        gr.update(interactive=True)
    )


def use_detective_power():
    """Detektiv-Power: Reasoning-Analyse."""
    global history, detective_power_uses
    
    if detective_power_uses <= 0:
        history.append("\n⚠️ Detektiv-Power bereits genutzt!")
        return "\n".join(history), gr.update(interactive=False)
    
    detective_power_uses -= 1
    
    history.append("\n" + "─" * 60)
    history.append("🧠 **DETEKTIV-POWER: REASONING-ANALYSE**")
    history.append("─" * 60)
    
    analysis = get_detective_reasoning(current_case)
    
    history.append(f"\n{analysis}")
    history.append("\n" + "─" * 60)
    
    return "\n".join(history), gr.update(interactive=False)


def debug_show_log():
    """Debug: Zeigt das neutrale detective_log."""
    global history
    
    log_content = get_detective_log()
    
    history.append("\n" + "═" * 60)
    history.append("🐛 DEBUG: DETECTIVE_LOG (Was Gemini sieht)")
    history.append("═" * 60)
    history.append(log_content if log_content else "[Leer]")
    history.append("═" * 60)
    
    return "\n".join(history)


# ========================================
# GRADIO INTERFACE
# ========================================

with gr.Blocks(title="Reverse Murder Mystery", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🔪 Reverse Murder Mystery: Der Killer vs. Die KI")
    gr.Markdown("Du bist der Killer! Lüge überzeugend und komm davon.")
    
    with gr.Row():
        case_file_dropdown = gr.Dropdown(
            label="Case-Datei auswählen",
            choices=get_case_files(),
            value=get_case_files()[0] if get_case_files() else None
        )
        start_btn = gr.Button("Fall laden & Spiel starten", variant="primary")
    
    case_info = gr.Textbox(label="Fall-Informationen", lines=8, interactive=False)
    
    with gr.Row():
        day_status = gr.Textbox(label="Status", value="-", interactive=False, scale=2)
        power_btn = gr.Button("🧠 Detektiv-Power (1x)", interactive=False, variant="secondary", scale=1)
        debug_btn = gr.Button("🐛 Debug Log", interactive=False, scale=1)
    
    chat_history = gr.Textbox(label="Verhör-Protokoll", lines=20, interactive=False)
    
    gr.Markdown("---")
    gr.Markdown("### Deine Aktionen")
    
    with gr.Row():
        detective_btn = gr.Button("🔍 Gemini, befrage jemanden", interactive=False, variant="primary", scale=3)
    
    with gr.Row():
        killer_input = gr.Textbox(
            label="Deine Antwort (nur aktiv, wenn du befragt wirst)",
            placeholder="Wartet auf deine Befragung...",
            interactive=False,
            scale=3
        )
        killer_submit_btn = gr.Button("📤 Lüge senden", interactive=False, variant="stop", scale=1)
    
    # Events
    start_btn.click(
        fn=start_new_game,
        inputs=[case_file_dropdown],
        outputs=[case_info, detective_btn, power_btn, debug_btn, chat_history, day_status, killer_input, killer_submit_btn]
    )
    
    detective_btn.click(
        fn=handle_detective_action,
        inputs=[],
        outputs=[chat_history, day_status, killer_input, killer_submit_btn, detective_btn]
    )
    
    killer_submit_btn.click(
        fn=handle_killer_response,
        inputs=[killer_input],
        outputs=[chat_history, day_status, killer_input, killer_input, killer_submit_btn, detective_btn]
    )
    
    power_btn.click(
        fn=use_detective_power,
        inputs=[],
        outputs=[chat_history, power_btn]
    )
    
    debug_btn.click(
        fn=debug_show_log,
        inputs=[],
        outputs=[chat_history]
    )


if __name__ == "__main__":
    print("─" * 60)
    print("🔪 Reverse Murder Mystery - V7.0")
    print("─" * 60)
    print("Starte Gradio Interface...")
    print("Öffne Browser bei: http://127.0.0.1:7860")
    print("─" * 60)
    demo.launch()
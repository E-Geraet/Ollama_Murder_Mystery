# Ollama Murder Mystery — Reverse Edition

An AI-vs-AI crime game where you play the murderer instead of the detective. Your goal is to stay undetected for 30 days while a detective AI tries to catch you through contradictions in the interrogations.

## Concept

Two AI models play against you:

- **The Detective** (external, Gemini API) — sees only the neutral interrogation log and has to identify the most likely murderer with no prior knowledge of who did it. It looks for contradictions and builds a hypothesis for each suspect.
- **The Suspects** (local, Ollama) — play the innocent characters, defend their alibi automatically, and generate the questions the detective asks.

The detective interrogates suspects in rotation, automatically. If the person being questioned is innocent, the local AI answers on its own. If you (the murderer) are questioned, you type your own lie to avoid getting caught.

If the detective ends up accusing someone else, you win. If it accuses you, you lose.

## Architecture

| File | Role | Tech |
|---|---|---|
| `app.py` | Gradio UI, game logic, game state | Gradio |
| `game_engine.py` | AI integration (prompts, API calls) | Ollama + Gemini API |
| `cases/*.json` | Case data (victim, suspects, alibis, murderer) | JSON |

## Requirements

- Python 3.10+
- Ollama installed and running locally
- A Gemini API key (free via Google AI Studio)

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/E-Geraet/Ollama_Murder_Mystery.git
   cd Ollama_Murder_Mystery
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Pull the Ollama model (default: `ministral-3:3b`):
   ```bash
   ollama pull ministral-3:3b
   ```

4. Create a `.env` file (use `.env.example` as a template) and add your own Gemini key:
   ```env
   OLLAMA_MODEL=ministral-3:3b
   EXTERNAL_API_KEY="your-gemini-api-key"
   EXTERNAL_MODEL_NAME="gemini-2.0-flash"
   EXTERNAL_API_URL="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
   ```

5. Add at least one case file under `cases/` — see format below.

6. Start the game:
   ```bash
   python app.py
   ```
   Opens at `http://127.0.0.1:7860`.

## Case format

A file under `cases/example.json` needs at least this structure:

```json
{
  "victim": "Markus Keller",
  "location": "Lakeside Villa",
  "motive": "Inheritance dispute",
  "murderer_name": "Anna",
  "suspects": [
    {
      "name": "Anna",
      "alibi": "Claims she was home alone.",
      "traits": "Nervous, evasive under direct questioning."
    },
    {
      "name": "Thomas",
      "alibi": "Was at the office, confirmed by colleagues.",
      "traits": "Confident, easily irritated."
    }
  ]
}
```

## Gameplay

1. Select a case file and start the game.
2. The detective interrogates suspects in rotation, five questions per day, up to 30 days.
3. When you're questioned as the murderer, type your lie into the input field.
4. Once per game you can use the "Detective Power" for a deeper reasoning analysis of the investigation so far.
5. Eventually the detective makes an accusation, and the result shows immediately.

## Known limitations

- The game won't start without at least one file in `cases/`.
- How well lies get caught depends heavily on which Ollama model you use.

## Security note

The `.env` file holds your personal API key and must never be committed. It's in `.gitignore` — use `.env.example` as a template.

from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from flask_cors import CORS
import logging

# ✅ Laad de OpenAI API Key vanuit .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Flask-app instellen
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# ✅ Opslag voor gespreksgeschiedenis per gebruiker
user_sessions = {}

@app.route('/')
def home():
    return "🚀 AI Woningadviseur API is live! Gebruik /chat om vragen te stellen."

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_id = data.get('user_id', 'default')
    user_message = data.get('vraag', '').strip()

    if not user_message:
        return jsonify({"error": "Bericht mag niet leeg zijn."}), 400

    logging.info(f"📩 Bericht ontvangen van {user_id}: {user_message}")

    if user_id not in user_sessions:
        # Nieuwe sessie starten met aangepaste prompt
        user_sessions[user_id] = [
            {"role": "system", "content": """
Je bent een slimme AI-woningadviseur op Huislijn.nl.
Je helpt bezoekers om vragen te beantwoorden over specifieke woningen.

📌 Als de gebruiker nog geen URL heeft gedeeld van een woningpagina op Huislijn.nl:
- Vraag dan eerst vriendelijk om de link naar de woningpagina.

📌 Zodra de gebruiker een woning-URL heeft gedeeld:
- Gebruik de URL om het adres van de woning af te leiden.
- Gebruik Search Preview om online relevante informatie op te zoeken over de woning, omgeving, voorzieningen, reistijd, verduurzaming, hypotheken en verzekeringen.

⛔️ Je mag alleen woninggerelateerde vragen beantwoorden.
⛔️ Beantwoord geen vragen over niet-woninggerelateerde onderwerpen zoals auto's, fietsen, elektronica of persoonlijke zaken.

Geef altijd duidelijke, feitelijke en vriendelijke antwoorden.
"""}
        ]

    user_sessions[user_id].append({"role": "user", "content": user_message})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o-search-preview",
        "messages": user_sessions[user_id],
        "temperature": 0.5,
        "web_search_options": {
            "user_location": {
                "type": "approximate",
                "approximate": {
                    "country": "NL"
                }
            },
            "search_context_size": "medium"
        }
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        ai_response = response.json()["choices"][0]["message"]["content"]
        user_sessions[user_id].append({"role": "assistant", "content": ai_response})
        return jsonify({"antwoord": ai_response.strip()})
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify({"error": "Er is een fout opgetreden bij de AI. Probeer het later opnieuw."}), 500

if __name__ == '__main__':
    app.run(debug=True)

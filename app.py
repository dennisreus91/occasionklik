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
    vraag = data.get('vraag', '').strip()
    url = data.get('url', '').strip()

    if not vraag or not url:
        return jsonify({"error": "Zowel vraag als URL zijn verplicht."}), 400

    logging.info(f"📩 Vraag ontvangen van {user_id}: {vraag} (URL: {url})")

    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": f"""
Je bent een slimme AI-woningadviseur op Huislijn.nl.
Je krijgt vragen over woningen die bezoekers bekijken.
Gebruik de opgegeven URL om het adres van de woning af te leiden.
Gebruik Search Preview om online relevante informatie over de woning, omgeving, reistijd, voorzieningen, hypotheken, verzekeringen of verduurzaming op te zoeken.

📌 Alleen woninggerelateerde vragen mogen beantwoord worden.
⛔️ Vragen over niet-woninggerelateerde onderwerpen (zoals auto's of persoonlijke zaken) mag je niet beantwoorden.
Als iets niet woninggerelateerd is, geef dan vriendelijk aan dat je alleen vragen over de woning kunt beantwoorden.
"""}
        ]

    # ✅ Bouw gebruikersinvoer als promptregel
    user_sessions[user_id].append({"role": "user", "content": f"Vraag: {vraag}\nWoningpagina: {url}"})

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
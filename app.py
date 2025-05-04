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
    """
    Voert een doorlopend gesprek met de gebruiker via AI
    met focus op woninggerelateerde vragen.
    """
    data = request.json
    user_id = data.get('user_id', 'default')  # Uniek ID per gebruiker (afkomstig uit Landbot)
    user_message = data.get('message', '').strip()

    logging.info(f"📩 Ontvangen bericht van {user_id}: {user_message}")

    if not user_message:
        return jsonify("Bericht mag niet leeg zijn."), 400

    # ✅ Start nieuwe sessie indien nodig
    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """
Je bent een slimme AI-woningadviseur op Huislijn.nl.
Je helpt bezoekers bij het vinden van informatie en advies over specifieke woningen.

📌 Vraag eerst waar de bezoeker behoefte aan heeft.
📌 Als de bezoeker informatie of advies wil over een specifieke woning:
    - Vraag om de URL van de woningpagina op Huislijn.nl (als die nog niet bekend is).

📌 Zodra een woning-URL is gedeeld:
    - Gebruik deze om online informatie op te halen over de woning, buurt, voorzieningen, verduurzaming, hypotheken of verzekeringen via web search.
    - Houd rekening met de gedeelde woning voor verdere vragen.

⛔️ Beantwoord alleen woninggerelateerde vragen.
⛔️ Geef vriendelijk aan als een vraag niet over woningen gaat.

Wees altijd vriendelijk, behulpzaam en duidelijk.
"""}
        ]

    # ✅ Voeg nieuwe gebruikersinvoer toe
    user_sessions[user_id].append({"role": "user", "content": user_message})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # ✅ Bouw de payload correct voor gpt-4o-search-preview
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

        # ✅ Stuur antwoord terug naar de gebruiker
        return jsonify({"antwoord": ai_response.strip()})
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify({"error": "Er is een fout opgetreden bij de AI. Probeer het later opnieuw."}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

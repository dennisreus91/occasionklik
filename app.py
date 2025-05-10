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
CORS(app)  # Sta API-aanvragen toe vanaf andere domeinen

# ✅ Logging instellen voor debug-informatie
logging.basicConfig(level=logging.INFO)

# ✅ Opslag voor gespreksgeschiedenis per gebruiker (tijdelijk geheugen)
user_sessions = {}

@app.route('/')
def home():
    return "🚀 AI Woningadviseur API is live! Gebruik /chat om vragen te stellen."

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_id = data.get('user_id', 'default')
    user_message = data.get('message', '').strip()

    logging.info(f"📩 Ontvangen bericht van {user_id}: {user_message}")

    if not user_message:
        return jsonify("Bericht mag niet leeg zijn"), 400

    # ✅ Start nieuwe sessie indien nodig
    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """
Je bent Ronald, woningadviseur bij Huislijn.nl. Bezoekers plakken woninginformatie in de chat. Beantwoord vervolgens woninggerelateerde vragen.

Start:
- Stel jezelf voor.
- Vraag om de volledige informatie over de woning waar de bezoeker geïnteresseerd in is zodat hier in de antwoorden rekening mee gehouden kan worden.

Als info is ontvangen:
- Geef aan dat je kan helpen bij alle vragen over de woning om tot een keuze te komen zoals voorzieningen, ligging, verduurzaming, etc.
- Beantwoord vragen kort en concreet, enkel op basis van de geplakte tekst.

Sluit af:
- Vraag of ze interesse hebben in de woning.
- Zo ja: vraag naam, e-mail en telefoonnummer voor contact met de makelaar.

✅ Gebruik emoji’s waar passend. 
"""}
        ]

    user_sessions[user_id].append({"role": "user", "content": user_message})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o",
        "messages": user_sessions[user_id],
        "temperature": 0.3
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        ai_response = response.json()["choices"][0]["message"]["content"]
        clean_response = ai_response.strip().replace("\n\n", "<br><br>").replace("\n", " ")

        user_sessions[user_id].append({"role": "assistant", "content": ai_response})
        return jsonify(clean_response)

    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify("Er is een fout opgetreden bij de AI. Probeer het later opnieuw."), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

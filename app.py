from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from flask_cors import CORS
import logging
import markdown  # ✅ Toegevoegd voor automatische Markdown naar HTML conversie

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
        return jsonify({"error": "Bericht mag niet leeg zijn."}), 400

    # ✅ Start nieuwe sessie indien nodig
    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """
Je bent een slimme AI-woningadviseur op Huislijn.nl.

Werkwijze:
- Vraag eerst waar de bezoeker behoefte aan heeft.
- Als de bezoeker informatie of advies wil over een specifieke woning:
    - Vraag zowel om de URL van de woningpagina op Huislijn.nl
    - En vraag welke specifieke vragen of welk type advies de bezoeker over deze woning wil.
- Gebruik pas daarna de URL (en de vragen) om gericht antwoord te geven.

Belangrijk:
- Gebruik Search Preview om online informatie op te halen over de woning, buurt, voorzieningen, verduurzaming, hypotheken of verzekeringen.
- Beantwoord alleen woninggerelateerde vragen.
- Geef vriendelijk aan als vragen niet woninggerelateerd zijn.
- Beantwoord kort, bondig, feitelijk en specifiek de gestelde vraag.
- Je mag waar relevant gebruik maken van kleine symbolen en emoji's (zoals ✅, 📍, 🔑) om antwoorden visueel aantrekkelijker te maken.
- Blijf professioneel en duidelijk. Gebruik symbolen spaarzaam en passend bij het antwoord.

Regels voor je antwoord:
- Voeg geen externe links toe zoals Google Maps-links.
- Herhaal het adres van de woning niet expliciet in het antwoord.
- Richt je direct op het beantwoorden van de vraag.

Wees vriendelijk, behulpzaam en duidelijk.
"""}
        ]

    # ✅ Voeg nieuwe gebruikersinvoer toe
    user_sessions[user_id].append({"role": "user", "content": user_message})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # ✅ Bouw de correcte payload
    payload = {
        "model": "gpt-4o-search-preview",
        "messages": user_sessions[user_id],
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

    # ✅ Debugging: toon de payload die naar OpenAI wordt gestuurd
    logging.debug(f"➡️ Payload naar OpenAI: {payload}")

    # ✅ Verstuur naar OpenAI
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        raw_response = response.json()["choices"][0]["message"]["content"]

        # ✅ Stap 1: opschonen van onnodige headings en lege regels
        lines = raw_response.splitlines()
        cleaned_lines = [line for line in lines if not (line.startswith("#") or line.strip() == "")]
        markdown_text = " ".join(cleaned_lines).strip()

        # ✅ Stap 2: Markdown naar nette HTML omzetten
        html_text = markdown.markdown(markdown_text)

        # ✅ Stap 3: Extra lichte cleaning voor losse escapes en spaties
        html_text = html_text.replace("\\n", " ").replace("\\", "").replace("  ", " ").strip()

        # ✅ Update sessiegeschiedenis
        user_sessions[user_id].append({"role": "assistant", "content": html_text})

        # ✅ Retourneer direct de nette HTML output
        return html_text
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify({"error": "Er is een fout opgetreden bij de AI. Probeer het later opnieuw."}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

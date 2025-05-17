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
Je bent Ronald, woningadviseur bij Huislijn.nl. Je helpt bezoekers via deze chat met alle woninggerelateerde vragen.

Bezoekers kunnen woninginformatie in de chat plakken (zoals een woningtekst of link). Gebruik deze tekst als basis, maar geef alleen antwoord op gestelde vragen — deel dus geen proactieve informatie over de woning zonder dat erom gevraagd is. Vul je antwoorden aan met je eigen algemene kennis over woningen, wijken, verduurzaming, ligging, voorzieningen, hypotheken en verbouwing.

Start:
- Stel jezelf kort voor als Ronald van Huislijn.nl.
- Vertel waarmee je kunt helpen, zoals:
  ➤ het beantwoorden van vragen over een specifieke woning  
  ➤ hulp bij verduurzaming, verbouwing, financiering en ligging  
  ➤ ondersteuning bij het vergelijken van woningen
- Vraag daarna naar de volledige informatie over de woning waar de bezoeker interesse in heeft (of laat hen een woningpagina-link delen), zodat je antwoorden hierop kunt afstemmen.

Antwoordregels:
- Geef altijd eerst zelf een concreet en woninggericht antwoord op de vraag.
- Gebruik de geplakte woningtekst én je eigen kennis.
- Geef korte, duidelijke antwoorden.
- Gebruik emoji’s waar passend (zoals ✅ 📍 🔑).
- Als je de vraag niet concreet kunt beantwoorden, verwijs dan vriendelijk naar een relevante externe website waar deze info mogelijk wel te vinden is.

Externe links (indien relevant, na antwoord):
- Verduurzaming ➝ <a href="https://mijnenergieprestatie.nl/?utm_source=huislijn&utm_medium=chat&utm_campaign=advies" target="_blank">mijnenergieprestatie.nl</a>  
- Financiering ➝ <a href="https://www.hypotheker.nl/?utm_source=huislijn&utm_medium=chat&utm_campaign=advies" target="_blank">hypotheker.nl</a>  
- Hypotheekadvies ➝ <a href="https://www.hypotheker.nl/?utm_source=huislijn&utm_medium=chat&utm_campaign=advies" target="_blank">hypotheker.nl</a>
- Berekenen maximale hypotheek of budget ➝ <a href="https://www.hypotheker.nl/zelf-berekenen/kan-ik-dit-huis-betalen/?utm_source=huislijn&utm_medium=chat&utm_campaign=advies" target="_blank">Bereken nu!</a>
                          
Afsluiting:
- Vraag na het beantwoorden van alle vragen of de bezoeker geïnteresseerd is in een bezichtiging of contact met de makelaar.
- Als dat zo is, verwijs de bezoeker dan naar het aanmeldformulier via:
  ➤ [woningpagina-URL]/bezichtiging  
  Bijvoorbeeld: <a href="https://www.huislijn.nl/koopwoning/nederland/utrecht/4182711/iepstraat-3-utrecht/bezichtiging" target="_blank">hypotheker.nl</a>
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

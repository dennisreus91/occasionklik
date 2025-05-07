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
Je bent Ronald, jouw persoonlijke woningadviseur namens Huislijn.nl.

Je bent zichtbaar voor alle bezoekers die op Huislijn.nl op zoek zijn naar een nieuwe woning.  
Je doel is om bezoekers zo goed mogelijk te begeleiden door kort, duidelijk en bondig antwoord te geven op hun vragen.  
Je mag symbolen en emoji’s gebruiken om antwoorden visueel aantrekkelijker te maken, zolang het professioneel blijft.  

Stap 1 – Introductie:
- Stel jezelf voor als Ronald, persoonlijk woningadviseur.
- Vraag waarmee je de bezoeker mag helpen.

Stel hierbij vriendelijk drie opties ter inspiratie voor:
1️⃣ Hulp bij het vinden van een geschikte woning ➔ Vraag in dat geval naar de woonwensen zodat een dynamische link naar relevante woningen gedeeld kan worden.  
2️⃣ Vragen over een specifieke woning ➔ Vraag naar de URL van de woningpagina en vraag welke specifieke vragen of punten de bezoeker heeft over deze woning.  
3️⃣ Vragen over verbouwen, verduurzaming of financiering ➔ Vraag om toelichting op hun specifieke situatie zodat je gericht advies kunt geven.

Stap 2 – Gesprek voeren:
- Antwoord kort, duidelijk en feitelijk.
- Speel in op de gekozen behoefte van de bezoeker.
- Gebruik zo nodig kleine emoji's of symbolen om belangrijke punten te benadrukken (zoals ✅, 📍, 🛠️, 💬).
- Vermijd lange lappen tekst of uitgebreide toelichtingen.

Stap 3 – Afsluiten:
- Vraag altijd na een antwoord of de bezoeker hiermee geholpen is, of dat er nog aanvullende vragen zijn.  
  Bijvoorbeeld: “Kan ik verder nog ergens bij helpen? 😊”

Belangrijke regels:
- Alleen woninggerelateerde vragen beantwoorden.
- Geen externe links zoals Google Maps delen.
- Herhaal het adres van woningen niet expliciet, tenzij de bezoeker hierom vraagt.
- Gebruik Search Preview om waar nodig extra actuele informatie online op te halen.
- Focus op helder, vriendelijk en behulpzaam communiceren.

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

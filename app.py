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

# ✅ Opslag voor gespreksgeschiedenis en samenvatting per gebruiker
user_sessions = {}
user_summaries = {}  # ✅ Hier slaan we de samenvatting per gebruiker op

# ✅ Configuratie instellingen
MAX_HISTORY_BEFORE_SUMMARY = 15  # Tot 15 berichten wordt de volledige chatgeschiedenis meegestuurd
LAST_MESSAGES_AFTER_SUMMARY = 5  # Na samenvatting worden de laatste 5 berichten meegestuurd

@app.route('/')
def home():
    return "🚀 AI Autoverkoper API is live! Gebruik /chat om vragen te stellen."

@app.route('/chat', methods=['POST'])
def chat():
    """
    Voert een doorlopend gesprek met de gebruiker via AI.
    De AI is getraind als een ervaren autoverkoper.
    """
    data = request.json
    user_id = data.get('user_id', 'default')  # Uniek ID per gebruiker (afkomstig uit Landbot)
    user_message = data.get('message', '').strip()

    # ✅ Log het ontvangen bericht
    logging.info(f"🚀 Ontvangen bericht van {user_id}: {user_message}")

    # ✅ Controleer of het bericht leeg is
    if not user_message:
        return jsonify({"response": "Bericht mag niet leeg zijn"}), 400

    # ✅ Gespreksgeschiedenis ophalen of aanmaken
    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """Je bent Jan Reus, een ervaren autoverkoper met 10 jaar ervaring.
            Je helpt klanten bij het vinden van hun ideale tweedehands auto door hen vragen te stellen over hun wensen en situatie.
            Je introduceert jezelf vriendelijk en stelt enkele beginvragen zoals budget, type auto en gebruiksdoel.
            Je beantwoordt **alleen autogerelateerde vragen**. Als iemand iets anders vraagt, zeg je dat deze chat alleen bedoeld is voor autovragen."""}
        ]
        user_summaries[user_id] = ""  # ✅ Start met een lege samenvatting

    # ✅ Voeg de gebruikersvraag toe aan de sessie
    user_sessions[user_id].append({"role": "user", "content": user_message})

    # ✅ **Bepaal welke data naar OpenAI wordt gestuurd**
    if len(user_sessions[user_id]) <= MAX_HISTORY_BEFORE_SUMMARY:
        # ✅ Stuur volledige gespreksgeschiedenis als het minder dan 15 berichten zijn
        messages_to_send = user_sessions[user_id]
    else:
        # ✅ Maak een samenvatting als de chatgeschiedenis te lang wordt
        if not user_summaries[user_id]:  # Alleen samenvatten als dit nog niet is gedaan
            summary_prompt = """Vat dit gesprek kort samen en bewaar alleen de belangrijkste informatie die nodig is om een goed advies te geven.
            Focus op:
            - Naam van de gebruiker
            - Budget
            - Woonplaats
            - Gebruik van de auto (bijvoorbeeld woon-werk, vakantie, gezin, etc.)
            - Type auto (SUV, hatchback, station, etc.)
            - Maximale kilometerstand
            - Bouwjaar
            - Voorkeur voor opties (navigatie, stoelverwarming, trekhaak, etc.)
            - Voorkeur voor merk en model
            - Eventuele extra wensen of belangrijke informatie."""

            history_text = "\n".join([msg["content"] for msg in user_sessions[user_id]])

            summary_payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": summary_prompt},
                    {"role": "user", "content": history_text}
                ],
                "temperature": 0.5
            }

            summary_response = requests.post("https://api.openai.com/v1/chat/completions", headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }, json=summary_payload)

            if summary_response.status_code == 200:
                user_summaries[user_id] = summary_response.json()["choices"][0]["message"]["content"]
                logging.info(f"✅ Samenvatting gegenereerd voor {user_id}: {user_summaries[user_id]}")

        # ✅ Gebruik de samenvatting + de laatste 5 berichten als context
        messages_to_send = [
            {"role": "system", "content": f"Samenvatting van eerdere gesprekken: {user_summaries[user_id]}"}
        ] + user_sessions[user_id][-LAST_MESSAGES_AFTER_SUMMARY:]

    # ✅ OpenAI API-aanroep
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages_to_send,
        "temperature": 0.7
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        ai_response = response.json()["choices"][0]["message"]["content"]
        
        # ✅ Log de AI-reactie
        logging.info(f"🛠️ AI-reactie voor {user_id}: {ai_response}")

        # ✅ Verwijder overbodige newlines en vervang markdown (`###`) door vetgedrukte HTML-tags
        clean_response = ai_response.strip()\
            .replace("\n\n", "<br><br>")\
            .replace("\n", " ")\
            .replace("### ", "<b>")\
            .replace("###", "</b>")\
            .replace("\n- ", "<br>🔹 ")\
            .replace("•", "🔹")

        # ✅ Voeg AI-reactie toe aan de gespreksgeschiedenis
        user_sessions[user_id].append({"role": "assistant", "content": ai_response})

        return jsonify({"response": clean_response})  # ✅ JSON blijft behouden, maar netjes geformatteerd
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify({"error": "OpenAI API-fout", "details": response.text}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

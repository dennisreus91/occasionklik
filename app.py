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

# ✅ Opslag voor gespreksgeschiedenis, samenvatting en auto-advies per gebruiker
user_sessions = {}
user_summaries = {}
user_car_advice = {}  # ✅ Hier slaan we het geadviseerde model op per gebruiker

# ✅ Configuratie instellingen
MAX_HISTORY_BEFORE_SUMMARY = 15
LAST_MESSAGES_AFTER_SUMMARY = 5

@app.route('/')
def home():
    return "🚀 AI Autoverkoper API is live! Gebruik /chat om vragen te stellen."

# ✅ Functie om een dynamische Gaspedaal.nl-link te genereren
def generate_gaspedaal_link(brand, model, budget, min_year, max_km):
    """
    Genereert een dynamische link naar Gaspedaal.nl op basis van de gebruikersvoorkeuren.
    """
    base_url = "https://www.gaspedaal.nl"
    search_url = f"{base_url}/{brand.lower()}/{model.lower()}?bmax={budget}&jaarmin={min_year}&kmmax={max_km}"
    return search_url

@app.route('/chat', methods=['POST'])
def chat():
    """
    Voert een doorlopend gesprek met de gebruiker via AI.
    De AI is getraind als een ervaren autoverkoper.
    """
    data = request.json
    user_id = data.get('user_id', 'default')
    user_message = data.get('message', '').strip()

    logging.info(f"🚀 Ontvangen bericht van {user_id}: {user_message}")

    if not user_message:
        return jsonify({"response": "Bericht mag niet leeg zijn"}), 400

    # ✅ Gespreksgeschiedenis ophalen of aanmaken
    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """Je bent Jan Reus, een ervaren autoverkoper. 
            Je stelt slimme vragen en adviseert uiteindelijk **een specifiek merk, model en uitvoering**.
            Bijvoorbeeld: "Op basis van jouw wensen raad ik de **Volkswagen Tiguan 1.5 TSI Highline 2021** aan."
            Zorg ervoor dat je altijd een **specifiek model met bouwjaar en uitvoering** noemt. 
            Vraag de gebruiker altijd om bevestiging voordat je een link deelt."""}
        ]
        user_summaries[user_id] = ""
        user_car_advice[user_id] = None  # ✅ Auto-advies wordt hier opgeslagen

    user_sessions[user_id].append({"role": "user", "content": user_message})

    # ✅ Controleer of de gebruiker het auto-advies bevestigt
    if user_car_advice[user_id] and any(word in user_message.lower() for word in ["ja", "oké", "lijkt me goed", "dat zoek ik"]):
        car = user_car_advice[user_id]
        gaspedaal_url = generate_gaspedaal_link(car["brand"], car["model"], car["budget"], car["min_year"], car["max_km"])

        ai_response = f"🚗 Mooi! Hier is jouw auto op Gaspedaal.nl: [**Klik hier om de auto te bekijken**]({gaspedaal_url}) 🚀"
        return jsonify({"response": ai_response})

    # ✅ Als de sessie nog kort is, stuur volledige chatgeschiedenis
    if len(user_sessions[user_id]) <= MAX_HISTORY_BEFORE_SUMMARY:
        messages_to_send = user_sessions[user_id]
    else:
        if not user_summaries[user_id]:  
            summary_prompt = """Vat dit gesprek kort samen en bewaar alleen de belangrijkste informatie:
            - Budget
            - Type auto
            - Gebruiksdoel
            - Maximale kilometerstand
            - Bouwjaar
            - Voorkeur voor opties (navigatie, stoelverwarming, etc.)
            - Merk en model voorkeuren."""

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

        messages_to_send = [
            {"role": "system", "content": f"Samenvatting van eerdere gesprekken: {user_summaries[user_id]}"}
        ] + user_sessions[user_id][-LAST_MESSAGES_AFTER_SUMMARY:]

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

        # ✅ Controleer of AI een auto-advies geeft
        if "Op basis van jouw wensen raad ik de" in ai_response:
            words = ai_response.split()
            try:
                brand = words[words.index("raad") + 4]  
                model = words[words.index("raad") + 5]
                budget = 30000  # Placeholder, haal deze uit de chat
                min_year = 2020
                max_km = 80000

                user_car_advice[user_id] = {"brand": brand, "model": model, "budget": budget, "min_year": min_year, "max_km": max_km}

                ai_response += "\n\n👍 **Wil je deze auto bekijken op Gaspedaal.nl?** Bevestig dit en ik deel de link!"
            except ValueError:
                pass

        logging.info(f"🛠️ AI-reactie voor {user_id}: {ai_response}")

        clean_response = ai_response.strip()\
            .replace("\n\n", "<br><br>")\
            .replace("\n", " ")\
            .replace("### ", "<b>")\
            .replace("###", "</b>")\
            .replace("\n- ", "<br>🔹 ")\
            .replace("•", "🔹")

        user_sessions[user_id].append({"role": "assistant", "content": ai_response})

        return jsonify({"response": clean_response})
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify({"error": "OpenAI API-fout", "details": response.text}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

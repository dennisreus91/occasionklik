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

# ✅ Opslag voor gespreksgeschiedenis en auto-advies per gebruiker
user_sessions = {}
user_summaries = {}
user_car_advice = {}  # ✅ Hier slaan we het geadviseerde model op per gebruiker

# ✅ Configuratie instellingen
MAX_HISTORY_BEFORE_SUMMARY = 15
LAST_MESSAGES_AFTER_SUMMARY = 5

@app.route('/')
def home():
    return "🚀 AI Autoverkoper API is live! Gebruik /chat om vragen te stellen."

# ✅ Dynamische Gaspedaal.nl-link generatie zonder bevestiging
def generate_gaspedaal_link(brand, model, min_year, max_km, transmission, fuel_type):
    """
    Genereert een dynamische link naar Gaspedaal.nl op basis van de auto-voorkeuren.
    """
    base_url = "https://www.gaspedaal.nl"

    # ✅ Merk en model in kleine letters en URL-vriendelijk
    brand = brand.lower().replace(" ", "-")  
    model = model.lower().replace(" ", "-")

    # ✅ Transmissie omzetten naar juiste waarde
    trns = "14" if transmission.lower() == "automaat" else "15"

    # ✅ Brandstoftype omzetten naar juiste URL-waarde
    fuel_mapping = {
        "benzine": "benzine",
        "diesel": "diesel",
        "hybride": "hybride",
        "elektrisch": "elektrisch"
    }
    fuel_url = fuel_mapping.get(fuel_type.lower(), "benzine")  # Default naar benzine als onbekend

    # ✅ Genereer de uiteindelijke zoek-URL
    search_url = f"{base_url}/{brand}/{model}/{fuel_url}?trns={trns}&bmin={min_year}&kmax={max_km}&srt=df-a"

    return search_url

@app.route('/chat', methods=['POST'])
def chat():
    """
    Voert een doorlopend gesprek met de gebruiker via AI.
    De AI is getraind als een ervaren autoverkoper en genereert automatisch een Gaspedaal.nl-link.
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
            Je stelt slimme vragen en adviseert een **specifiek merk, model en uitvoering**.
            Bijvoorbeeld: "Ik raad de **Volkswagen Tiguan 1.5 TSI Highline 2021, automaat, benzine** aan."
            Geef korte, professionele en duidelijke antwoorden.
            Zodra een auto geadviseerd wordt, geef je direct de bijbehorende Gaspedaal.nl-link."""}
        ]
        user_summaries[user_id] = ""
        user_car_advice[user_id] = None  # ✅ Auto-advies wordt hier opgeslagen

    user_sessions[user_id].append({"role": "user", "content": user_message})

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

        # ✅ Controleer of AI een auto-advies geeft en genereer direct de link
        if "Ik raad de" in ai_response:
            words = ai_response.split()
            try:
                brand = words[words.index("de") + 2]  
                model = words[words.index("de") + 3]
                budget = 30000  # Placeholder, haal deze uit de chat
                min_year = 2020
                max_km = 80000
                transmission = "automaat" if "automaat" in ai_response.lower() else "handgeschakeld"
                fuel = "benzine" if "benzine" in ai_response.lower() else "diesel" if "diesel" in ai_response.lower() else "hybride" if "hybride" in ai_response.lower() else "elektrisch"

                gaspedaal_url = generate_gaspedaal_link(brand, model, min_year, max_km, transmission, fuel)

                ai_response += f"\n\n🚗 **Bekijk deze auto op Gaspedaal.nl:** [**Klik hier**]({gaspedaal_url}) 🚀"
            except ValueError:
                pass

        user_sessions[user_id].append({"role": "assistant", "content": ai_response})
        return jsonify({"response": ai_response})
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify({"error": "OpenAI API-fout", "details": response.text}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

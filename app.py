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

# ✅ Functie voor het genereren van de correcte Gaspedaal.nl-link
def generate_gaspedaal_link(brand, model, fuel_type):
    """
    Genereert een correcte dynamische link naar Gaspedaal.nl met merk, model en brandstofsoort.
    """
    base_url = "https://www.gaspedaal.nl"

    # ✅ Merk en model correct in URL-formaat zetten
    brand = brand.lower().replace(" ", "-")  
    model = model.lower().replace(" ", "-")

    # ✅ Brandstoftype correct verwerken
    fuel_mapping = {
        "benzine": "benzine",
        "diesel": "diesel",
        "hybride": "hybride",
        "elektrisch": "elektrisch"
    }
    fuel_url = fuel_mapping.get(fuel_type.lower(), "benzine")  # Default naar benzine als onbekend

    # ✅ Eindelijke zoek-URL genereren
    search_url = f"{base_url}/{brand}/{model}/{fuel_url}?srt=df-a"

    return search_url

@app.route('/chat', methods=['POST'])
def chat():
    """
    Voert een doorlopend gesprek met de gebruiker via AI.
    Zodra een auto-advies is gegeven, wordt automatisch een Gaspedaal.nl-link gedeeld.
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
            Je stelt slimme vragen en adviseert een **specifiek merk, model en brandstofsoort**.
            Bijvoorbeeld: "Ik raad de **Peugeot 2008, benzine** aan."
            Zodra een auto geadviseerd wordt, geef je direct de bijbehorende Gaspedaal.nl-link in de volgende vorm:
            "🚗 Bekijk deze auto op Gaspedaal.nl: [**Klik hier**](de dynamische link) 🚀"
            """}
        ]
        user_summaries[user_id] = ""
        user_car_advice[user_id] = None  # ✅ Auto-advies wordt hier opgeslagen

    user_sessions[user_id].append({"role": "user", "content": user_message})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": user_sessions[user_id],
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
                fuel = "benzine" if "benzine" in ai_response.lower() else \
                       "diesel" if "diesel" in ai_response.lower() else \
                       "hybride" if "hybride" in ai_response.lower() else \
                       "elektrisch"

                gaspedaal_url = generate_gaspedaal_link(brand, model, fuel)

                ai_response += f"\n\n🚗 Bekijk deze auto op Gaspedaal.nl: [**Klik hier**]({gaspedaal_url}) 🚀"
            except ValueError:
                pass

        # ✅ Verbeterde chatweergave en verwijder ongewenste tekens
        formatted_response = ai_response.strip()\
            .replace("\n\n", "<br><br>")\
            .replace("\n", " ")\
            .replace("### ", "<b>")\
            .replace("###", "</b>")\
            .replace("\n- ", "<br>🔹 ")\
            .replace("•", "🔹")

        user_sessions[user_id].append({"role": "assistant", "content": formatted_response})
        return jsonify({"response": formatted_response})
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify({"error": "OpenAI API-fout", "details": response.text}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

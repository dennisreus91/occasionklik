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

# ✅ Opslag voor gespreksgeschiedenis per gebruiker
user_sessions = {}

@app.route('/')
def home():
    return "🚀 AI Autoverkoper API is live! Gebruik /chat om vragen te stellen."

@app.route('/chat', methods=['POST'])
def chat():
    """
    Voert een doorlopend gesprek met de gebruiker via AI.
    Zodra een auto-advies is gegeven, genereert OpenAI de Gaspedaal.nl-link.
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

            Als je een auto adviseert, genereer je automatisch een **correcte en klikbare Gaspedaal.nl-link** in de volgende vorm:
            "🚗 Bekijk deze auto op Gaspedaal.nl: [**Klik hier**](https://www.gaspedaal.nl/{merk}/{model}/{brandstof}?srt=df-a) 🚀"

            Waarbij je **{merk} en {model}** in kleine letters en zonder spaties omzet naar URL-vriendelijke formaten.
            Voorbeeld:  
            - "Peugeot 2008, benzine" → https://www.gaspedaal.nl/peugeot/2008/benzine?srt=df-a
            - "Volkswagen Golf, diesel" → https://www.gaspedaal.nl/volkswagen/golf/diesel?srt=df-a
            - "Toyota Yaris, hybride" → https://www.gaspedaal.nl/toyota/yaris/hybride?srt=df-a

            Zorg ervoor dat de link correct is en klikbaar blijft. Formatteer het antwoord professioneel en beknopt."""}
        ]

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

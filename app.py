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

# ✅ Homepage route (Render zal deze pagina tonen bij bezoek aan de hoofd-URL)
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
        return jsonify({"error": "Bericht mag niet leeg zijn"}), 400

    # ✅ Gespreksgeschiedenis ophalen of aanmaken
    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """Je bent Jan Reus, een ervaren autoverkoper met 10 jaar ervaring.
            Je helpt klanten bij het vinden van hun ideale tweedehands auto door hen vragen te stellen over hun wensen en situatie.
            Je introduceert jezelf vriendelijk en stelt enkele beginvragen zoals budget, type auto en gebruiksdoel.
            Als klanten niet genoeg details geven, stel je vervolgvragen. Zodra er voldoende informatie is, adviseer je een specifieke auto
            inclusief merk, model, type en een bouwjaar.
            Je beantwoordt **alleen autogerelateerde vragen**. Als iemand iets anders vraagt, zeg je dat deze chat alleen bedoeld is voor autovragen."""}
        ]

    # ✅ Voeg de gebruikersvraag toe aan de gespreksgeschiedenis
    user_sessions[user_id].append({"role": "user", "content": user_message})

    # ✅ Log de volledige gespreksgeschiedenis voor debuggen
    logging.info(f"📝 Huidige gespreksgeschiedenis voor {user_id}: {user_sessions[user_id]}")

    # ✅ OpenAI API-aanroep met volledige gespreksgeschiedenis
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": user_sessions[user_id],  # Stuur de volledige gespreksgeschiedenis mee
        "temperature": 0.7
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        ai_response = response.json()["choices"][0]["message"]["content"]
        
        # ✅ Log de AI-reactie
        logging.info(f"🛠️ AI-reactie voor {user_id}: {ai_response}")

        # ✅ Formatteer de AI-reactie als HTML zonder conflicten met Landbot
        clean_response = ai_response.replace("\n", "<br>").replace("•", "🔹")
        formatted_response = f"""
        <div style='background:#f4f4f4; padding:12px; border-radius:10px; font-family:Arial, sans-serif; line-height:1.6;'>
            <b>🤖 AI Autoverkoper:</b><br><br>
            {clean_response}
        </div>
        """

        # ✅ Voeg AI-reactie toe aan de gespreksgeschiedenis
        user_sessions[user_id].append({"role": "assistant", "content": ai_response})

        return jsonify({"response": formatted_response})
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify({"error": "OpenAI API-fout", "details": response.text}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

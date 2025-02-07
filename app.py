from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from flask_cors import CORS

# ✅ Laad de API Key vanuit .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Flask-app instellen
app = Flask(__name__)
CORS(app)  # Sta API-aanvragen toe vanaf andere domeinen

# ✅ Opslag voor gespreksgeschiedenis per gebruiker (tijdelijk geheugen)
user_sessions = {}

@app.route('/chat', methods=['POST'])
def chat():
    """
    Voert een doorlopend gesprek met de gebruiker via AI.
    De AI is getraind als een ervaren autoverkoper.
    """
    data = request.json
    print("🚀 Ontvangen data van Landbot:", data)  # 👉 Logt de binnenkomende data

    user_id = data.get('user_id', 'default')  
    user_message = data.get('message', '').strip()  # 🛑 Zorgt ervoor dat lege berichten niet worden verzonden

    # 🚨 Controleer of het bericht leeg is
    if not user_message:
        print("⚠️ Leeg bericht ontvangen, antwoord niet mogelijk.")  # 👉 Logt fout
        return jsonify({"error": "Geen geldige invoer ontvangen. Stel een vraag over een auto."}), 400

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
    
    # ✅ Voeg de gebruikersvraag toe aan de chatgeschiedenis
    user_sessions[user_id].append({"role": "user", "content": user_message})

    # ✅ OpenAI API-aanroep met chatgeschiedenis
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
        
        # ✅ Voeg AI-reactie toe aan de chatgeschiedenis
        user_sessions[user_id].append({"role": "assistant", "content": ai_response})

        print("✅ AI-reactie:", ai_response)  # 👉 Logt AI-respons

        return jsonify({"ai_response": ai_response})
    else:
        error_details = response.text
        print("❌ OpenAI API-fout:", error_details)  # 👉 Logt API-fouten
        return jsonify({"error": "OpenAI API-fout", "details": error_details}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

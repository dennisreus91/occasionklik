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
    return "🚀 AI Autoverkoper API is live! Gebruik /chat om vragen te stellen."

@app.route('/chat', methods=['POST'])
def chat():
    """
    Voert een doorlopend gesprek met de gebruiker via AI.
    Zodra er een concreet auto-advies wordt gegeven, genereert OpenAI automatisch een dynamische Gaspedaal.nl-link.
    """
    data = request.json
    user_id = data.get('user_id', 'default')  # Uniek ID per gebruiker (afkomstig uit Landbot)
    user_message = data.get('message', '').strip()

    logging.info(f"🚀 Ontvangen bericht van {user_id}: {user_message}")

    if not user_message:
        return jsonify("Bericht mag niet leeg zijn"), 400  

    # ✅ Gespreksgeschiedenis ophalen of aanmaken
    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """Je bent Jan Reus, een ervaren autoverkoper met 10 jaar ervaring. 
            Je helpt klanten bij het vinden van hun ideale tweedehands auto door slimme vragen te stellen over hun wensen. 
            
            ✅ **Zodra er voldoende informatie is, adviseer je een specifieke auto** met:
            - Merk en model
            - Brandstoftype (benzine, diesel, hybride, elektrisch)
            - Bouwjaar (schatting)
            - Transmissie (automaat of handgeschakeld)
            
            ✅ **Je genereert automatisch een correcte, klikbare link naar Gaspedaal.nl.**  
            Gebruik deze URL-structuur en vul deze dynamisch in:
            
            🚗 *Voorbeeld link:*
            [**Klik hier**](https://www.gaspedaal.nl/{merk}/{model}/{brandstof}?srt=df-a)

            **Regels voor de link:**  
            - Merk en model moeten klein geschreven zijn, zonder spaties.  
            - Brandstoftype moet correct worden verwerkt (benzine, diesel, hybride of elektrisch).  
            - De link mag alleen worden gegenereerd als je zeker weet welk model het best bij de klant past.  
            
            🎯 **Voorbeelden van correcte links:**  
            - Peugeot 2008, benzine → [Klik hier](https://www.gaspedaal.nl/peugeot/2008/benzine?srt=df-a)  
            - Volkswagen Golf, diesel → [Klik hier](https://www.gaspedaal.nl/volkswagen/golf/diesel?srt=df-a)  
            - Toyota Yaris, hybride → [Klik hier](https://www.gaspedaal.nl/toyota/yaris/hybride?srt=df-a)  

            ✅ **Je gebruikt een vriendelijke en professionele toon en houdt je antwoorden kort.**  
            ✅ **Je mag emoji's gebruiken om het gesprek menselijker te maken, maar houd het professioneel.**  
            ✅ **Je beantwoordt alleen autogerelateerde vragen en verwijst gebruikers anders door.**  
            """}
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

        # ✅ Log AI-reactie voor controle
        logging.info(f"🛠️ AI-reactie voor {user_id}: {ai_response}")

        # ✅ Verbeterde opmaak zonder markdown en JSON-fouten
        clean_response = ai_response.strip()\
            .replace("\n\n", "<br><br>")\
            .replace("\n", " ")\
            .replace("### ", "<b>")\
            .replace("###", "</b>")\
            .replace("\n- ", "<br>🔹 ")\
            .replace("•", "🔹")

        # ✅ Voeg AI-reactie toe aan de gespreksgeschiedenis
        user_sessions[user_id].append({"role": "assistant", "content": ai_response})

        return jsonify(clean_response)  
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify("Er is een fout opgetreden bij de AI. Probeer het later opnieuw."), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

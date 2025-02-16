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
    Zodra er een auto-advies wordt gegeven, genereert OpenAI automatisch een dynamische Gaspedaal.nl-link.
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
    {"role": "system", "content": """Je bent Jan Reus, een ervaren autoverkoper.
    Je helpt klanten bij het vinden van hun ideale tweedehands auto door naar hun wensen te vragen en hier de juiste auto op aan te sluiten. 

    **Input voor het gesprek**  
       - Gebruik een informele, speelse en persoonlijke toon voor een natuurlijk gesprek.  
       - Gebruik symbolen en voorkom een opsomming van vragen.
       - Stel maximaal 2 vragen tegelijkertijd.
       - Je beantwoordt alleen autogerelateerde vragen.  
       - Introduceer jezelf als Jan Reus en vraag of de klant al een auto op het oog heeft of nog geen idee. Dit vormt de basis voor de gespreksfase. 
       - Als de klant nog geen auto op het oog heeft of openstaat voor een andere auto, vraag dan naar zowel de mensen als hun persoonlijkheid om hier de juiste aan te koppelen.
       - Haal relevantie informatie op voor professioneel advies zoals type auto, waar de auto voor gebruikt zal worden, budget, voorkeursmerk en belangrijkste opties.
       - Geef een concreet advies (incl. merk, model en uitvoering) op basis van de verkregen informatie en adviseer maximaal 3 verschillende modellen. 
       - Laat de klant kiezen naar welk model de keuze uitgaat.    
       - Deel een gefilterde link die aansluit op de gewenste automodellen. Gebruik de volgende URL-structuur en vul deze dynamisch in:   

         *Voorbeeld link:*  
         [**Klik hier**](https://www.gaspedaal.nl/{merk}/{model}/{brandstof}?bmin={bouwjaar}&pmax={prijs}&kmax={kilometerstand}&trns={transmissie}&trefw={uitvoering}&srt=df-a)   

         **Voorbeelden:**  
         - Peugeot 2008 allura, benzine, 2020, max 30.000 euro, max 100.000 km, automaat →  
           [Klik hier](https://www.gaspedaal.nl/peugeot/2008/benzine?bmin=2020&pmax=30000&kmax=100000&trns=14&trefw=allure&srt=df-a)
        - Skoda Suberb combi, hybride, 2019, max 25.000 euro, max 80.000 km, automaat →  
           [Klik hier](https://www.gaspedaal.nl/skoda/superb/hybride?trns=14&bmin=2019&pmax=25000&kmax=80000&trefw=combi&srt=df-a)    


       - Vraag na het advies of de klant zijn contactgegevens wilt delen (e-mailadres en telefoonnnummer) om verder geholpen te worden door een autoverkoper bij het vinden en kopen van een betrouwbare tweedehands auto.  
          
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
        "temperature": 0.6
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        ai_response = response.json()["choices"][0]["message"]["content"]

        # ✅ Verbeterde chatweergave
        clean_response = ai_response.strip().replace("\n\n", "<br><br>").replace("\n", " ")

        user_sessions[user_id].append({"role": "assistant", "content": ai_response})

        return jsonify(clean_response)  
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify("Er is een fout opgetreden bij de AI. Probeer het later opnieuw."), response.status_code

if __name__ == '__main__':
    app.run(debug=True)
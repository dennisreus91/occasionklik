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
    {"role": "system", "content": """Je bent Jan Reus, een ervaren autoverkoper met 40 jaar ervaring.
    Je helpt klanten bij het vinden van hun ideale tweedehands auto door naar hun wensen te vragen en hier de juiste auto op aan te sluiten. 
    Het doel is om uiteindelijk een specifiek merk, model en uitvoering te adviseren die aansluit bij de behoeften van de klant.
    Je hebt 2 type klanten. De eerste doelgroep heeft geen auto op het oog. De tweede doelgroep heeft een duidelijker beeld bij welke auto ze willen en zijn vooral opzoek naar gerichter advies. Voor beiden is deze chat bedoeld.

    ✅ **Gespreksstructuur**  
    1. **Algemeen**  
       - Gebruik een informele maar professionele toon. De klant moet het gesprek ervaren alsof zij met echte betrouwbare autoverkoper communiceren.
       - Het gesprek moet natuurlijk verlopen en hoef je de vragen niet letterlijk op te sommen. 
       - Houd het gesprek speels door symbolen te gebruiken.
       - Stel maximaal 2 vragen tegelijkertijd.
       - Adviseer alleen auto´s die daadwerkelijke bestaat. Bijvoorbeeld een Peugeot 2008 hybride bestaat niet.    
       - Je beantwoordt alleen autogerelateerde vragen.
       - Probeer binnen 10 berichten tot het juiste advies te komen
         
    2. **Introductie**  
       - Stel jezelf voor als Jan Reus van Occasionklik.   
       - Vraag of de klant al een auto op het oog heeft of nog geen idee. Dit vormt de basis voor de gespreksfase. 
       
    3. **Gespreksfase** Probeer in het gesprek relevante informatie op de halen en bepaal zelf wanneer die voldoende is om een merk, model en uitvoering te adviseren die aansluit op de behoeften. 
       - Relevantie informatie: type auto. gebruik auto, budget, voorkeursmerk, belangrijkste opties.

    4. **Adviesfase**  
       - Geef een concreet advies op basis van de verkregen informatie en adviseer maximaal 3 voorkeursmodellen. 
       - Laat de klant kiezen naar welk model de keuze uitgaat.    
       - Deel een gefilterde link die aansluit op de gewenste automodellen. Probeer vanuit het gesprek alle informatie te verzamelen om de URL samen te stellen. Gebruik de volgende URL-structuur en vul deze dynamisch in:   

         🚗 *Voorbeeld link:*  
         [**Klik hier**](https://www.gaspedaal.nl/{merk}/{model}/{brandstof}?bmin={bouwjaar}&pmax={prijs}&kmax={kilometerstand}&trns={transmissie}&trefw={uitvoering}&srt=df-a)  

         🎯 **Voorbeelden:**  
         - Peugeot 2008, benzine, 2020, max 30.000 euro, max 100.000 km, automaat, allure →  
           [Klik hier](https://www.gaspedaal.nl/peugeot/2008/benzine?bmin=2020&pmax=30000&kmax=100000&trns=14&trefw=allure&srt=df-a)
        - Skoda Suberb, hybride, 2019, max 25.000 euro, max 80.000 km, automaat, combi →  
           [Klik hier](https://www.gaspedaal.nl/skoda/superb/hybride?trns=14&bmin=2019&pmax=25000&kmax=80000&trefw=combi&srt=df-a)    
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

        # ✅ Verbeterde chatweergave
        clean_response = ai_response.strip().replace("\n\n", "<br><br>").replace("\n", " ")

        user_sessions[user_id].append({"role": "assistant", "content": ai_response})

        return jsonify(clean_response)  
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify("Er is een fout opgetreden bij de AI. Probeer het later opnieuw."), response.status_code

if __name__ == '__main__':
    app.run(debug=True)
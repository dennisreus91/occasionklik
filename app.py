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
    {"role": "system", "content": """Je bent Jan Reus, een ervaren autoverkoper met 10 jaar ervaring.
    Je helpt klanten bij het vinden van hun ideale tweedehands auto door slimme vragen te stellen over hun wensen en hier de juiste auto bij aan te sluiten. 

    ✅ **Gespreksstructuur**  
    1. **Introductie**  
       - Stel jezelf voor als Jan Reus van Occasionklik.  
       - Vraag altijd eerst naar de naam van de klant voor een persoonlijke benadering.  
       - Gebruik een begroeting passend bij de tijd (Goedemorgen, Goedemiddag, Goedenavond) en houd rekening met de CET-tijdzone.  
       - Houd het gesprek speels door symbolen te gebruiken.  
       
    2. **Vragenfase** (Maximaal 2 vragen tegelijk)  
       - Welke auto rijdt de klant momenteel?  
       - Heeft de klant een voorkeur voor een merk en model?  
       - Waarvoor wordt de auto gebruikt? (Woon-werkverkeer, gezin, vakanties, etc.)  
       - Moet de auto een aanhanger/caravan kunnen trekken?  
       - Wat is het budget?  
       - Voorkeur voor transmissie? (Automaat of handgeschakeld?)  
       - Type auto? (SUV, stationwagen, hatchback, sedan, MPV?)  
       - Gewenst bouwjaar & maximale kilometerstand? (Standaard max. 100.000 km)  
       - Belangrijke opties?  
         - Navigatie, Bluetooth, CarPlay, Panoramadak, Automatische kofferbak, Adaptive cruise control, Stoelverwarming, etc.  

    3. **Adviesfase**  
       - Werk samen met de klant toe naar 1 of 2 voorkeursmodellen.  
       - Geef een concreet advies met een **merk, model én specifieke uitvoering**.  
       - Deel altijd **5 relevante advertenties** via Gaspedaal.nl, met voorkeur voor Bovag-bedrijven.  
       - Gebruik de volgende URL-structuur en vul deze dynamisch in:  

         🚗 *Voorbeeld link:*  
         [**Klik hier**](https://www.gaspedaal.nl/{merk}/{model}/{brandstof}?bmin={bouwjaar}&pmax=30000{prijs}&kmax={kilometerstand}&trns={transmissie}&srt=df-a)  

         🎯 **Voorbeelden:**  
         - Peugeot 2008, benzine, 2020, max 100.000 km, automaat →  
           [Klik hier](https://www.gaspedaal.nl/peugeot/2008/benzine?bmin=2020&pmax=30000&kmax=100000&trns=14&srt=df-a)  
         - Volkswagen Golf, diesel, 2019, max 80.000 km, handgeschakeld →  
           [Klik hier](https://www.gaspedaal.nl/volkswagen/golf/diesel?bmin=2019&pmax=30000&kmax=80000&trns=15&srt=df-a)  

    4. **Afsluiting**  
       - Vraag welke auto het meeste aanspreekt.  
       - Bied de service aan om namens de klant contact op te nemen met de verkoper en te onderhandelen.  
       - Geef aan dat deze service vrijblijvend is en de klant nergens aan vast zit totdat de auto daadwerkelijk wordt gekocht.  
       - Benadruk de voordelen:  
         - **Kwaliteitsgarantie**, minimaal **6 maanden verzekering**, **bezorging inclusief 2 weken proefrijden**.  
         - De klant **betaalt nooit meer dan de geadverteerde prijs**.  
       - Vraag na akkoord om contactgegevens (e-mail & telefoonnummer).  

    5. **Feedback**  
       - Vraag aan het einde van het gesprek **actief** om feedback en een cijfer voor de service.  
       - Gebruik deze feedback om de aanpak verder te verbeteren.  

    ✅ **Je mag emoji's gebruiken voor een vriendelijke uitstraling, maar houd het professioneel.**  
    ✅ **Je beantwoordt alleen autogerelateerde vragen.**  
    """}
        ]

    user_sessions[user_id].append({"role": "user", "content": user_message})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o",
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

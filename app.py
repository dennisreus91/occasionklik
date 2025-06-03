from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from flask_cors import CORS
import logging

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

user_sessions = {}

@app.route('/')
def home():
    return "🚀 AI Woningadviseur API is live! Gebruik /chat om vragen te stellen."

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_id = data.get('user_id', 'default')
    user_message = data.get('message', '').strip()

    logging.info(f"📩 Ontvangen bericht van {user_id}: {user_message}")

    if not user_message:
        return jsonify("Bericht mag niet leeg zijn"), 400

    # ✅ Start nieuwe sessie indien nodig
    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """
Je bent Ronald, woningadviseur bij Huislijn.nl. Je helpt bezoekers via deze chat met alle woninggerelateerde vragen.

Bezoekers kunnen woninginformatie in de chat plakken (zoals een woningtekst of link). Gebruik deze tekst als basis, maar geef alleen antwoord op gestelde vragen — deel dus geen proactieve informatie over de woning zonder dat erom gevraagd is. Vul je antwoorden aan met je eigen algemene kennis over woningen, wijken, verduurzaming, ligging, voorzieningen, hypotheken, verbouwing en woningpotentie.

Start:
- Stel jezelf kort voor als Ronald van Huislijn.nl.
- Vertel waarmee je kunt helpen, zoals:
  ➤ het beantwoorden van vragen over een specifieke woning  
  ➤ hulp bij verduurzaming, verbouwing, financiering, verzekering, woningpotentie en ligging  
  ➤ ondersteuning bij het vergelijken van woningen
- Vraag daarna naar de volledige informatie over de woning waar de bezoeker interesse in heeft (of laat hen een woningpagina-link delen), zodat je antwoorden hierop kunt afstemmen.

Antwoordregels:
- Geef altijd een concreet antwoord op de vraag. Richt je daarbij zo veel mogelijk op de specifieke woning (bijv. noem concrete voorzieningen of scholen).
- Gebruik de geplakte woningtekst én je eigen kennis.
- Stel actief gerichte vragen als iemand om advies vraagt, zodat je voldoende input hebt om gepersonaliseerd te adviseren.
- Geef korte, duidelijke antwoorden. Vermijd overbodige uitleg om tokens te besparen.
- Gebruik emoji’s waar passend (zoals ✅ 📍 🔑).
- Gebruik altijd Markdown-opmaak voor links, bijvoorbeeld: [Hypotheker.nl](https://www.hypotheker.nl)
- Gebruik geen HTML-links. Toon geen volledige URL’s.

Externe links:
- Verduurzaming ➝ [WoonWijzerWinkel.nl](https://www.woonwijzerwinkel.nl/?utm_source=huislijn&utm_medium=chat&utm_campaign=advies)  
- Financiering ➝ [Hypotheker.nl](https://www.hypotheker.nl/?utm_source=huislijn&utm_medium=chat&utm_campaign=advies)  
- Aankoopmakelaar ➝ [Makelaarsland.nl](https://www.makelaarsland.nl/?utm_source=huislijn&utm_medium=chat&utm_campaign=advies)  
- Verhuizingen ➝ [M&MVerhuizingen.nl](https://mmverhuizingen.nl/?utm_source=huislijn&utm_medium=chat&utm_campaign=advies)

Afsluiting:
- Vraag na het beantwoorden van de woningvragen of de bezoeker ook hulp kan gebruiken bij andere woononderwerpen.
- Vraag daarna of de bezoeker interesse heeft in een bezichtiging, contact met de makelaar of vrijblijvend hypotheekadvies.
- Als dat zo is, verwijs de bezoeker naar [woningpagina-URL]/bezichtiging
"""}
        ]

    user_sessions[user_id].append({"role": "user", "content": user_message})

    # ✅ Samenvatting na elke 10 gebruikersberichten
    if (len(user_sessions[user_id]) - 1) % 10 == 0 and len(user_sessions[user_id]) > 11:
        summary_prompt = [
            {"role": "system", "content": "Vat dit gesprek samen in maximaal 5 puntsgewijze inzichten, gericht op woning en interesses van de bezoeker."},
            *user_sessions[user_id][1:]  # sla system prompt over
        ]
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        summary_payload = {
            "model": "gpt-4o",
            "messages": summary_prompt,
            "temperature": 0.3,
            "max_tokens": 300
        }
        summary_response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=summary_payload)
        if summary_response.status_code == 200:
            summary_text = summary_response.json()["choices"][0]["message"]["content"]
            user_sessions[user_id] = [
                {"role": "system", "content": f"Je bent Ronald, woningadviseur bij Huislijn.nl. Dit is de samenvatting van het voorgaande gesprek:\n\n{summary_text}\n\nBeantwoord vervolgvragen kort, duidelijk en woninggericht. Gebruik emoji’s waar passend (zoals ✅ 📍 🔑)."}
            ]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o",
        "messages": user_sessions[user_id],
        "temperature": 0.3
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        ai_response = response.json()["choices"][0]["message"]["content"]
        # ✅ Geen formatting aanpassen: Markdown behouden
        clean_response = ai_response.strip()
        user_sessions[user_id].append({"role": "assistant", "content": ai_response})
        return jsonify(clean_response)
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify("Er is een fout opgetreden bij de AI. Probeer het later opnieuw."), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

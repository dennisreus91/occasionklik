from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from flask_cors import CORS
import logging
from bs4 import BeautifulSoup
import re
import json

# ✅ Omgeving instellen
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Flask-app configureren
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

user_sessions = {}
scraped_urls = set()

@app.route('/')
def home():
    return "🚀 AI Woningadviseur API is live! Gebruik /chat om vragen te stellen."

def scrape_woning_info(url):
    try:
        page = requests.get(url, timeout=5)
        soup = BeautifulSoup(page.text, 'html.parser')

        json_ld_script = soup.find("script", type="application/ld+json")
        json_ld = json.loads(json_ld_script.string) if json_ld_script else {}

        adres = json_ld.get("address", {})
        pricing = json_ld.get("offers", {}).get("price", "Onbekend")
        straat = adres.get("streetAddress", "")
        plaats = adres.get("addressLocality", "")
        postcode = re.search(r'\d{4}[A-Z]{2}', json_ld.get("description", ""))

        beschrijving = soup.select_one(".object-section-beschrijving")
        kenmerken = soup.select_one(".object-section-kenmerken")
        makelaar_naam = soup.select_one(".broker-logo h2")

        info = {
            "url": url,
            "adres": f"{straat}, {postcode.group() if postcode else ''} {plaats}",
            "prijs": f"€{pricing}",
            "makelaar": makelaar_naam.text.strip() if makelaar_naam else "Onbekend",
            "beschrijving": beschrijving.text.strip() if beschrijving else "",
            "kenmerken": kenmerken.text.strip() if kenmerken else ""
        }
        return info
    except Exception as e:
        logging.warning(f"⚠️ Scraping mislukt: {e}")
        return None

def maak_samenvatting(info_dict):
    prompt = f"""Vat deze woninginformatie samen in maximaal 5 puntsgewijze inzichten:
Adres: {info_dict['adres']}
Vraagprijs: {info_dict['prijs']}
Makelaar: {info_dict['makelaar']}
Beschrijving: {info_dict['beschrijving']}
Kenmerken: {info_dict['kenmerken']}"""

    messages = [
        {"role": "system", "content": "Je bent een assistent die woninginformatie bondig samenvat."},
        {"role": "user", "content": prompt}
    ]

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        },
        json={"model": "gpt-4o", "messages": messages, "max_tokens": 300, "temperature": 0.3}
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        logging.warning(f"❌ Samenvatten mislukt: {response.text}")
        return None

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_id = data.get('user_id', 'default')
    user_message = data.get('message', '').strip()
    url = data.get('url', '').strip()

    logging.info(f"📩 Ontvangen bericht van {user_id}: {user_message} (URL: {url})")

    if not user_message:
        return jsonify("Vraag mag niet leeg zijn"), 400

    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": "Je bent Ronald, woningadviseur bij Huislijn.nl. Je helpt bezoekers via deze chat met woningvragen."}
        ]

    # ✅ Voeg woninginformatie toe indien nieuw
    if url and url not in scraped_urls:
        info = scrape_woning_info(url)
        if info:
            samenvatting = maak_samenvatting(info)
            if samenvatting:
                user_sessions[user_id].insert(1, {"role": "system", "content": f"Samenvatting woninginformatie:\n{samenvatting}"})
                scraped_urls.add(url)

    user_sessions[user_id].append({"role": "user", "content": user_message})

    # ✅ Samenvatten bij elke 10 vragen
    if (len(user_sessions[user_id]) - 1) % 10 == 0 and len(user_sessions[user_id]) > 11:
        summary_prompt = [
            {"role": "system", "content": "Vat dit gesprek samen in maximaal 5 puntsgewijze inzichten."},
            *user_sessions[user_id][1:]
        ]
        summary_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": "gpt-4o", "messages": summary_prompt, "max_tokens": 300}
        )
        if summary_response.status_code == 200:
            summary_text = summary_response.json()["choices"][0]["message"]["content"]
            user_sessions[user_id] = [
                {"role": "system", "content": f"Je bent Ronald van Huislijn.nl. Samenvatting tot nu toe:\n{summary_text}"}
            ]

    # ✅ AI-antwoord genereren
    payload = {
        "model": "gpt-4o",
        "messages": user_sessions[user_id],
        "temperature": 0.3
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }, json=payload)

    if response.status_code == 200:
        ai_response = response.json()["choices"][0]["message"]["content"]
        user_sessions[user_id].append({"role": "assistant", "content": ai_response})
        return jsonify(ai_response.strip())
    else:
        logging.error(f"❌ OpenAI API-fout: {response.text}")
        return jsonify("Er is een fout opgetreden bij de AI. Probeer het later opnieuw."), response.status_code

if __name__ == '__main__':
    app.run(debug=True)

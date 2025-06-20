from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
from flask_cors import CORS
import logging
import json, re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

user_sessions = {}
user_scraped_urls = {}

# 🔹 HEADERS voor scraping
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8"
}

def is_valid_woning_url(url: str) -> bool:
    return bool(re.search(r"/(\d{6,})/", url))

def extract_extra_fields(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    beschrijving = soup.select_one(".object-section-beschrijving .content")
    kenmerken = soup.select_one(".object-section-kenmerken")
    makelaar_naam_el = soup.select_one(".object-sections-makelaar h3")
    makelaar_tel = soup.select_one(".object-sections-makelaar small")
    return {
        "beschrijving_html": beschrijving.get_text(strip=True, separator=" ") if beschrijving else "",
        "kenmerken_html": kenmerken.get_text(strip=True, separator=" | ") if kenmerken else "",
        "makelaar_naam": makelaar_naam_el.get_text(strip=True) if makelaar_naam_el else "",
        "makelaar_telefoon": makelaar_tel.get_text(strip=True).replace("Tel:", "").strip() if makelaar_tel else ""
    }

def get_jsonld_from_html(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            obj = json.loads(tag.string or "")
            t = obj.get("@type", [])
            if (isinstance(t, list) and "Apartment" in t) or (isinstance(t, str) and t in ("Apartment", "Product")):
                return obj
        except json.JSONDecodeError:
            continue
    return None

def scrape_listing_data(url: str, timeout: int = 6):
    try:
        html = requests.get(url, headers=HEADERS, timeout=timeout).text
        jsonld = get_jsonld_from_html(html)
        extra = extract_extra_fields(html)
        if jsonld:
            return {
                "type_woning": jsonld.get("@type"),
                "url": jsonld.get("url"),
                "straatadres": jsonld.get("address", {}).get("streetAddress"),
                "plaats": jsonld.get("address", {}).get("addressLocality"),
                "regio": jsonld.get("address", {}).get("addressRegion"),
                "prijs": jsonld.get("offers", {}).get("price"),
                "omschrijving_jsonld": jsonld.get("description"),
                **extra
            }
    except:
        pass
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=HEADERS["User-Agent"], locale="nl-NL")
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            html = page.content()
            json_text = page.evaluate("""() => {
                const el = document.querySelector('script[type="application/ld+json"]');
                return el ? el.innerText : null;
            }""")
            jsonld = json.loads(json_text) if json_text else None
            extra = extract_extra_fields(html)
            if jsonld:
                return {
                    "type_woning": jsonld.get("@type"),
                    "url": jsonld.get("url"),
                    "straatadres": jsonld.get("address", {}).get("streetAddress"),
                    "plaats": jsonld.get("address", {}).get("addressLocality"),
                    "regio": jsonld.get("address", {}).get("addressRegion"),
                    "prijs": jsonld.get("offers", {}).get("price"),
                    "omschrijving_jsonld": jsonld.get("description"),
                    **extra
                }
        except:
            return None
        finally:
            browser.close()

@app.route('/')
def home():
    return "🚀 AI Woningadviseur API is live! Gebruik /chat om vragen te stellen."

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_id = data.get('user_id', 'default')
    user_message = data.get('message', '').strip()
    woning_url = data.get('woning_url', '').strip()

    if not user_message:
        return jsonify("Bericht mag niet leeg zijn"), 400

    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """
Je bent Ronald, woningadviseur bij Huislijn.nl. Je helpt bezoekers via deze chat met alle woninggerelateerde vragen.
... (volledige systeem prompt)
"""}
        ]
        user_scraped_urls[user_id] = set()

    woning_info = ""
    if woning_url and is_valid_woning_url(woning_url) and woning_url not in user_scraped_urls[user_id]:
        scraped = scrape_listing_data(woning_url)
        if scraped:
            woning_info = f"\nWoninginformatie: {json.dumps(scraped, ensure_ascii=False)}"
            user_scraped_urls[user_id].add(woning_url)

    prompt_content = f"Vraag: {user_message}\nURL: {woning_url}{woning_info}"
    user_sessions[user_id].append({"role": "user", "content": prompt_content})

    if (len(user_sessions[user_id]) - 1) % 10 == 0 and len(user_sessions[user_id]) > 11:
        summary_prompt = [
            {"role": "system", "content": "Vat dit gesprek samen in maximaal 5 puntsgewijze inzichten, gericht op woning en interesses van de bezoeker."},
            *user_sessions[user_id][1:]
        ]
        response = requests.post("https://api.openai.com/v1/chat/completions", headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"
        }, json={"model": "gpt-4o", "messages": summary_prompt, "temperature": 0.3, "max_tokens": 300})
        if response.status_code == 200:
            summary = response.json()["choices"][0]["message"]["content"]
            user_sessions[user_id] = [{"role": "system", "content": f"Je bent Ronald, woningadviseur bij Huislijn.nl. Dit is de samenvatting van het voorgaande gesprek:\n\n{summary}\n\nBeantwoord vervolgvragen kort, duidelijk en woninggericht. Gebruik emoji’s waar passend (zoals ✅ 📍 🔑)."}]

    chat_response = requests.post("https://api.openai.com/v1/chat/completions", headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"
    }, json={"model": "gpt-4o", "messages": user_sessions[user_id], "temperature": 0.3})

    if chat_response.status_code == 200:
        reply = chat_response.json()["choices"][0]["message"]["content"].strip()
        user_sessions[user_id].append({"role": "assistant", "content": reply})
        return jsonify(reply)
    else:
        logging.error(f"❌ OpenAI API-fout: {chat_response.text}")
        return jsonify("Er is een fout opgetreden bij de AI. Probeer het later opnieuw."), chat_response.status_code

if __name__ == '__main__':
    app.run(debug=True)

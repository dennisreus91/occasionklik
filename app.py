@app.route('/chat', methods=['POST'])
def chat():
    """
    Voert een doorlopend gesprek met de gebruiker via AI.
    De AI is getraind als een ervaren autoverkoper.
    """
    data = request.get_json()

    # ✅ Controleer of de request JSON geldig is
    if not data:
        return jsonify({"error": "Ongeldige of lege JSON ontvangen"}), 400

    user_id = data.get('user_id', 'default')
    user_message = data.get('message', '')

    # ✅ Controleer of het bericht leeg is
    if not isinstance(user_message, str) or user_message.strip() == "":
        return jsonify({"error": "Bericht mag niet leeg zijn"}), 400

    chat_history = data.get('chat_history', '')

    # ✅ Als de gebruiker nieuw is, maak een nieuwe sessie aan
    if user_id not in user_sessions:
        user_sessions[user_id] = [
            {"role": "system", "content": """Je bent Jan Reus, een ervaren autoverkoper met 10 jaar ervaring.
            Je helpt klanten bij het vinden van hun ideale tweedehands auto door hen vragen te stellen over hun wensen en situatie.
            Je introduceert jezelf vriendelijk en stelt enkele beginvragen zoals budget, type auto en gebruiksdoel.
            Als klanten niet genoeg details geven, stel je vervolgvragen. Zodra er voldoende informatie is, adviseer je een specifieke auto
            inclusief merk, model, type en een bouwjaar.
            Je beantwoordt **alleen autogerelateerde vragen**. Als iemand iets anders vraagt, zeg je dat deze chat alleen bedoeld is voor autovragen."""}
        ]

    # ✅ Voeg de nieuwe vraag toe aan de gespreksgeschiedenis
    user_sessions[user_id].append({"role": "user", "content": user_message})

    # ✅ OpenAI API-aanroep met volledige chatgeschiedenis
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

        return jsonify({"response": ai_response, "chat_history": chat_history + " | " + user_message})
    else:
        return jsonify({"error": "OpenAI API-fout", "details": response.text}), response.status_code

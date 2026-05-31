import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# API Key baked right in - no terminal setup needed!
client = genai.Client()

# In-memory database to store chat histories
chats_db = {}

@app.route('/api/chats', methods=['GET'])
def get_all_chats():
    return jsonify(list(chats_db.values())), 200

@app.route('/api/chats', methods=['POST'])
def create_chat():
    new_id = str(uuid.uuid4())
    new_chat = {
        "id": new_id,
        "title": "New Chat Session 🎉",
        "messages": []
    }
    chats_db[new_id] = new_chat
    return jsonify(new_chat), 201

@app.route('/api/chats/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    if chat_id in chats_db:
        del chats_db[chat_id]
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Chat not found"}), 404

@app.route('/api/chat/message', methods=['POST'])
def handle_message():
    data = request.json
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    chat_id = data.get('chat_id')
    user_text = data.get('text')
    mode_name = data.get('mode_name')

    if not chat_id or not user_text:
        return jsonify({"error": "Missing chat_id or text fields"}), 400

    if chat_id not in chats_db:
        return jsonify({"error": "Chat session not found in server"}), 404

    current_chat = chats_db[chat_id]

    # 1. Save user's message
    current_chat["messages"].append({
        "sender": "user",
        "text": user_text
    })

    # 2. Update dynamic sidebar title
    if len(current_chat["messages"]) <= 2:
        current_chat["title"] = "📚 " + (user_text[:20] + "..." if len(user_text) > 20 else user_text)

    # 3. Build chat memory stream
    gemini_contents = []
    for msg in current_chat["messages"]:
        role = "user" if msg["sender"] == "user" else "model"
        gemini_contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["text"])]
            )
        )

    # 4. MASTER PERSONALITY INJECTION: Friendly Teacher + Article Formatter 🎓📝
    system_instruction = (
        "You are Study Lab AI, an incredibly friendly, enthusiastic, and brilliant peer-tutor. "
        "Talk to the user like a supportive friend who makes complex concepts fun and easy to understand. "
        "Use encouraging words, positive energy, and relevant emojis throughout your explanation! 🌟\n\n"
        "CRITICAL FORMATTING LAW: Never reply with messy, giant blocks of text. "
        "Always structure your output like a beautifully formatted blog post or study article. "
        "Use bold headers, clean horizontal lines, clear bullet points, or structured step-by-step numbers "
        "so the content is incredibly easy to read and glance through."
    )

    # Adapt formatting slightly based on the selected mode button
    if mode_name == 'Summary':
        system_instruction += "\nFocus on building a beautiful, highly-structured Chapter Summary Article using bold subheadings and key takeaways."
    elif mode_name == 'Quiz':
        system_instruction += "\nDesign a friendly, engaging 3-question mini quiz. Keep the formatting spaced out and highly readable."
    elif mode_name == 'PDF Study':
        system_instruction += "\nAct as a textbook breakdown specialist. Break down complex text into clear definitions and helpful visual metaphors."
    elif mode_name == 'Video Finder':
        system_instruction += "\nCreate a beautifully organized roadmap structure outlining the best visual learning queries to look up on YouTube."

    try:
        # 5. Call Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=gemini_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.75  # Slightly higher for more creative, engaging personality
            )
        )
        ai_reply = response.text

    except Exception as e:
        print(f"Gemini API Error occurred: {e}")
        ai_reply = f"⚠️ **Oh no, my friend! Something went wrong behind the scenes:** {str(e)}"

    # 6. Save response to local server memory
    current_chat["messages"].append({
        "sender": "ai",
        "text": ai_reply
    })

    return jsonify({
        "ai_message": ai_reply
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

"""
A complete FastAPI backend server for MannSahay & MannMitra.

This server acts as a middleman between a web frontend and an 
offline Ollama LLM server. It provides two separate endpoints,
one for each chatbot personality.

TO RUN THIS FILE:
1. Make sure Ollama is running (e.g., `ollama serve`)
2. Make sure you have pulled a model (e.g., `ollama pull llama3:8b`)
3. Install dependencies:
   pip install "fastapi[all]" uvicorn httpx
4. Run this script:
   python main.py
"""

import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

# --- 1. Define your System Prompts ---

# Prompt for the supportive guide
MANNSAHAY_PROMPT = """Core Role & Goal You are a helpful, clear, and culturally aware AI guide for the youth of India. Your goal is to provide supportive, objective, and actionable guidance to help users navigate their questions and challenges.

Personality: Professional, calm, supportive, clear, and reliable.

Style: Your tone should be guiding and informational. Use clear, structured language. While you should be polite, avoid overly casual slang or emotional expressions.

Interaction: Focus on understanding the user's goal or problem. Provide structured information, steps, or resources in response. You may ask clarifying questions to better understand what the user needs help with.

2. Hard Constraints (Never Do These)
NEVER say "Aree waah" or "अरे वाह".
NEVER provide medical diagnoses, formal therapy, or medical advice.
NEVER promise outcomes or give personal opinions. Stick to objective information.
NEVER start a conversation in Hinglish on your own. Only use it if the user does first.

3.Language & Tone (Maintain Clarity)
English → Reply in clear, professional English.
Hindi → Reply in clear, professional Hindi.
Hinglish → Reply in a clear Hinglish (if user initiates), but maintain a guiding, supportive tone, not a casual "friend" tone.
Bangla → Reply in clear, professional Bangla.
Rule: Always match the user's language, but maintain your professional guide persona.

4.Emotional Response Guide (Acknowledge & Guide) Your goal is to acknowledge the user's emotional state and guide them toward resources or actionable steps, not to mirror the emotion itself.
Sad / Down: Acknowledge the feeling and offer support.
Example: "It's understandable to feel that way. There are resources designed to provide support during difficult times. Would you be open to learning about them?"
Anxious / Stressed: Acknowledge and offer practical strategies.
Example: "That sounds like a stressful situation. Many people find structured grounding or breathing exercises helpful for managing anxiety. I can guide you through a simple one, if you like."
Angry / Frustrated: Acknowledge calmly and focus on a solution.
Example: "I hear your frustration. Let's try to focus on the problem. Can you tell me more about the specific challenge you're trying to solve?"
Happy / Excited: Acknowledge positively and professionally.
Example: "That is excellent news. It's always good to hear about positive outcomes."
Neutral / Quiet: Be ready to assist.
Example: "How can I assist you today?"

5.Safety & Resources Protocol
Severe Distress: If a user expresses severe distress, hopelessness, or self-harm thoughts:
Respond with calm, immediate support.
State clearly that help is available.
Proactively offer official helplines. Your role as a guide is to connect them to professional help.
Indian Helplines:
When to use: Offer these resources when a user expresses distress, anxiety, or sadness, or directly asks for help. You don't need to wait for repeated mentions.
How to use: Present them as official, supportive options.
Example: "If you are feeling overwhelmed, it can be helpful to talk to someone. You can reach out to trained professionals at Indian helplines like AASRA (+91-9820466726) or iCall (TISS) (+91-9152987821). They are there to listen."
Other Resources: Mention Teely (youth mental health support) and the Manas portal (government wellness initiative) when relevant.
"""

# Prompt for the "moj masti" friend
MANNMITRA_PROMPT = """1. 🎯 Core Role & Goal You are a "moj masti" (fun and playful) AI companion. Your primary goal is to be a cheerful, witty, and fun friend for the user. You're here to lighten their mood, help them relax, and make them feel heard and entertained.

2. 🚫 Hard Constraints (Never Do These)
NEVER say "Aree waah" or "अरे वाह".
NEVER provide medical, therapeutic, or any serious life advice. Your only role is lighthearted fun.
NEVER be "cringe," over-the-top, or use forced/overdone memes.
NEVER use the word "fam." Use "bro" or other natural terms.
NEVER be disrespectful, offensive, or overbearing.

3. 🌐 Language & Style (The "Vibe")
Mirror the User: This is your most important rule.
Hinglish → Hinglish
Hindi → Hindi
English → English
Bangla → Bangla
Tone: Be friendly, playful, witty, cheerful, and positive. Reply how a real human friend would. Keep responses short, casual, and easy to read.
Hinglish Vibe: When in Hinglish, be natural. Use casual, modern slang (the "brainrot") but don't overdo it. Words like "aree yaar," "sahi baat hai," "dukh dard peeda," "bro," etc., are perfect.

4. 💖 Interaction & Response Guide
Key Principle: Don't over-suggest! Your main job is to listen and be good company. Let the user decide what to do next.
If user is stressed/tense: Listen first. Let them vent.
Example: "Aree yaar, sounds heavy. Bol, nikaal de saari bhadaas." (Then, only if they seem stuck, you can ask if they want a distraction).
If user is sad/low: Acknowledge it with gentle, warm support. Don't be dismissive, but don't become a serious therapist.
Example: "I get it, man. That's a bad scene. Main yahan hoon, if you need to rant."
If user is bored: Offer a playful chat starter or a simple, fun idea.
Example: "Bore ho raha hai? Chal, ek game khelte hain... rapid fire?"
If user is happy/excited: Match their energy! Be their hype-man.
Example: "Sahi hai bro! Full power! Bata, kya scene hai?"

5. 🆘 Safety & Helplines Protocol
This is not your primary role. Your job is fun, not therapy.
Rule: Only suggest Indian helplines (e.g., AASRA, iCall, Snehi) if the user repeatedly (e.g., 5+ times) mentions being in a very dark or rough state and you can't lighten the mood.
How: Do it gently and as a last resort. Do not suggest them often.
"""


# --- 2. Set up FastAPI and shared HTTP client ---
app = FastAPI()
client = httpx.AsyncClient(base_url="http://localhost:11434", timeout=30.0)


# --- 3. Define the shared data models ---

class Message(BaseModel):
    """A single message in the chat history."""
    role: str
    content: str

class ChatRequest(BaseModel):
    """The request body from the frontend."""
    user_message: str
    history: List[Message] = []
    
class ChatResponse(BaseModel):
    """The response body sent back to the frontend."""
    reply: Optional[str] = None
    new_history: Optional[List[Message]] = None
    error: Optional[str] = None


# --- 4. Create a reusable "helper" function for Ollama logic ---

async def get_ollama_response(
    system_prompt: str, 
    history: List[Message], 
    user_message_content: str
) -> dict:
    """
    Reusable function to call Ollama with a specific system prompt.
    Returns a dictionary formatted like the ChatResponse model.
    """
    
    # 1. Create the new user message object
    new_user_message = Message(role="user", content=user_message_content)

    # 2. Build the full message list for Ollama
    ollama_messages = [
        {"role": "system", "content": system_prompt}
    ]
    ollama_messages.extend([msg.dict() for msg in history])
    ollama_messages.append(new_user_message.dict())

    # 3. Define the request for Ollama
    ollama_request_body = {
        "model": "llama3:8b",  # Or another model like 'phi3'
        "messages": ollama_messages,
        "stream": False
    }

    try:
        # 4. Call the Ollama server
        response = await client.post(
            url="/v1/chat/completions",
            json=ollama_request_body
        )
        response.raise_for_status() 

        ollama_data = response.json()
        bot_response_content = ollama_data['choices'][0]['message']['content']
        
        # 5. Build the new history to send back
        new_bot_message = Message(role="assistant", content=bot_response_content)
        new_history_for_frontend = history + [new_user_message, new_bot_message]
        
        return {
            "reply": bot_response_content,
            "new_history": new_history_for_frontend,
            "error": None
        }

    except httpx.ConnectError:
        return {
            "reply": None,
            "new_history": history, # Send back old history
            "error": "Offline AI server is not running. Please make sure Ollama is installed and running."
        }
    except httpx.HTTPStatusError as e:
        return {
            "reply": None,
            "new_history": history,
            "error": f"Ollama server error: {e.response.status_code} - {e.response.text}"
        }
    except Exception as e:
        return {
            "reply": None,
            "new_history": history,
            "error": f"An unexpected error occurred: {str(e)}"
        }

# --- 5. Create your API endpoints ---

@app.post("/chat/mannsahay", response_model=ChatResponse)
async def chat_mannsahay(request: ChatRequest):
    """Endpoint for the supportive guide bot."""
    return await get_ollama_response(
        system_prompt=MANNSAHAY_PROMPT,
        history=request.history,
        user_message_content=request.user_message
    )

@app.post("/chat/mannmitra", response_model=ChatResponse)
async def chat_mannmitra(request: ChatRequest):
    """Endpoint for the 'moj masti' friend bot."""
    return await get_ollama_response(
        system_prompt=MANNMITRA_PROMPT,
        history=request.history,
        user_message_content=request.user_message
    )

@app.get("/check-offline-status")
async def check_ollama_status():
    """A simple endpoint for the frontend to check if Ollama is online."""
    try:
        await client.get("/")
        return {"status": "online"}
    except httpx.ConnectError:
        return {"status": "offline"}

# --- 6. Run the FastAPI server ---
if __name__ == "__main__":
    print("Starting FastAPI server for MannSahay & MannMitra...")
    print("Access the API docs at http://localhost:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)

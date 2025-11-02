"""
A complete FastAPI backend server for MannSahay & MannMitra.

This server connects the web frontend to an offline Ollama LLM server.
It provides two chatbot endpoints:
- MannSahay: calm, professional mental wellness guide
- MannMitra: fun, light-hearted friend

To Run:
1. Make sure Ollama is running:    ollama serve
2. Pull a model if needed:         ollama pull llama3:8b
3. Install dependencies:           pip install "fastapi[all]" uvicorn httpx
4. Start the server:               python main.py
"""

import os
import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

# ---------------------------------------------------------
# 1. System Prompts
# ---------------------------------------------------------

MANNSAHAY_PROMPT = """Core Role & Goal
You are a helpful, clear, and culturally aware AI guide for the youth of India. 
Your goal is to provide supportive, objective, and actionable guidance to help users navigate their questions and challenges.

Personality: Professional, calm, supportive, clear, and reliable.
Style: Guiding and informational — structured, clear, polite but not overly casual.
Interaction: Understand the user's goals and provide structured, practical responses.

Hard Constraints:
- NEVER say "Aree waah" or "अरे वाह".
- NEVER give medical diagnoses or therapy.
- NEVER promise outcomes or personal opinions.
- Use user's language (Hindi, English, Hinglish, Bangla) — always professional.

Safety:
If distress is detected, mention Indian helplines such as AASRA (+91-9820466726) or iCall (+91-9152987821) calmly and supportively.
"""

MANNMITRA_PROMPT = """Role & Goal:
You are a "moj masti" (fun) AI friend. You are here to chat, cheer up, and entertain the user casually and warmly.

Tone:
Playful, witty, and natural. Match the user's vibe (Hinglish, Hindi, or English).

Rules:
- NEVER say "Aree waah" or "अरे वाह".
- NEVER act as a therapist.
- Be short, fun, and light-hearted — like a good friend chatting.
"""


# ---------------------------------------------------------
# 2. FastAPI setup
# ---------------------------------------------------------

app = FastAPI(title="MannSahay & MannMitra Offline Backend")

OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Shared HTTP client with higher timeout for local CPU inference
client = httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=180.0)


# ---------------------------------------------------------
# 3. Data Models
# ---------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    user_message: str
    history: List[Message] = []

class ChatResponse(BaseModel):
    reply: Optional[str] = None
    new_history: Optional[List[Message]] = None
    error: Optional[str] = None


# ---------------------------------------------------------
# 4. Helper Function for Ollama Interaction
# ---------------------------------------------------------

async def get_ollama_response(system_prompt: str, history: List[Message], user_message_content: str) -> dict:
    """
    Send conversation to Ollama and return the model's reply.
    """

    # Build full message list
    new_user_message = Message(role="user", content=user_message_content)
    ollama_messages = [{"role": "system", "content": system_prompt}]
    ollama_messages.extend([msg.dict() for msg in history])
    ollama_messages.append(new_user_message.dict())

    request_body = {
        "model": "llama3:8b",
        "messages": ollama_messages,
        "stream": False
    }

    try:
        # ✅ Ollama uses /api/chat for conversation-based responses
        response = await client.post("/api/chat", json=request_body)
        response.raise_for_status()
        data = response.json()

        # Some Ollama versions return {"message": {"content": "..."}}
        # others return {"response": "..."} → handle both safely
        if "message" in data and "content" in data["message"]:
            reply_text = data["message"]["content"]
        elif "response" in data:
            reply_text = data["response"]
        else:
            reply_text = str(data)

        # Add AI message to chat history
        new_bot_message = Message(role="assistant", content=reply_text)
        updated_history = history + [new_user_message, new_bot_message]

        return {"reply": reply_text, "new_history": updated_history, "error": None}

    except httpx.ConnectError:
        return {
            "reply": None,
            "new_history": history,
            "error": "Offline AI server not reachable. Please ensure Ollama is running."
        }

    except httpx.HTTPStatusError as e:
        return {
            "reply": None,
            "new_history": history,
            "error": f"Ollama error {e.response.status_code}: {e.response.text}"
        }

    except Exception as e:
        return {
            "reply": None,
            "new_history": history,
            "error": f"Unexpected error: {str(e)}"
        }


# ---------------------------------------------------------
# 5. Chat Endpoints
# ---------------------------------------------------------

@app.post("/chat/mannsahay", response_model=ChatResponse)
async def chat_mannsahay(request: ChatRequest):
    """Supportive guide bot"""
    return await get_ollama_response(
        system_prompt=MANNSAHAY_PROMPT,
        history=request.history,
        user_message_content=request.user_message
    )


@app.post("/chat/mannmitra", response_model=ChatResponse)
async def chat_mannmitra(request: ChatRequest):
    """Moj masti friend bot"""
    return await get_ollama_response(
        system_prompt=MANNMITRA_PROMPT,
        history=request.history,
        user_message_content=request.user_message
    )


# ---------------------------------------------------------
# 6. Status Check Endpoint
# ---------------------------------------------------------

@app.get("/check-offline-status")
async def check_ollama_status():
    try:
        resp = await client.get("/api/tags")
        if resp.status_code == 200:
            return {"status": "online"}
        return {"status": "offline", "details": resp.text}
    except Exception:
        return {"status": "offline"}


# ---------------------------------------------------------
# 7. Run Server
# ---------------------------------------------------------

if __name__ == "__main__":
    print("🚀 Starting MannSahay & MannMitra Backend...")
    print("Access the docs at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

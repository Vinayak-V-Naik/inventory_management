'''Groq LLM factory — one place that knows about API keys and model names.

Get a free key at https://console.groq.com and put it in .env:
    GROQ_API_KEY=gsk_...
Optionally override the model:
    GROQ_MODEL=llama-3.3-70b-versatile
'''

import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "llama-3.3-70b-versatile"


def groq_ready():
    '''True when a GROQ_API_KEY is available in the environment / .env'''
    return bool(os.getenv("GROQ_API_KEY"))


def get_llm(temperature=0.2):
    '''ChatGroq instance — raises with a helpful message if the key is missing'''
    if not groq_ready():
        raise RuntimeError(
            "GROQ_API_KEY is not set. Create a free key at https://console.groq.com "
            "and add GROQ_API_KEY=gsk_... to the .env file."
        )
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", DEFAULT_MODEL),
        temperature=temperature,
    )

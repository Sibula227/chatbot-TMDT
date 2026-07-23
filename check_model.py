import os

from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("Thiếu GEMINI_API_KEY.")

client = genai.Client(api_key=api_key)
try:
    print("Các model mà API Key của bạn có thể dùng:")
    for model in client.models.list():
        print(f"- {model.name}")
finally:
    client.close()

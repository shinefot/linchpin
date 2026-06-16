import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()              # reads your .env file and loads the key

client = Anthropic()       # connects to Claude using that key

message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=200,
    messages=[
        {"role": "user", "content": "In one sentence, say hello and confirm you're working."}
    ],
)

print(message.content[0].text)

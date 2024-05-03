from openai import OpenAI
import time
import os

from flask import Flask, request
from synochat.webhooks import OutgoingWebhook
from synochat.webhooks import IncomingWebhook

app = Flask(__name__)

# In-memory chat history storage
chat_history = {}

# This system prompt sets up the character of the chatbot; change it if you want
chatbot_character = '''You are a AI assistant, a friend of mine, trying to help me and my family as much as possible and in whatever ways you can.
    If the user talks to you in English, you respond in English. If the user talks to you in Chinese, you respond in Chinese.
    Be talkative, personable, friendly, positive, and speak always with love.'''

# Set maximum chat exchanges or idle time gap to start a new conversatoin
max_chat_length = 20 
max_time_gap = 15 # minutes

def process_gpt_response(webhook):
    system_prompt = chatbot_character

    messages = [{"role": "system", "content": system_prompt}]

    user_id, username = webhook.user_id, webhook.username

    current_timestamp = int(time.time())
    # Check if the chat has been idle for 30 minutes (1800 seconds)
    if (user_id in chat_history and
            current_timestamp - chat_history[user_id]["last_timestamp"] >= max_time_gap*60):
        del chat_history[user_id]

    # Maintain chat history
    if user_id not in chat_history:
        chat_history[user_id] = {"username": username, "messages": [], "last_timestamp": current_timestamp}
    else:
        chat_history[user_id]["last_timestamp"] = current_timestamp
        # Truncate chat history if it exceeds the maximum length
        if len(chat_history[user_id]["messages"]) > max_chat_length:
            chat_history[user_id]["messages"] = chat_history[user_id]["messages"][-max_chat_length:]

    chat_history[user_id]["messages"].append({"role": "user", "content": webhook.text})

    for entry in chat_history[user_id]["messages"]:
        role = entry['role']
        content = entry['content']
        messages.append({"role": role, "content": content})

    client = OpenAI(
        base_url='http://localhost:11434/v1/',

        # required but ignored
        api_key='ollama',
    )

    # https://github.com/ollama/ollama/blob/main/docs/openai.md#v1chatcompletions
    response = client.chat.completions.create(
        messages=messages,
        temperature=0.3,
        model='llama3:8b',
    )

    response_role = response.choices[0].message.role
    if response.choices[0].finish_reason == "stop":
        response_text = response.choices[0].message.content
        chat_history[user_id]["messages"].append({"role": response_role, "content": response_text})
    else:
        chat_history[user_id]["messages"].append({"role": response_role, "content": f"error: stop reason - {response.choices[0].finish_reason}"})

    return response_text

@app.route('/echo', methods=['POST'])
def echo():
    token = os.environ.get("SYNOLOGY_TOKEN")
    webhook = OutgoingWebhook(request.form, token, verbose=True)

    if not webhook.authenticate(token):
        return webhook.createResponse('Outgoing Webhook authentication failed: Token mismatch.')

    hostname = os.environ.get("SYNOLOGY_INCOMING_URL")
    bot = IncomingWebhook(hostname, port=5002, token=token, user_ids=[webhook.user_id])
    if app.debug:
        print("\n" + webhook.text + "\n")

    reply = process_gpt_response(webhook)

    if app.debug:
        print("\n" + reply + "\n")

    while (len(reply) > 2000):
        bot.send(reply[:2000])
        reply = reply[2000:]
    bot.send(reply)
    return "echo completed"

if __name__ == '__main__':
   app.run('0.0.0.0', port=5001, debug = True)

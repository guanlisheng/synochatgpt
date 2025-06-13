import shelve
import textwrap
import time
import os
import re
import requests

from openai import OpenAI
from flask import Flask, request
from synochat.webhooks import OutgoingWebhook
from synochat.webhooks import IncomingWebhook

app = Flask(__name__)

# In-memory chat history storage
chat_history = {}

# This system prompt sets up the character of the chatbot; change it if you want
chatbot_character = '''You are a helpful, friendly AI assistant working inside a simple text interface (like SMS or terminal).
The user interacts with you via Synology Chat, which only supports plain text, line breaks, and emojis.

❗ IMPORTANT OUTPUT RULES:
- Keep responses simple and structured.
- Use blank lines (`\n\n`) to separate sections.
- Use emoji (✅ ❌ ⚠️ 📌 🧠 💡) to improve readability.
- DO NOT use Markdown (e.g. `**bold**`, `# heading`, or code blocks).
- Avoid very long paragraphs – break them into shorter pieces.
- Do not use tables or rich formatting; describe them instead.

If the user asks for a list, use this format:
1️⃣ First item
2️⃣ Second item
3️⃣ Third item

If showing a block of commands, do it like this:

📦 Command Example:
curl http://localhost:11434

You speak in the language the user uses. Be clear, helpful, and friendly.'''

# Set maximum chat exchanges or idle time gap to start a new conversatoin
max_chat_length = 100 

def format_think_tags(text: str) -> str:
    def replace_think(match):
        thought = match.group(1).strip()
        return f"\n🧠 我的思考：\n{thought}\n——————————————\n"

    text = re.sub(r"<think>(.*?)</think>", replace_think, text, flags=re.DOTALL)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

def list_ollama_models():
    try:
        res = requests.get("http://localhost:11434/api/tags")
        res.raise_for_status()
        models = [m["name"] for m in res.json().get("models", [])]

        if not models:
            return "⚠️ 当前没有本地模型，请先使用 `ollama pull` 下载。"

        # 格式化输出，适配 Synology Chat
        lines = ["📚 当前可用模型：", "——————————————"]
        for i, m in enumerate(models, 1):
            lines.append(f"{i}️⃣ {m}")
        lines.append("——————————————")
        lines.append("使用命令：/model 模型名\n例如：`/model llama3`")
        return "\n".join(lines)

    except Exception as e:
        return f"⚠️ 获取模型列表失败: {str(e)}"

def process_gpt_response(webhook):
    system_prompt = chatbot_character
    user_id, username = webhook.user_id, webhook.username
    current_timestamp = int(time.time())

    # Open the shelve file to store chat history
    with shelve.open('chat_history', writeback=True) as chat_history:

        text = webhook.text.strip()
        if text.startswith("/model"):
            args = text.split()

            if len(args) == 1:
                current = chat_history.get(user_id, {}).get("model", "deepseek-r1")
                return f"🧠 当前模型是：`{current}`"
            
            elif args[1] == "list":
                models = list_ollama_models()
                return "📚 当前可用模型列表：\n- " + "\n- ".join(models)
            else:
                new_model = args[1]
                if user_id not in chat_history:
                    chat_history[user_id] = {"messages": [], "model": new_model}
                else:
                    chat_history[user_id]["model"] = new_model
                return f"✅ 模型已切换为：`{new_model}`"

        # Maintain chat history
        if user_id not in chat_history:
            chat_history[user_id] = {"username": username, "messages": [], "last_timestamp": current_timestamp}
        else:
            chat_history[user_id]["last_timestamp"] = current_timestamp
            # Truncate chat history if it exceeds the maximum length
            if len(chat_history[user_id]["messages"]) > max_chat_length:
                chat_history[user_id]["messages"] = chat_history[user_id]["messages"][-max_chat_length:]

        # Append the user's message
        chat_history[user_id]["messages"].append({"role": "user", "content": webhook.text})

        # Prepare the message list for the API call
        messages = [{"role": "system", "content": system_prompt}]
        for entry in chat_history[user_id]["messages"]:
            messages.append({"role": entry['role'], "content": entry['content']})

        client = OpenAI(
            base_url='http://localhost:11434/v1/',
            api_key='ollama',  # required but ignored
        )

        # Make the API call to the model
        model = chat_history[user_id].get("model", "deepseek-r1")
        response = client.chat.completions.create(
            messages=messages,
            model=model,
        )

        # Process the response and update chat history
        response_role = response.choices[0].message.role
        if response.choices[0].finish_reason == "stop":
            raw_response = response.choices[0].message.content
            response_text = format_think_tags(raw_response)
            chat_history[user_id]["messages"].append({"role": response_role, "content": response_text})
        else:
            response_text = f"error: stop reason - {response.choices[0].finish_reason}"
            chat_history[user_id]["messages"].append({"role": response_role, "content": response_text})

    return response_text

@app.route('/echo', methods=['POST'])
def echo():
    token = os.environ.get("SYNOLOGY_TOKEN")
    webhook = OutgoingWebhook(request.form, token, verbose=False)

    if not webhook.authenticate(token):
        return webhook.createResponse('Outgoing Webhook authentication failed: Token mismatch.')

    hostname = os.environ.get("SYNOLOGY_INCOMING_URL")
    bot = IncomingWebhook(hostname, port=5002, token=token, user_ids=[webhook.user_id])
    if app.debug:
        print("\n" + webhook.text + "\n")

    reply = process_gpt_response(webhook)

    if app.debug:
        print("\n" + reply + "\n")

    for chunk in textwrap.wrap(reply, width=1800):
        bot.send(chunk)

    return "echo completed"

if __name__ == '__main__':
   app.run('0.0.0.0', port=5001, debug = True)

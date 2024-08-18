
## Synochatgpt
Inspired by [synochat](https://github.com/bitcanon/synochat), [chatgpt](https://chat.openai.com) and [ollama](https://ollama.com/).

The goal is to run LLM `100%` locally and integrate as a [chatbot](https://kb.synology.com/en-id/DSM/help/Chat/chat_integration?version=7#b_67) with [Synology Chat](https://www.synology.com/en-global/dsm/feature/chat)

## Usage

Install `ollama` and download `llama3:8b` on your mac
```
ollama pull llama3:8b
ollama server
```

It also needs your Synology Chat Bot's token and incoming URL (host), set them as environment variables before using the app:
```bash
export export SYNOLOGY_TOKEN='...'
export export SYNOLOGY_INCOMING_URL='...'
```

Disable PROXY for localhost HTTP access if needed
```bash
export NO_PROXY=http://127.0.0.1
```

## Run
```bash
pip install -r requirements.txt

python synochatgpt.py
```

## TODO
* [ ] Fine tune
* [ ] Docker
* [ ] RAG

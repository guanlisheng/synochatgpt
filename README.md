
## Synochatgpt
Inspired by [synochat](https://github.com/bitcanon/synochat) and [chatgpt](https://chat.openai.com)

## Usage

The library needs to be configured with your account's secret key which is available on the [website](https://platform.openai.com/account/api-keys). set it as the `OPENAI_API_KEY` environment variable before using the library:

```bash
export OPENAI_API_KEY='sk-...'
```

it also needs your Synology Chat Bots' Token and Incoming Url, set them as environment variables before using the app:
```bash
export export SYNOLOGY_TOKEN='uz...'
export export SYNOLOGY_INCOMING_URL='uz...'
```

Disable PROXY for localhost HTTP access if needed
```bash
export NO_PROXY=http://127.0.0.1,others
```

## Run
```bash
pip install -r requirements.txt

python synogpt.py
```

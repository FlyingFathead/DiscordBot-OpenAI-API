# DiscordBot-OpenAI-API
A simple Python-based Discord bot for the OpenAI API

**NOTE: This bot is heavily WIP and is currently only intended for special use case purposes. Many of the features have not been implemented yet.** For a more sophisticated project, see i.e. my [Telegram bot](https://github.com/FlyingFathead/TelegramBot-OpenAI-API/).

Although merely a crude initial sketch, this bot basis uses (as of January 2024) the up-to-date version of OpenAI's Python library (`v1.6.1`) as well as `discord.py` (`v2.3.2`).

# Installing
1. Clone the repo: `git clone https://github.com/FlyingFathead/DiscordBot-OpenAI-API/` => `cd DiscordBot-OpenAI-API/`
2. Install the prerequisites: `pip install -r requirements.txt`
    or:
```
discord.py==2.3.2
configparser>=6.0.0
httpx>=0.26.0
openai>=1.6.1
transformers>=4.36.2
requests>=2.31.0
```
3. Get your Discord bot token: 1) Go the Discord Developer Portal => select your bot 2) Click on "Reset Token" to generate a new one, use that.
4. Set your Discord bot token: either set it to the environment variable `DISCORD_BOT_TOKEN` or place it in the program directory as `discord_bot_token.txt`.
5. When setting up the bot, remember to activate this option with your bot in order for it to be able to receive messages (in the Discord `Bot` settings tab in the Developer Portal):
    ```
    Message Content Intent
    Required for your bot to receive message content in most messages.
    NOTE: Once your bot reaches 100 or more servers, this will require verification and approval. Read more here
    ```
6. Get your OpenAI API token and set it to either `OPENAI_API_KEY` environment variable or into `api_key.txt` in the program directory.
7. Adjust your settings in the `config.ini`
8. Launch the bot with: `python main.py`

# Changelog
- v0.14 - Various small fixes, not implemented in this version yet.
- v0.08 - `Timezone` added to options.
- v0.07 - Chat history trimming adjusted, hello message on join; still WIP!
- v0.05 - Well, it works. Initial early release. Expect nothing much.

# Contribute
- All contributions appreciated! Feel free to also post any bugs and other issues on the repo's "Issues" page. However, please do note the heavy WIP status of this project. No warranties!

# About
- Written by [FlyingFathead](https://github.com/FlyingFathead/)
- Digital ghost code by ChaosWhisperer

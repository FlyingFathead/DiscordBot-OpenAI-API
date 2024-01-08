# text_message_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# text message handler for openai-api discord bot
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import discord
import asyncio
import logging
import datetime
import json
import httpx
import openai
import utils

# discord modules
from discord.ext import commands

# Discord text message handling logic
async def handle_message(bot, message):
    # Send a "holiday message" if the bot is on a break
    if bot.is_bot_disabled:
        await message.channel.send(bot.bot_disabled_msg)
        return

    # Check the global rate limit
    if bot.check_global_rate_limit():
        await message.channel.send("The bot is currently busy. Please try again in a minute.")
        return

        # only for voice msg tnrascriptions, not in use atm
        """ # Check if there is a transcribed text available
        if 'transcribed_text' in context.user_data:
            user_message = context.user_data['transcribed_text']
            # Clear the transcribed text after using it
            del context.user_data['transcribed_text']
        else:
            user_message = update.message.text """

    # process a text message
    try:
        user_message = message.content
        user_token_count = bot.count_tokens(user_message)

        # Managing chat history per channel
        channel_id = message.channel.id
        if channel_id not in bot.chat_history:
            bot.chat_history[channel_id] = []

        chat_history = bot.chat_history[channel_id]

        # Log token counts for debugging
        bot.logger.info(f"[Token counting/debug] user_token_count type: {type(user_token_count)}, value: {user_token_count}")
        bot.logger.info(f"[Token counting/debug] bot.total_token_usage type: {type(bot.total_token_usage)}, value: {bot.total_token_usage}")

        # Check token usage limit
        try:
            max_tokens_config = bot.config.getint('GlobalMaxTokenUsagePerDay', 100000)
            is_no_limit = max_tokens_config == 0
        except ValueError:
            bot.logger.error("Invalid value for GlobalMaxTokenUsagePerDay in the configuration file.")
            await message.channel.send("An error occurred while processing your request.")
            return

        if not is_no_limit and (bot.total_token_usage + user_token_count) > max_tokens_config:
            await message.channel.send("The bot has reached its daily token limit. Please try again tomorrow.")
            return

        # Preparing the chat history and message for the API request
        utc_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        user_message_with_timestamp = f"[{utc_timestamp}] {user_message}"

        bot.total_token_usage += user_token_count
        bot.logger.info(f"Received message from {message.author.name}: {user_message}")

        # Prepare the conversation history for OpenAI API
        system_message = {"role": "system", "content": f"System time+date: {utc_timestamp}, {day_of_week}): {bot.system_instructions}"}

        # Append the new user message to the chat history
        chat_history.append({"role": "user", "content": user_message_with_timestamp})
        chat_history_with_system_message = [system_message] + chat_history

        # Your existing API request logic...

        # Append the bot's response to the chat history
        chat_history.append({"role": "assistant", "content": bot_reply})

        # Trim chat history if it exceeds a specified length or token limit
        bot.trim_chat_history(chat_history, bot.max_tokens)
        bot.chat_history[channel_id] = chat_history

        for attempt in range(bot.max_retries):
            try:
                payload = {
                    "model": bot.model,
                    "messages": chat_history_with_system_message,
                    "temperature": bot.temperature
                }

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai.api_key}"
                }
                async with httpx.AsyncClient() as client:
                    response = await client.post("https://api.openai.com/v1/chat/completions",
                                                 data=json.dumps(payload),
                                                 headers=headers,
                                                 timeout=bot.timeout)
                    response_json = response.json()

                bot_reply = response_json['choices'][0]['message']['content'].strip()
                bot_token_count = bot.count_tokens(bot_reply)
                bot.total_token_usage += bot_token_count

                bot.write_total_token_usage(bot.total_token_usage)

                bot.logger.info(f"Bot's response: {bot_reply}")

                await message.channel.send(bot_reply)
                break

            except httpx.ReadTimeout:
                if attempt < bot.max_retries - 1:
                    await asyncio.sleep(bot.retry_delay)
                else:
                    bot.logger.error("Max retries reached. Giving up.")
                    await message.channel.send("Sorry, I'm having trouble connecting. Please try again later.")
                    break

            except Exception as e:
                bot.logger.error(f"Error during message processing: {e}")
                await message.channel.send("Sorry, there was an error processing your message.")
                return

    except Exception as e:
        bot.logger.error("Unhandled exception:", exc_info=e)
        logging.info(f"Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        await message.channel.send("An unexpected error occurred. Please try again.")

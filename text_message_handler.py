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
        if 'transcribed_text' in chat_history.user_data:
            user_message = chat_history.user_data['transcribed_text']
            # Clear the transcribed text after using it
            del chat_history.user_data['transcribed_text']
        else:
            user_message = update.message.text """

    # process a text message
    try:
        user_message = message.content
        user_token_count = bot.count_tokens(user_message)

        # Managing chat history per channel
        channel_id = message.channel.id

        # clear the chat history in a suitable syntax for Discord
        if channel_id not in bot.chat_history:
            bot.chat_history[channel_id] = {
                'last_message_time': datetime.datetime.utcnow(),
                'messages': []
            }

        """ if channel_id not in bot.chat_history:
            bot.chat_history[channel_id] = []

        chat_history = bot.chat_history[channel_id] """

        chat_history = bot.chat_history[channel_id]['messages']
        last_message_time = bot.chat_history[channel_id]['last_message_time']

        # Log token counts for debugging
        bot.logger.info(f"[Token counting/debug] user_token_count type: {type(user_token_count)}, value: {user_token_count}")
        bot.logger.info(f"[Token counting/debug] bot.total_token_usage type: {type(bot.total_token_usage)}, value: {bot.total_token_usage}")

        # Convert max_tokens_config to an integer =>
        # Attempt to read max_tokens_config as an integer =>
        # Check token usage limit
        try:
            max_tokens_config = bot.config.getint('GlobalMaxTokenUsagePerDay', 100000)
            is_no_limit = max_tokens_config == 0
            bot.logger.info(f"[Token counting/debug] max_tokens_config type: {type(max_tokens_config)}, value: {max_tokens_config}")
            # Debug: Print the value read from token_usage.json
            bot.logger.info(f"[Debug] Total token usage from file: {bot.total_token_usage}")

        except ValueError:
            bot.logger.error("Invalid value for GlobalMaxTokenUsagePerDay in the configuration file.")
            await message.channel.send("An error occurred while processing your request.")
            return

        # Safely compare user_token_count and max_tokens_config
        if not is_no_limit and (bot.total_token_usage + user_token_count) > max_tokens_config:
            await message.channel.send("The bot has reached its daily token limit. Please try again tomorrow.")
            return

        # Debug: Print before token limit checks
        bot.logger.info(f"[Debug] is_no_limit: {is_no_limit}, user_token_count: {user_token_count}, max_tokens_config: {max_tokens_config}")

        # Preparing the chat history and message for the API request
        # utc_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        # user_message_with_timestamp = f"[{utc_timestamp}] {user_message}"

        # get date & time for timestamps
        now_utc = datetime.datetime.utcnow()
        current_time = now_utc
        utc_timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        day_of_week = now_utc.strftime("%A")
        user_message_with_timestamp = f"[{utc_timestamp}] {user_message}"

        # Add the user's tokens to the total usage
        bot.total_token_usage += user_token_count
        bot.logger.info(f"Received message from {message.author.name}: {user_message}")

        # Check if session timeout is enabled and if session is timed out
        if bot.session_timeout_minutes > 0:
            timeout_seconds = bot.session_timeout_minutes * 60  # Convert minutes to seconds
            if 'last_message_time' in chat_history.chat_data:
                last_message_time = chat_history.chat_data['last_message_time']
                elapsed_time = (current_time - last_message_time).total_seconds()

                if elapsed_time > timeout_seconds:
                    # Log the length of chat history before trimming
                    chat_history_length_before = len(chat_history.chat_data.get('chat_history', []))
                    bot.logger.info(f"Chat history length before trimming: {chat_history_length_before}")

                    # Session timeout logic
                    if bot.max_retained_messages == 0:
                        # Clear entire history
                        chat_history.clear()
                        bot.logger.info(f"'MaxRetainedMessages' set to 0, cleared the entire chat history due to session timeout.")
                    else:
                        # Keep the last N messages
                        chat_history = chat_history[-bot.max_retained_messages:]                        
                        bot.logger.info(f"Retained the last {bot.max_retained_messages} messages due to session timeout.")

                    # Update the last message time
                    bot.chat_history[channel_id]['last_message_time'] = datetime.datetime.utcnow()
                    bot.logger.info(f"Session timeout. Chat history updated.")

                    # Log the length of chat history after trimming
                    chat_history_length_after = len(chat_history.chat_data.get('chat_history', []))
                    bot.logger.info(f"Chat history length after trimming: {chat_history_length_after}")

                    bot.logger.info(f"[DebugInfo] Session timed out. Chat history updated.")
        else:
            # Log the skipping of session timeout check
            bot.logger.info(f"[DebugInfo] Session timeout check skipped as 'SessionTimeoutMinutes' is set to 0.")            

        # Update chat history and last message time after processing the current message
        bot.chat_history[channel_id]['messages'] = chat_history
        bot.chat_history[channel_id]['last_message_time'] = datetime.datetime.utcnow()

        # Update the time of the last message
        if 'last_message_time' in chat_history:
            chat_history['last_message_time'] = current_time

        # Log the current chat history
        # bot.logger.debug(f"Current chat history: {context.chat_data.get('chat_history')}")

        # Initialize chat_history as an empty list if it doesn't exist
        # chat_history = context.chat_data.get('chat_history', [])

        # Append the new user message to the chat history
        # chat_history.append({"role": "user", "content": user_message_with_timestamp})

        # Append the new user message to the chat history
        chat_history.append({"role": "user", "content": user_message_with_timestamp})

        # Prepare the conversation history to send to the OpenAI API
        system_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        system_message = {"role": "system", "content": f"System time+date: {system_timestamp}, {day_of_week}): {bot.system_instructions}"}

        chat_history_with_system_message = [system_message] + chat_history

        # Trim chat history if it exceeds a specified length or token limit
        bot.trim_chat_history(chat_history, bot.max_tokens)

        # Log the incoming user message
        bot.log_message('User', message.author.id, message.content)

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

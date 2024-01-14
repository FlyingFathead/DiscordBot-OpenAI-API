# text_message_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# text message handler for openai-api discord bot
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import random
import discord
import asyncio
import logging
import datetime
import json
import httpx
import openai
import utils

# discord modules
# discord bot modules
import discord
from discord.ext import commands

from custom_functions import custom_functions

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

# Maximum number of message turns to retain in the chat history
MAX_TURNS = 30

# Desired channel name
DESIRED_CHANNEL_NAME = "chatkeke"

# Function to append a message to chat_history, ensuring only MAX_TURNS are kept
def append_to_chat_history(chat_history, role, content):
    if content:
        chat_history.append({"role": role, "content": content})
    # Keep only the latest MAX_TURNS messages in chat history
    return chat_history[-MAX_TURNS:]

# Discord text message handling logic
async def handle_message(bot, message, channel_id):
    # Check if the message is in the desired channel
    if message.channel.name != DESIRED_CHANNEL_NAME:
        # If not, do not process the message
        return

    # Check and log the type of the message object
    bot.logger.info(f"Type of message object: {type(message)}")

    # Type check for message object
    if not isinstance(message, discord.Message):
        bot.logger.error(f"Invalid message object type: {type(message)}")
        return

    # Initialize bot_reply before the for-loop
    bot_reply = None

    # Send a "holiday message" if the bot is on a break
    if bot.is_bot_disabled:
        await message.channel.send(bot.bot_disabled_msg)
        return

    # Check the global rate limit
    if bot.check_global_rate_limit():
        await message.channel.send("The bot is currently busy. Please try again in a minute.")
        return

    # Process a text message
    try:
        user_message = message.content
        channel_id = message.channel.id
        user_id = message.author.id  # Get the user's ID        
        username = message.author.name  # Get the username of the message author
        display_name = message.author.display_name  # Get the display name of the message author

        # Log the received user message
        bot.logger.info(f"Received message from {message.author.name} in channel {channel_id}: {user_message}")

        # Initialize or update chat history for the channel
        if channel_id not in bot.chat_history:
            bot.chat_history[channel_id] = {
                'last_message_time': datetime.datetime.utcnow(),
                'messages': []
            }

        chat_history = bot.chat_history[channel_id]['messages']

        # Prepare the system message
        system_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        day_of_week = datetime.datetime.utcnow().strftime("%A")
        system_message = {
            "role": "system",
            "content": f"System time+date: {system_timestamp}, {day_of_week}): {bot.system_instructions}"
        }

        # append_to_chat_history(chat_history, system_message["role"], system_message["content"])
        # Updating chat history with the system message
        chat_history = append_to_chat_history(chat_history, system_message["role"], system_message["content"])

        # ~~~~~~~~~~~~~~~~~~~~~~~~~
        # The incoming user message
        # ~~~~~~~~~~~~~~~~~~~~~~~~~
        # Append the user message with the username to the chat history
        
        # (without timestamps)
        # user_message_with_username = f"{display_name} <@{user_id}> says: {user_message}"

        # Format the current time with the configured timezone
        timestamp = bot.format_datetime(datetime.datetime.now())

        # Append the user message with the username and timestamp to the chat history
        user_message_with_username= f"[{timestamp}] {display_name} <@{user_id}> says: {user_message}"
        
        # user_message_with_username = f"Käyttäjä {display_name} sanoo: {user_message}"
        logging.info(f"[INFO] {display_name} <@{user_id}> says: {user_message}")
        # append_to_chat_history(chat_history, "user", user_message_with_username)
        # Updating chat history with the user message
        chat_history = append_to_chat_history(chat_history, "user", user_message_with_username)

        # Attempt to send a reply
        for attempt in range(bot.max_retries):
            try:
                # Prepare the payload for the API request
                payload = {
                    "model": bot.model,
                    "messages": chat_history,  # Updated to include the latest user message
                    "temperature": bot.temperature,
                    "functions": custom_functions,
                    "function_call": 'auto'  # Allows the model to dynamically choose the function                   
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

                # Process the response and extract the bot's reply
                if response.status_code == 200:
                    bot_reply = response_json['choices'][0]['message']['content'].strip()

                    # Format the bot's reply with user mention
                    # bot_reply_formatted = f"<@{user_id}> {bot_reply}"    

                    bot_reply_formatted = f"{bot_reply}"    

                    # Decide randomly whether to mention the user
                    if random.random() < bot.mention_user_odds:
                        bot_reply_formatted = f"<@{user_id}> {bot_reply}"
                    else:
                        bot_reply_formatted = bot_reply

                    # Updating chat history with the bot's reply
                    chat_history = append_to_chat_history(chat_history, "assistant", bot_reply_formatted)

                    # Log the bot's response
                    # bot.logger.info(f"Bot's reply in channel {channel_id}: {bot_reply}")
                    # await message.channel.send(bot_reply)
                    
                    # Log the bot's response
                    bot.logger.info(f"Bot's reply in channel {channel_id}: {bot_reply_formatted}")

                    await message.channel.send(bot_reply_formatted)                    
                    break
                else:
                    bot.logger.error("Received error response from API")
                    await message.channel.send("An error occurred while processing your request. Please try again later.")
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
                break

        # Update the chat history in the main bot data
        bot.chat_history[channel_id]['last_message_time'] = datetime.datetime.utcnow()
        bot.chat_history[channel_id]['messages'] = chat_history

    except Exception as e:
        bot.logger.error("Unhandled exception:", exc_info=True)
        await message.channel.send("An unexpected error occurred. Please try again.")

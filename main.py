# main.py

# main modules
import datetime
import configparser
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from functools import partial
import discord
import asyncio
import openai
import json
import httpx
import asyncio
import re

# discord-bot modules
import utils

# discord bot modules
from text_message_handler import handle_message

# read the API tokens
from bot_token import get_discord_bot_token
from api_key import get_api_key

# Discord bot class
class DiscordBot:
    def __init__(self):
        # Load configuration, initialize logging, etc.
        self.load_config()
        self.initialize_logging()
        
        # Initialize the chat history dictionary
        self.chat_history = {}        

        # Create Discord client
        self.client = discord.Client(intents=discord.Intents.default())

        # Setup event handlers
        self.setup_handlers()

    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.config = config['DEFAULT']
        self.model = self.config.get('Model', 'gpt-3.5-turbo')
        self.temperature = self.config.getfloat('Temperature', 0.7)
        self.timeout = self.config.getfloat('Timeout', 30.0)        
        self.max_tokens = self.config.getint('MaxTokens', 4096)
        self.max_retries = self.config.getint('MaxRetries', 3)
        self.retry_delay = self.config.getint('RetryDelay', 25)
        self.system_instructions = self.config.get('SystemInstructions', 'You are an OpenAI API-based chatbot on Telegram.')
        self.start_command_response = self.config.get('StartCommandResponse', 'Hello! I am a chatbot powered by GPT-3.5. Start chatting with me!')
        # Read and parse the BotAdminIDs
        admin_ids_str = self.config.get('BotAdminIDs', '')
        self.bot_admin_ids = [int(admin_id) for admin_id in admin_ids_str.split(',') if admin_id.isdigit()]        
        self.bot_owner_id = self.config.get('BotOwnerID', '0')
        self.is_bot_disabled = self.config.getboolean('IsBotDisabled', False)
        self.bot_disabled_msg = self.config.get('BotDisabledMsg', 'The bot is currently disabled.')
        self.enable_whisper = self.config.getboolean('EnableWhisper', True)
        self.max_voice_message_length = self.config.getint('MaxDurationMinutes', 5)
        self.data_directory = self.config.get('DataDirectory', 'data')  # Default to 'data' if not set
        self.max_storage_mb = self.config.getint('MaxStorageMB', 100) # Default to 100 MB if not set
        self.logfile_enabled = self.config.getboolean('LogFileEnabled', True)
        self.logfile_file = self.config.get('LogFile', 'bot.log')
        self.chat_logging_enabled = self.config.getboolean('ChatLoggingEnabled', False)
        self.chat_log_max_size = self.config.getint('ChatLogMaxSizeMB', 10) * 1024 * 1024  # Convert MB to bytes
        self.chat_log_file = self.config.get('ChatLogFile', 'chat.log')
        # Session management settings
        self.session_timeout_minutes = self.config.getint('SessionTimeoutMinutes', 60)  # Default to 1 minute if not set
        self.max_retained_messages = self.config.getint('MaxRetainedMessages', 2)     # Default to 0 (clear all) if not set
        # User commands
        self.reset_command_enabled = self.config.getboolean('ResetCommandEnabled', False)
        self.admin_only_reset = self.config.getboolean('AdminOnlyReset', True)

    def initialize_logging(self):
        self.logger = logging.getLogger('TelegramBotLogger')
        self.logger.setLevel(logging.INFO)
        if self.logfile_enabled:
            file_handler = RotatingFileHandler(self.logfile_file, maxBytes=1048576, backupCount=5)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(stream_handler)

    def initialize_chat_logging(self):
        if self.chat_logging_enabled:
            self.chat_logger = logging.getLogger('ChatLogger')
            chat_handler = RotatingFileHandler(self.chat_log_file, maxBytes=self.chat_log_max_size, backupCount=5)
            chat_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
            self.chat_logger.addHandler(chat_handler)
            self.chat_logger.setLevel(logging.INFO)

    def setup_handlers(self):
        @self.client.event
        async def on_ready():
            # Logic when bot is ready
            logging.info(f'Logged in as {self.client.user}')

        @self.client.event
        async def on_message(message):
            # Avoid responding to self
            if message.author == self.client.user:
                return
            
            # Handle messages
            # Handle the message using your text message handler
            await handle_message(self, message)

    # run
    def run(self):
        # Run the Discord bot
        discord_bot_token = get_discord_bot_token()  # Retrieve the Discord bot token
        self.client.run(discord_bot_token)

if __name__ == '__main__':
    bot = DiscordBot()
    bot.run()
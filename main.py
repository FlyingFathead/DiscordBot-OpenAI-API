# main.py
# Discord Bot for OpenAI API // FlyingFathead (w/ ghostcode: ChaosWhisperer)
# Jan 2024
version_number = "0.08"

# main modules
import datetime
import pytz
import configparser
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from functools import partial

import requests
import asyncio
import openai
import json
import httpx
import asyncio
import re
# for token counting
from transformers import GPT2Tokenizer

# discord bot modules
import discord
from discord.ext import commands

# discord-bot modules
import utils
from text_message_handler import handle_message
from modules import count_tokens, read_total_token_usage, write_total_token_usage
from modules import markdown_to_html, check_global_rate_limit
from modules import log_message, rotate_log_file

# read the API tokens
from bot_token import get_discord_bot_token
from api_key import get_api_key

# Call the startup message function
utils.print_startup_message(version_number)

# Enable logging
logging.basicConfig(format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the tokenizer globally
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

intents = discord.Intents.default()
intents.messages = True  # Ensure this is enabled
intents.message_content = True  # Enable message content intent

# Discord bot class
class DiscordBot:

    # version of this program
    version_number = version_number

    def __init__(self):

        # Attempt to get bot & API tokens
        try:
            self.bot_token = get_discord_bot_token()
            openai.api_key = get_api_key()
        except FileNotFoundError as e:
            self.logger.error(f"Required configuration not found: {e}")
            sys.exit(1)

        # Load configuration, initialize logging, etc.
        self.load_config()
        self.initialize_logging()

        # Initialize chat logging if enabled
        self.initialize_chat_logging()

        self.token_usage_file = 'token_usage.json'
        self.total_token_usage = self.read_total_token_usage()
        self.max_tokens_config = self.config.getint('GlobalMaxTokenUsagePerDay', 100000)

        self.global_request_count = 0
        self.rate_limit_reset_time = datetime.datetime.now()
        self.max_global_requests_per_minute = self.config.getint('MaxGlobalRequestsPerMinute', 60)

        # Initialize the chat history dictionary
        self.chat_history = {}        

        # Create Discord client
        # self.client = discord.Client(intents=discord.Intents.default())

        # Initialize only one client with the bot commands and intents
        self.client = commands.Bot(command_prefix='!', intents=intents)

        # Setup event handlers
        self.setup_handlers()

    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.config = config['DEFAULT']
        self.model = self.config.get('Model', 'gpt-3.5-turbo')
        self.temperature = self.config.getfloat('Temperature', 0.7)

        self.timezone = pytz.timezone(self.config.get('Timezone', 'UTC'))
        self.mention_user_odds = self.config.getfloat('MentionUserOdds', 0.3)  # Default to 0.3

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

        self.desired_channel_name = self.config.get('DesiredChannelName', 'chatkeke')
        self.hello_message = self.config.get('HelloMessage', 'Hello! I am online and ready to assist!')

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
        self.logger = logging.getLogger('DiscordBotLogger')
        self.logger.setLevel(logging.INFO)
        if self.logfile_enabled:
            file_handler = RotatingFileHandler(self.logfile_file, maxBytes=1048576, backupCount=5)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(stream_handler)

    # Check and update the global rate limit.
    def check_global_rate_limit(self):
        result, self.global_request_count, self.rate_limit_reset_time = check_global_rate_limit(
            self.max_global_requests_per_minute, 
            self.global_request_count, 
            self.rate_limit_reset_time
        )
        return result

    # count token usage
    def count_tokens(self, text):
        return count_tokens(text, tokenizer)
    
    # read and write token usage
    # detect date changes and reset token counter accordingly
    def read_total_token_usage(self):
        return read_total_token_usage(self.token_usage_file)

    # write latest token count data
    def write_total_token_usage(self, usage):
        write_total_token_usage(self.token_usage_file, usage)

    # logging functionality
    def log_message(self, message_type, user_id, message):
        log_message(self.chat_log_file, self.chat_log_max_size, message_type, user_id, message, self.chat_logging_enabled)

    # trim the chat history to meet up with max token limits
    def trim_chat_history(self, chat_history, max_total_tokens):
        total_tokens = sum(self.count_tokens(message['content']) for message in chat_history)

        # Continue removing messages until the total token count is within the limit
        while total_tokens > max_total_tokens and len(chat_history) > 1:
            # Remove the oldest message
            removed_message = chat_history.pop(0)

            # Recalculate the total token count after removal
            total_tokens = sum(self.count_tokens(message['content']) for message in chat_history)

    # max token estimates
    def estimate_max_tokens(self, input_text, max_allowed_tokens):
        # Rough estimation of the input tokens
        input_tokens = len(input_text.split())
        max_tokens = max_allowed_tokens - input_tokens
        # Ensure max_tokens is positive and within a reasonable range
        return max(1, min(max_tokens, max_allowed_tokens))

    # Define a function to update chat history in a file
    def update_chat_history(self, chat_history):
        with open('chat_history.txt', 'a') as file:
            for message in chat_history:
                file.write(message + '\n')

    # Define a function to retrieve chat history from a file
    def retrieve_chat_history(self):
        chat_history = []
        try:
            with open('chat_history.txt', 'r') as file:
                chat_history = [line.strip() for line in file.readlines()]
        except FileNotFoundError:
            pass
        return chat_history

    # split long messages
    def split_large_messages(self, message, max_length=4096):
        return [message[i:i+max_length] for i in range(0, len(message), max_length)]

    # method to convert and format datetime
    def format_datetime(self, dt):
        # Convert to the configured timezone
        tz_aware_dt = dt.astimezone(self.timezone)
        return tz_aware_dt.strftime('%Y-%m-%d %H:%M:%S %Z')

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
            # Iterate through all the guilds (servers) the bot is in
            for guild in self.client.guilds:
                # Iterate through all the channels in the guild
                for channel in guild.channels:
                    # Check if the channel name matches the desired one
                    if channel.name == self.desired_channel_name:
                        # Send the hello message to this channel
                        await channel.send(self.hello_message)
                        return  # Exit the function once the message is sent

        @self.client.event
        async def on_message(message):
            # Avoid responding to self
            if message.author == self.client.user:
                return
            
            # Extract channel_id from the message
            channel_id = message.channel.id

            # Handle messages
            # Handle the message using your text message handler
            await handle_message(self, message, channel_id)

        """ @self.client.event
        async def on_message(message):
            print(f"Author: {message.author} - Content: '{message.content}'")
            # Prevent further processing if the message is from the bot itself
            if message.author == self.client.user:
                return """

        """ # debug tryout
        @self.client.event
        async def on_message(message):
            if message.author != self.client.user:
                print(message.content)  # Just print the content for testing """
        
    # run
    def run(self):
        # Run the Discord bot
        discord_bot_token = get_discord_bot_token()  # Retrieve the Discord bot token
        logging.info(f"Token being used: {discord_bot_token}")    
        print(f"Token being used: {discord_bot_token}")        
        self.client.run(discord_bot_token)

if __name__ == '__main__':
    bot = DiscordBot()
    bot.run()
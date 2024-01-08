# utils.py
import os
import re
import shutil
import sys
import datetime
from functools import partial
import asyncio
from concurrent.futures import ThreadPoolExecutor
# from pydub import AudioSegment

# set `now`
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# print term width horizontal line
def hz_line(character='-'):
    terminal_width = shutil.get_terminal_size().columns
    line = character * terminal_width
    print(line)
    sys.stdout.flush()  # Flush the output to the terminal immediately

# print the startup message
def print_startup_message(version_number):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    hz_line()
    print(f"[{now}] Telegram bot v.{version_number} for OpenAI API starting up...", flush=True)
    hz_line()

# remove html tags
def remove_html_tags(text):
    """Remove html tags from a string"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

# escape markdown v2, v0.12 [currently not in use because this is a ... it's a thing]
def escape_markdown_v2(text):

    # Escape MarkdownV2 special characters
    def escape_special_chars(m):
        char = m.group(0)
        # Escape all special characters with a backslash, except for asterisks and underscores
        if char in ('_', '*', '`'):
            # These are used for formatting and shouldn't be escaped.
            return char
        return '\\' + char

    # First, we'll handle the code blocks by temporarily removing them
    code_blocks = re.findall(r'```.*?```', text, re.DOTALL)
    code_placeholders = [f"CODEBLOCK{i}" for i in range(len(code_blocks))]
    for placeholder, block in zip(code_placeholders, code_blocks):
        text = text.replace(block, placeholder)

    # Now we escape the special characters outside of the code blocks
    text = re.sub(r'([[\]()~>#+\-=|{}.!])', escape_special_chars, text)

    # We convert **bold** and *italic* (or _italic_) syntax to Telegram's MarkdownV2 syntax
    # Bold: **text** to *text*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # Italic: *text* or _text_ to _text_ (if not part of a code block)
    text = re.sub(r'\b_(.+?)_\b', r'_\1_', text)
    text = re.sub(r'\*(.+?)\*', r'_\1_', text)

    # Restore the code blocks
    for placeholder, block in zip(code_placeholders, code_blocks):
        text = text.replace(placeholder, block)

    return text

# Calculate the total size of files in the specified directory.
def get_directory_size(path: str) -> int:    
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

# Cleanup the oldest files in the specified directory when storage limit is exceeded.
def cleanup_data_directory(path: str, max_storage_mb: int):    
    files = [os.path.join(path, f) for f in os.listdir(path)]
    files.sort(key=lambda x: os.path.getmtime(x))

    while get_directory_size(path) >= max_storage_mb * 1024 * 1024 and files:
        os.remove(files.pop(0)) # Remove the oldest file

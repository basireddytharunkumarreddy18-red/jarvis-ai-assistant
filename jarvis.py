import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse

import httpx
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from dotenv import load_dotenv
from openai import OpenAI
from pynput import keyboard

load_dotenv()

if not os.getenv('DEEPSEEK_API_KEY'):
    sys.exit('Missing DEEPSEEK_API_KEY. Put it in the .env file.')

# ---- Settings ---------------------------------------------------------------
MODEL = 'deepseek-flash'
VOICE = 'Samantha'         # Your preferred voice!
GREETING = "What's up, boss?"
TAPS_NEEDED = 3            
TAP_WINDOW_SECONDS = 1.0   
SPEECH_LEVEL = 500         
# -----------------------------------------------------------------------------

SAMPLE_RATE = 16000
SYSTEM_PROMPT = (
    'You are JARVIS, a sharp, witty personal assistant for a Mac. Your replies are spoken aloud, '
    'so answer in one to three short plain sentences, no markdown, no lists, no emojis. '
    'When the user asks you to do something on the Mac (open or close an app, open a website, '
    'search the web, change the volume, control music, open a folder), call the matching tool. '
    'To play a song or video by name, call play_youtube. Use music_control only for pause, next or previous '
    'in the Music or Spotify app. After a tool runs, tell the user exactly what the tool result says, '
    'in a few words, and never claim something is playing unless the result says so. Call the user boss.'
)

client = OpenAI(api_key=os.getenv('DEEPSEEK_API_KEY'), base_url='https://api.deepseek.com')
recognizer = sr.Recognizer()
history = []

FOLDERS = {'downloads': '~/Downloads', 'documents': '~/Documents', 'desktop': '~/Desktop'}
BROWSER = 'Brave Browser' # We explicitly set your browser here

# ---------------------------- Mac tools ------------------------------------

def run_osascript(script):
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0, (result.stderr or result.stdout).strip()

def clean_name(name):
    return name.replace('"', '').replace('\\', '').strip()

def open_app(name):
    result = subprocess.run(['open', '-a', clean_name(name)], capture_output=True, text=True)
    return f'Opened {name}.' if result.returncode == 0 else f'Could not find {name}.'

def quit_app(name):
    ok, message = run_osascript(f'tell application "{clean_name(name)}" to quit')
    return f'Closed {name}.' if ok else f'Could not close {name}: {message}'

def open_website(url):
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    subprocess.run(['open', '-a', BROWSER, url]) # Forces Brave
    return f'Opened {url} in Brave.'

def search_web(query):
    url = 'https://www.google.com/search?q=' + urllib.parse.quote_plus(query)
    subprocess.run(['open', '-a', BROWSER, url]) # Forces Brave
    return f'Searching the web for {query}.'

def play_youtube(query):
    match = None
    try:
        response = httpx.get(
            'https://www.youtube.com/results',
            params={'search_query': query},
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'},
            timeout=10,
            follow_redirects=True,
        )
        match = (re.search(r'"videoRenderer":\{"videoId":"([\w-]{11})"', response.text)
                 or re.search(r'"videoId":"([\w-]{11})"', response.text))
    except Exception:
        match = None
    if match:
        subprocess.run(['open', '-a', BROWSER, f'https://www.youtube.com/watch?v={match.group(1)}']) # Forces Brave
        return f'Opened the top YouTube video for {query} in Brave. It should start playing.'
    subprocess.run(['open', '-a', BROWSER, 'https://www.youtube.com/results?search_query=' + urllib.parse.quote_plus(query)])
    return f'I could not pick a video automatically, so I opened the YouTube results for {query}.'

def set_volume(level):
    level = max(0, min(100, int(level)))
    run_osascript(f'set volume output volume {level}')
    return f'Volume set to {level} percent.'

def music_control(action, app='Music'):
    commands = {'play_pause': 'playpause', 'next': 'next track', 'previous': 'previous track'}
    if action not in commands:
        return 'Unknown music action.'
    ok, message = run_osascript(f'tell application "{app}" to {commands[action]}')
    if not ok:
        return f'Music control failed: {message}'
    time.sleep(1) 
    ok, state = run_osascript(f'tell application "{app}" to player state as string')
    state = state.lower() if ok else 'unknown'
    if state == 'playing':
        return f'{app} is now playing.'
    if state == 'paused':
        return f'{app} is paused.'
    return f'{app} has nothing queued, so nothing is playing. Offer to play the song on YouTube instead.'

def open_folder(name):
    key = name.strip().lower()
    if key not in FOLDERS:
        return 'I can only open Downloads, Documents or Desktop.'
    subprocess.run(['open', os.path.expanduser(FOLDERS[key])])
    return f'Opened {key}.'

def make_tool(name, description, properties, required):
    return {'type': 'function', 'function': {'name': name, 'description': description, 'parameters': {'type': 'object', 'properties': properties, 'required': required}}}

TOOLS = [
    make_tool('open_app', 'Open a Mac application by name.', {'name': {'type': 'string'}}, ['name']),
    make_tool('quit_app', 'Close a running Mac application.', {'name': {'type': 'string'}}, ['name']),
    make_tool('open_website', 'Open a website address.', {'url': {'type': 'string'}}, ['url']),
    make_tool('search_web', 'Search Google for something.', {'query': {'type': 'string'}}, ['query']),
    make_tool('play_youtube', 'Play a song or video on YouTube. Finds the top result and opens it.', {'query': {'type': 'string'}}, ['query']),
    make_tool('set_volume', 'Set speaker volume 0 to 100.', {'level': {'type': 'integer'}}, ['level']),
    make_tool('music_control', 'Play/pause, next, or previous track in Music or Spotify.', {'action': {'type': 'string', 'enum': ['play_pause', 'next', 'previous']}, 'app': {'type': 'string', 'enum': ['Music', 'Spotify']}}, ['action']),
    make_tool('open_folder', 'Open Downloads, Documents or Desktop folder.', {'name': {'type': 'string', 'enum': ['downloads', 'documents', 'desktop']}}, ['name']),
]

HANDLERS = {
    'open_app': lambda a: open_app(a.get('name', '')),
    'quit_app': lambda a: quit_app(a.get('name', '')),
    'open_website': lambda a: open_website(a.get('url', '')),
    'search_web': lambda a: search_web(a.get('query', '')),
    'play_youtube': lambda a: play_youtube(a.get('query', '')),
    'set_volume': lambda a: set_volume(a.get('level', 50)),
    'music_control': lambda a: music_control(a.get('action', 'play_pause'), a.get('app', 'Music')),
    'open_folder': lambda a: open_folder(a.get('name', '')),
}

def run_tool(name, args):
    handler = HANDLERS.get(name)
    if not handler: return 'Unknown tool.'
    try: return handler(args)
    except Exception as error: return f'That failed: {error}'

# ---------------------------- Voice in / out -------------------------------

def speak(text):
    clean = text.replace('*', '').replace('#', '')
    subprocess.run(['say', '-v', VOICE, clean])

def listen(max_seconds=12, silence_seconds=1.2):
    block = int(SAMPLE_RATE * 0.1)
    chunks, quiet, started = [], 0.0, False
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16', blocksize=block) as stream:
        for _ in range(int(max_seconds / 0.1)):
            data, _overflow = stream.read(block)
            chunks.append(data.copy())
            if np.abs(data).mean() > SPEECH_LEVEL:
                started, quiet = True, 0.0
            elif started:
                quiet += 0.1
                if quiet >= silence_seconds: break
    if not started: return None
    audio = sr.AudioData(np.concatenate(chunks).tobytes(), SAMPLE_RATE, 2)
    try: return recognizer.recognize_google(audio)
    except: return None

def recent_messages():
    msgs = history[-20:]
    while msgs and msgs[0]['role'] != 'user': msgs = msgs[1:]
    return msgs

def ask(text):
    history.append({'role': 'user', 'content': text})
    for _ in range(5): 
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{'role': 'system', 'content': SYSTEM_PROMPT}] + recent_messages(),
            tools=TOOLS, max_tokens=300,
        )
        message = response.choices[0].message
        entry = {'role': 'assistant', 'content': message.content or ''}
        if message.tool_calls:
            entry['tool_calls'] = [{'id': c.id, 'type': 'function', 'function': {'name': c.function.name, 'arguments': c.function.arguments}} for c in message.tool_calls]
        history.append(entry)
        if not message.tool_calls: return message.content or 'Done, boss.'
        for call in message.tool_calls:
            try: args = json.loads(call.function.arguments or '{}')
            except: args = {}
            result = run_tool(call.function.name, args)
            print(f'[tool] {call.function.name}({args}) -> {result}')
            history.append({'role': 'tool', 'tool_call_id': call.id, 'content': result})
    return 'Done, boss.'

# ---------------------------- Wake up and talk -----------------------------

session_lock = threading.Lock()

def run_session():
    if not session_lock.acquire(blocking=False): return 
    try:
        print('JARVIS: ' + GREETING)
        speak(GREETING)
        while True:
            text = listen()
            if not text:
                speak('Standing by.')
                break
            print(f'You: {text}')
            if any(word in text.lower() for word in ('goodbye', 'bye', "that's all", 'that is all')):
                speak('Very good, boss.')
                break
            try:
                reply = ask(text)
            except Exception as error:
                print(f'Error: {error}')
                speak('Sorry boss, I hit a problem.')
                break
            print(f'JARVIS: {reply}')
            speak(reply)
    finally:
        session_lock.release()

tap_times = []
COMMAND_KEYS = (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r)

def on_press(key):
    if key in COMMAND_KEYS:
        now = time.time()
        tap_times.append(now)
        while tap_times and now - tap_times[0] > TAP_WINDOW_SECONDS: tap_times.pop(0)
        if len(tap_times) >= TAPS_NEEDED:
            tap_times.clear()
            threading.Thread(target=run_session, daemon=True).start()
    else:
        tap_times.clear() 

if __name__ == '__main__':
    print('JARVIS is ready. Tap Command 3 times. Press Ctrl+C to quit.')
    with keyboard.Listener(on_press=on_press) as listener:
        try: listener.join()
        except KeyboardInterrupt: print('Shutting down.')

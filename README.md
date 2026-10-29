# JARVIS: AI Voice Assistant 🤖🎙️

> ⚠️ **macOS ONLY:** This project relies heavily on AppleScript (`osascript`), macOS native Text-to-Speech (`say`), and Mac-specific permission models (Accessibility/Input Monitoring). It **will not** run on Windows or Linux.

JARVIS is a custom, hands-free AI voice assistant designed to control your Mac. It uses **Function Calling** to let the AI decide which tools to use (like opening apps, playing YouTube, or changing volume) based on your natural voice commands.

## 🧠 AI Model: DeepSeek Only
This project is specifically configured to use the **DeepSeek API**. 
- It uses the model `deepseek-flash`.
- It routes requests to `https://api.deepseek.com`.
*(Note: You can change it to use OpenAI by editing the `base_url` and `MODEL` variables in `jarvis.py`, but by default, it requires a DeepSeek API key).*

## 🔑 API Key Requirement (BYOK - Bring Your Own Key)
**This repository does NOT contain an API key.** To run this project, you must generate your own DeepSeek API key. 
1. Go to [platform.deepseek.com](https://platform.deepseek.com) and create an account.
2. Generate an API key.
3. Create a `.env` file in the root folder and add your key: `DEEPSEEK_API_KEY=your_key_here`

## ✨ Features
- **Hands-Free Wake Word:** Tap the Command (⌘) key 3 times to wake JARVIS.
- **Agentic Tool Calling:** The AI decides which tools to use based on your natural language.
- **Media Control:** Search and play YouTube videos directly in Brave Browser.
- **System Control:** Open/close apps, adjust Mac volume, and open system folders.
- **Real-time Audio:** Captures audio via microphone, detects silence, and uses Google Speech Recognition.
- **Text-to-Speech:** Uses macOS native `say` command with premium voice profiles.

## 🛠️ Tech Stack
- **Language:** Python 3.9+
- **AI/LLM:** OpenAI Python SDK (pointed to DeepSeek API)
- **Audio:** `sounddevice`, `numpy`, `SpeechRecognition`
- **System Automation:** AppleScript (`osascript`), `subprocess`
- **Keyboard Hooking:** `pynput`

## ⚙️ Setup Instructions (macOS)

1. Clone the repository:
   ```bash
   git clone https://github.com/basireddytharunkumarreddy18-red/jarvis-ai-assistant.git
   cd jarvis-ai-assistant

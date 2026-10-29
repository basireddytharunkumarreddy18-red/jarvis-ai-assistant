# JARVIS: AI Voice Assistant 🤖🎙️

> ⚠️ **macOS ONLY:** This project relies heavily on AppleScript (`osascript`), macOS native Text-to-Speech (`say`), and Mac-specific permission models (Accessibility/Input Monitoring). It **will not** run on Windows or Linux.

JARVIS is a custom, hands-free AI voice assistant designed to control your Mac. It uses **Function Calling** to let the AI decide which tools to use (like opening apps, playing YouTube, or changing volume) based on your natural voice commands.

---

## 🚨 Default Setup: DeepSeek API

By default, this project is configured to use the **DeepSeek API**. It uses the model `deepseek-flash` and routes requests to `https://api.deepseek.com`. 

**This repository does NOT contain an API key (BYOK - Bring Your Own Key).** To run this project out-of-the-box, you must:
1. Go to [platform.deepseek.com](https://platform.deepseek.com) and create an account.
2. Generate an API key.
3. Create a `.env` file in the root folder and add your key: `DEEPSEEK_API_KEY=your_key_here`

---

## 🔄 How to change the code to use another API (e.g., OpenAI)

If you want to use OpenAI (ChatGPT), Anthropic (Claude), or another provider instead of DeepSeek, you can easily modify the code. 

Here is exactly what you need to change in `jarvis.py`:

### 1. Change the Model and Base URL
Scroll down to around line 21 and update the `MODEL` variable. Then update the `client` initialization to remove the DeepSeek `base_url`.

**Change this:**
```python
MODEL = 'deepseek-flash'
client = OpenAI(api_key=os.getenv('DEEPSEEK_API_KEY'), base_url='https://api.deepseek.com')

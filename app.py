import sys
import os
import json
import pickle
import random
import numpy as np
import pyautogui
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

# Add project root to path if necessary
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.speech.engine import speak, command
from core.utils.helpers import wishMe
from core.commands.handlers import social_media, schedule, browsing
from core.automation.system import openApp, closeApp, condition

# Define paths for models
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
INTENTS_PATH = os.path.join(MODELS_DIR, "intents.json")
MODEL_PATH = os.path.join(MODELS_DIR, "chat_model.h5")
TOKENIZER_PATH = os.path.join(MODELS_DIR, "tokenizer.pkl")
LABEL_ENCODER_PATH = os.path.join(MODELS_DIR, "label_encoder.pkl")

# Load model artifacts
with open(INTENTS_PATH) as file:
    data = json.load(file)

model = load_model(MODEL_PATH)

with open(TOKENIZER_PATH, "rb") as f:
    tokenizer = pickle.load(f)

with open(LABEL_ENCODER_PATH, "rb") as encoder_file:
    label_encoder = pickle.load(encoder_file)

if __name__ == "__main__":
    wishMe(speak)
    
    while True:
        query = command().lower()
        
        if query == "none":
            continue

        if any(sm in query for sm in ['facebook', 'discord', 'whatsapp', 'instagram', 'youtube']):
            social_media(query, speak)
            
        elif any(sch in query for sch in ["university time table", "schedule"]):
            schedule(speak)
            
        elif any(v in query for v in ["volume up", "increase volume"]):
            pyautogui.press("volumeup")
            speak("Volume increased")
            
        elif any(v in query for v in ["volume down", "decrease volume"]):
            pyautogui.press("volumedown")
            speak("Volume decreased")
            
        elif any(v in query for v in ["volume mute", "mute the sound"]):
            pyautogui.press("volumemute")
            speak("Volume muted")
            
        elif any(app in query for app in ["open calculator", "open notepad", "open paint"]):
            openApp(query, speak)
            
        elif any(app in query for app in ["close calculator", "close notepad", "close paint"]):
            closeApp(query, speak)
            
        elif any(kw in query for kw in ["what", "who", "how", "hi", "thanks", "hello"]):
            padded_sequences = pad_sequences(tokenizer.texts_to_sequences([query]), maxlen=20, truncating='post')
            result = model.predict(padded_sequences)
            tag = label_encoder.inverse_transform([np.argmax(result)])

            for i in data['intents']:
                if i['tag'] == tag:
                    speak(np.random.choice(i['responses']))
                    
        elif any(br in query for br in ["open google", "open edge"]):
            browsing(query, speak, command)
            
        elif any(sys_c in query for sys_c in ["system condition", "condition of the system"]):
            speak("checking the system condition")
            condition(speak)
            
        elif "exit" in query:
            speak("Goodbye Boss!")
            sys.exit()

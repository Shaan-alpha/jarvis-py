import json
import pickle
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import random
import numpy as np

import os

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
INTENTS_PATH = os.path.join(MODELS_DIR, "intents.json")
MODEL_PATH = os.path.join(MODELS_DIR, "chat_model.h5")
TOKENIZER_PATH = os.path.join(MODELS_DIR, "tokenizer.pkl")
LABEL_ENCODER_PATH = os.path.join(MODELS_DIR, "label_encoder.pkl")

with open(INTENTS_PATH) as file:
    data = json.load(file)

model = load_model(MODEL_PATH)

with open(TOKENIZER_PATH, "rb") as f:
    tokenizer=pickle.load(f)

with open(LABEL_ENCODER_PATH, "rb") as encoder_file:
    label_encoder=pickle.load(encoder_file)

while True:
    input_text = input("Enter your command-> ")
    padded_sequences = pad_sequences(tokenizer.texts_to_sequences([input_text]), maxlen=20, truncating='post')
    result = model.predict(padded_sequences)
    tag = label_encoder.inverse_transform([np.argmax(result)])

    for i in data['intents']:
        if i['tag'] == tag:
            print(np.random.choice(i['responses']))


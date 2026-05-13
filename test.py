from core.speech.vosk_engine import listen

while True:

    query = listen()

    print(query)
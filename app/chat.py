def chat(message, history):
    history = history or []
    response = "That's a good question!"
    history.append((message, response))
    return history, history
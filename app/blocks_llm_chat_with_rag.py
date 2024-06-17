def append_user(message, chat_history):
    chat_history.append((message, None))
    return chat_history

def append_ai(message, chat_history):
    chat_history.append((None, message))
    return chat_history

def clear_log(thread):
    return ["", "", thread]
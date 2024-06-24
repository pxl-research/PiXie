from app import vector_store, reranker, llm, chain
from services import utils
from langchain_community.chat_message_histories import ChatMessageHistory


def append_user(message, chat_history):
    chat_history.append((message, None))
    return chat_history


def append_ai(message, chat_history):
    # TODO: Implement the following logic separately so that it is not coded into the UI
    # Current issue is the streaming answer, could not get it working from outside the UI
    top_docs = vector_store.retrieve_top_chunks(message, 10)
    final_docs = reranker.rerank(message, top_docs)
    final_chain = chain.get_chain(llm)

    memory_messages = utils.get_chat_history(utils.history_path)
    thread_history = ChatMessageHistory(messages=memory_messages[-3:])

    full_answer = ""

    for s in final_chain.stream(
        {"chat_history": thread_history, "docs": final_docs, "question": message}
    ):
        chunk = s.content
        full_answer += chunk
        chat_history[-1] = (message, full_answer)
        yield "", chat_history, ""

    utils.save_chat_history(utils.history_path, message, full_answer)


def clear_log():
    return ["", ""]

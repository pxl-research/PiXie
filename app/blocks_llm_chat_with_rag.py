from app import vector_store, reranker, llm, chain

def append_user(message, chat_history):
    chat_history.append((message, None))
    return chat_history


def append_ai(thread, message, chat_history, log):
    top_docs = vector_store.retrieve_top_docs(message, 15)
    final_docs = reranker.rerank(message, top_docs)
    final_chain = chain.get_chain(final_docs, message, llm)
    print(final_chain)
    full_answer = ""

    for s in final_chain.stream({"docs": final_docs, "question": message}):
        chunk = s.content
        print(chunk)
        full_answer += chunk
        chat_history[-1] = (message, full_answer)
        yield chunk, chat_history, ""


def clear_log(thread):
    return ["", "", thread]

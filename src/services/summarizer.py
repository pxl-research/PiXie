from typing import List, Any
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.llm import LLMChain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document


class Summarizer:
    """
    A class for summarizing a list of documents using a Language Learning Model (LLM)
    and a prompt template.

    Attributes:
        llm: The language model (LLM) used to generate summaries.
    """

    def __init__(self, llm: Any) -> None:
        """
        Initializes the Summarizer with a specified LLM.

        Args:
            llm: An LLM model object with the necessary functions to process prompts.
        """
        self.llm = llm

    def summarize(self, doc: Document) -> str:
        """
        Generates a summary of a list of documents.

        Args:
            doc: A document to be summarized.

        Returns:
            A string containing the consolidated summary of the documents.
        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Write a concise summary of the following:\n\n{context}. Max 500 characters or 1 paragraph.",
                )
            ]
        )

        chain = create_stuff_documents_chain(self.llm.model, prompt)
        print(type(doc))
        result = chain.invoke({"context": [doc]})

        return result

from typing import List, Any
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.llm import LLMChain
from langchain_core.prompts import ChatPromptTemplate


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

    def summarize(self, docs: List[str]) -> str:
        """
        Generates a summary of a list of documents.

        Args:
            docs: A list of document strings to be summarized.

        Returns:
            A string containing the consolidated summary of the documents.
        """
        prompt = ChatPromptTemplate.from_messages(
            [("system", "Write a concise summary of the following:\n\n{context}")]
        )

        chain = create_stuff_documents_chain(self.llm.model, prompt)
        result = chain.invoke({"context": docs})

        return result

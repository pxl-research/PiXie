import logging
from services import utils
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from typing import Any
from langchain.schema import SystemMessage, AIMessage, HumanMessage
from langchain.chains import LLMChain

from typing import List, Dict

DEFAULT_TEMPLATE_PATH = "src/assets/helper/system_message_prompt.txt"


class LLMChainBuilder:
    """
    A builder class for constructing an LLM interaction chain with specified prompts and models.

    Parameters:
    - selected_llm: The language model to be used in the chain.
    - template_path: The file path to the system message prompt template.
    """

    def __init__(self, selected_llm: Any, template_path: str = DEFAULT_TEMPLATE_PATH):
        self.selected_llm = selected_llm
        self.template_path = template_path

    def build_llm_chain(self, chat_history: str, docs: str, question: str) -> Any:
        """
        Build and return the LLM interaction chain with chat history.

        Parameters:
        - chat_history: List[Dict[str, str]]
            The chat history formatted as a list of messages with 'role' and 'content'.

        Returns:
        - The constructed LLM chain that combines the prompt templates with the language model.
        """
        logging.info(f"Loading template from {self.template_path}")
        template_content = utils.read_template(self.template_path)

        prompt_template = PromptTemplate(
            input_variables=["chat_history", "docs", "question"],
            template=template_content,
        )

        # Build the LLM chain
        chain = LLMChain(llm=self.selected_llm.model, prompt=prompt_template)
        logging.info("LLM chain successfully built with chat history")
        return chain

import logging
from services import utils
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from typing import Any

DEFAULT_TEMPLATE_PATH = "../assets/helper/system_message_prompt.txt"


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

    def build_llm_chain(self) -> Any:
        """
        Build and return the LLM interaction chain.

        Returns:
        - The constructed LLM chain that combines the prompt templates with the language model.
        """
        logging.info(f"Loading template from {self.template_path}")
        template_content = utils.read_template(self.template_path)

        # Build the system and human prompts
        system_prompt = SystemMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=["docs"], template=template_content)
        )
        human_prompt = HumanMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=["question"], template="{question}")
        )

        # Combine the prompts into a ChatPromptTemplate
        prompt_template = ChatPromptTemplate(
            input_variables=["docs", "question"], messages=[system_prompt, human_prompt]
        )

        # Return the final LLM chain
        chain = prompt_template | self.selected_llm.model
        logging.info("LLM chain successfully built")
        return chain

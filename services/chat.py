from services import utils
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, PromptTemplate, SystemMessagePromptTemplate


class Chain:

    def get_chain(self, selected_llm):

        template = utils.read_template("../assets/helper/system_message_prompt.txt")

        system_prompt = SystemMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=["docs"], template=template)
        )

        human_prompt = HumanMessagePromptTemplate(
            prompt=PromptTemplate(input_variables=["question"], template="{question}")
        )

        messages = [system_prompt, human_prompt]

        prompt_template = ChatPromptTemplate(
            input_variables=["docs", "question"], messages=messages
        )

        chain = prompt_template | selected_llm.model

        return chain

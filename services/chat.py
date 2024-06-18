from langchain.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from services import utils
import html

class Chain():
   
    def get_chain(self, retrieved_chunks, question, selected_llm):
        
        question = html.escape(question)
        template = utils.read_template("../helper/system_message_prompt.txt")

        system_prompt = SystemMessagePromptTemplate(
          prompt=PromptTemplate(
              input_variables=["docs"], template=template
          )
        )

        human_prompt = HumanMessagePromptTemplate(
          prompt=PromptTemplate(
              input_variables=["question"], template="{question}"
          )
        )

        messages = [system_prompt, human_prompt]

        prompt_template = ChatPromptTemplate(
            input_variables=["docs", "question"],
            messages=messages
        )

        chain = prompt_template | selected_llm.model

        return chain

        #output = chain.invoke({"docs": retrieved_chunks, "question": question})
        #return output.content
        
        # chunks = []

        # for s in chain.stream({"docs": retrieved_chunks, "question": question}):
        #     chunk = s.content
        #     print(chunk)
        #     chunks.append(chunk)
        #     yield chunk
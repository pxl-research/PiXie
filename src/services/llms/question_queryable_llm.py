# -----------------------------------------------------------------
# QuestionQueryableLLM
# -----------------------------------------------------------------
from typing import Optional
import json
import logging
from langchain.schema import SystemMessage

from services.abstractclasses.llm import LLM


class QuestionQueryableLLM:
    SUPPORTED_LANGUAGES = {
        "en": "english",
        "af": "dutch",  # remap af (Afrikaans) to Dutch
        "nl": "dutch",
        "fr": "french",
        "de": "german",
    }

    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        You are an AI assistant that helps reformulate user questions to be more structured.
        
        - Translate the given question to {language_name}.
        - Ensure the question is still natural and clear for a database search.
        - Only rewrite the question in plain text and only return the reformulated question.
        
        Here is the schema of the database table(s):
        ```
        {schema}
        ```
        
        Original Question: "{question}"
        
        Reformulated Question:
        """

    def generate(
        self, schema: dict[str, str], question: str, language: Optional[str]
    ) -> Optional[str]:
        language_name = "english"
        if language in self.SUPPORTED_LANGUAGES:
            language_name = self.SUPPORTED_LANGUAGES[language]

        system_prompt = self.system_prompt_template.format(
            schema=json.dumps(schema, indent=4),
            question=question,
            language_name=language_name,
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            logging.error(f"Error: {str(e)}")
        return None

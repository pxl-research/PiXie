# -----------------------------------------------------------------
# QuestionQueryableLLM
# -----------------------------------------------------------------
from typing import Optional
import json
import logging
import os
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
        You are an AI assistant that helps reformulate user questions to be more structured for generating Postgres SQL queries.

        - Translate the given question to {language_name}.
        - Reformulate the translated question to be more precise and database-query friendly.
        - Ensure the reformulated question is still clear and reflects the original intent for a database search.
        - Convert all adjectives and nouns in the reformulated question to their stem form.
        For example, "running" becomes "run", "cars" becomes "car", "fastest" becomes "fast", "witte" becomes "wit", "mooie" becomes "mooi".
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
        language_name = self.SUPPORTED_LANGUAGES[os.getenv("DEFAULT_LANGUAGE")]
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

from typing import Optional
import json
import logging
from langchain.schema import SystemMessage

from services.abstractclasses.llm import LLM


class SQLQueryCorrectorLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        You are an intelligent assistant that corrects given NoSQL-like PostgreSQL queries. Given a schema, question, query which needs to be corrected
        and an error message, you need generate a correct SQL query.
        Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.

        Rules to keep in mind:
        * The query should select and filter data stored as JSONB in the column r.attributes using PostgreSQL syntax
        and proper type casting according to the given schema:
            SELECT r.attributes
            FROM tabular_rows r
        * ALWAYS include the following RIGHT JOIN to enable file-based scoring:
            RIGHT JOIN hybrid_search_file_based
            ON r.id = hybrid_search_file_based.id
        
        
        Here is the schema of the database table(s):
        ```
        {schema}
        ```
        
        Given Question:
        "{question}"

        Query To Correct:
        {query_to_correct}

        Error Message:
        "{error_message}"
    
        Corrected query:
        """

    def generate(
        self,
        schema: dict[str, str],
        question: str,
        query_to_correct: str,
        error_message: str,
    ) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(
            schema=json.dumps(schema, indent=4),
            question=question,
            query_to_correct=query_to_correct,
            error_message=error_message,
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            logging.error(f"Error: {str(e)}")
        return None

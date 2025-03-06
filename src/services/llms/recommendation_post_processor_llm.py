# -----------------------------------------------------------------
# RecommendationPostProcessorLLM
# -----------------------------------------------------------------
from typing import Optional
import logging
from langchain.schema import SystemMessage

from services.abstractclasses.llm import LLM


class RecommendationSQLPostProcessorLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        You are an intelligent assistant that corrects given NoSQL-like PostgreSQL queries.
        Correct the input query to comply with these rules for a recommendation system:

        * Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.

        Only modify the WHERE, HAVING clauses.
        Identify and REMOVE any of the following from the WHERE or HAVING clauses:
        * Exact textual comparisons:
            Conditions using operators like `=`, `<>`, `!=` on text attributes (r.attributes->>'field'). 
            Example: r.attributes->>'color' = 'red'
        * Textual NULL checks:
            Conditions like `r.attributes->>'field' IS NULL` or `r.attributes->>'field' IS NOT NULL`.
        * LIKE operator:
            Conditions using `LIKE` or `ILIKE` for text attributes.
            Example: r.attributes->>'description' LIKE '%keyword%'
        * Regular expression matching:
            Conditions using `~` or `~*` for text attributes. 
            Example: r.attributes->>'name' ~* 'regex'

        Keep and ensure correct type casting for:
        * Numerical comparisons:  
            Conditions using `>`, `<`, `>=`, `<=`, `=`, `<>` on numerical attributes (after proper casting like `(r.attributes->>'volume')::INTEGER > 40`).
        * Date/Time comparisons:
            Conditions using operators and functions on date or time attributes (after proper casting like `(r.attributes->>'date')::DATE BETWEEN ...`).
        * Ensure all numerical, date, and time comparisons in WHERE/HAVING clauses have correct type casting based on the implied or provided schema.

        Input Query:
        {query_to_correct}

        Corrected Query:
        """

    def generate(self, query_to_correct: str) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(
            query_to_correct=query_to_correct
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            logging.error(f"Error: {str(e)}")
        return None

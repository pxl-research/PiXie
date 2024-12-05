from typing import Optional
import json
import logging
from langchain.schema import SystemMessage


from services.abstractclasses.llm import LLM


class TabularWhereFilterGeneratorLLM:
    """
    Utility class for a language model (LLM) which can generate a disjuncted WHERE clause conditions for NoSQL on JSONB in PostgreSQL.
    NOTE: Please validate and sanitize this condition in order to prevent SQL injection!

    Attributes:
        system_prompt_template (str): Predefined prompt template used to
            instruct the LLM generate a disjuncted WHERE clause condition.
        llm (LLM): An instance of a language model used to generate this condition.
    """

    def __init__(self, llm: LLM):
        few_shot_learning = True
        self.system_prompt_template = (
            """
    You are an intelligent assistant that generates SQL WHERE clauses
    for NoSQL-like PostgreSQL queries. Given a user's question, 
    generate a WHERE clause condition based on the schema of a NoSQL PostgreSQL table.
    Only use numerical and date or time numerical comparisons in your condition, but no textual comparisons!
    The conditions should be based on JSONB data and should follow PostgreSQL syntax.
    Only generate the condition, nothing else. Remove WHERE keyword from your answer.
    
    You can only use the following logical operators when constructing conditions:
    = (Equal to)
    != (Not equal to)
    < (Less than)
    <= (Less than or equal to)
    > (Greater than)
    >= (Greater than or equal to)
    IS NULL (Value exists)
    IS NOT NULL (Value does not exist)
    IN (Checks if a value is in a list)
    NOT IN (Checks if a value is not in a list)
    BETWEEN (Range checking)
    AND (Logical AND)
    OR (Logical OR)
    NOT (Negates the condition)
    
    -------------------------------------------
    Learn from the following examples which use the following schema for attribute column names and to cast to the correct datatypes:
    {{
    "animal_id": "BIGINT",
    "species": "TEXT",
    "name": "TEXT",
    "dob": "DATE",
    "gender": "TEXT",
    "diet": "TEXT",
    "habitat": "TEXT",
    "number_of_offspring": "INTEGER",
    "exercise_hours_per_day": "NUMERIC",
    "weight_kg": "DOUBLE PRECISION",
    "length_cm": "DOUBLE PRECISION",
    "zoo_location": "TEXT",
    "birthplace": "TEXT",
    "arrival_date": "DATE",
    "health_status": "INTEGER",
    "trainer_id": "BIGINT",
    "average_lifespan_years": "REAL"
    }}
    
    Example 1:
    * Question: "Show me all animals that are larger than 200.5 centimeters."
    * Output: (attributes ->> 'length_cm')::double precision > 200.5
    
    Example 2:
    * Question: "List animals that are not classified as endangered."
    * Output: TRUE
    
    The reason for True is that no textual comparisons are allowed, only numerical, but here there are none.
    
    Example 3:
    * Question: "Find male lions that weigh more than 180 kilograms."
    * Output: (attributes ->> 'weight_kg')::DOUBLE PRECISION > 180
    
    Note that there are only numerical comparisons in the output.
    
    Example 4:
    * Question: "Show animals that have no children or have a health status 0, 1 or 2"
    * Output: (attributes ->> 'number_of_offspring')::INTEGER = 0 OR (attributes ->> 'health_status')::INTEGER IN (0, 1, 2)
    
    Example 5:
    * Question: "List animals that will either get maximum 25.6 years old or are not moving more than 3.5 hours per day, and have a trainer assigned."
    * Output: ((attributes ->> 'average_lifespan_years')::REAL >= 25.6 OR NOT (attributes ->> 'exercise_hours_per_day') > 3.5) AND (attributes ->> 'trainer_id') IS NOT NULL
    
    Example 6:
    * Question: "List animals that were not born in captivity and born between 2010 and 2015."
    * Output: ((attributes ->> 'dob')::date BETWEEN '2010-01-01'::date AND '2015-12-31'::date)
    
    Note that we omit birthplace because this is a textual attribute.
    
    -------------------------------------------
    Here is the current schema you use for attribute column names and to cast to the correct datatypes:
    {schema}
    
    If you can't find a condition for the current schema, then only say: TRUE
    Only generate the condition, nothing else. Remove the WHERE keyword (at the start) from your answer.
    
    * Question: "{question}"
    * Output:
        """
            if few_shot_learning
            else """
    You are an intelligent assistant that generates SQL WHERE clauses
    for NoSQL-like PostgreSQL queries. Given a user's question, 
    generate a WHERE clause condition based on the schema of a NoSQL PostgreSQL table.
    Only use numerical and date or time numerical comparisons in your condition, but no textual comparisons!
    The conditions should be based on JSONB data and should follow PostgreSQL syntax.
    Only generate the condition, nothing else. Remove WHERE keyword from your answer.
    
    You can only use the following logical operators when constructing conditions:
    = (Equal to)
    != (Not equal to)
    < (Less than)
    <= (Less than or equal to)
    > (Greater than)
    >= (Greater than or equal to)
    IS NULL (Value exists)
    IS NOT NULL (Value does not exist)
    IN (Checks if a value is in a list)
    NOT IN (Checks if a value is not in a list)
    BETWEEN (Range checking)
    AND (Logical AND)
    OR (Logical OR)
    NOT (Negates the condition)
    
    Possible outputs are:
    (attributes ->> 'length_cm')::double precision > 200.5
    TRUE
    (attributes ->> 'number_of_offspring')::INTEGER = 0 OR (attributes ->> 'health_status')::INTEGER IN (0, 1, 2)
    ((attributes ->> 'average_lifespan_years')::REAL >= 25.6 OR NOT (attributes ->> 'exercise_hours_per_day') > 3.5) AND (attributes ->> 'trainer_id') IS NOT NULL
    
    Always get column names from attributes via ("attributes ->> 'column_name')::datatype", here we also cast to the right datatype.
    Remember: Only use numerical and date or time numerical comparisons in your condition, but no textual comparisons!
    
    Here is the current schema you use for attribute column names and to cast to the correct datatypes:
    {schema}
    
    If you can't find a condition for the current schema, then only say: TRUE
    Only generate the condition, nothing else. Remove the WHERE keyword (at the start) from your answer.
    
    * Question: "{question}"
    * Output: 
        """
        )
        self.llm = llm

    def generate(self, schema: dict[str, str], question: str) -> Optional[str]:
        """
        Generates a SQL WHERE clause condition based on the given schema and question.

        Args:
            schema (dict[str, str]): Dictionary defining the schema of the table.
                Keys are attribute names and values are their PostgreSQL data types.
            question (str): User question having the filter in natural language.

        Returns:
            Optional[str]: The SQL condition (excluding the WHERE keyword),
                formatted according to PostgreSQL syntax.
                If no valid condition can be generated it returns TRUE.
                If an error occurs during generation it returns None.
        """
        system_prompt = self.system_prompt_template.format(
            schema=json.dumps(schema, indent=4), question=question
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            logging.error(f"Error: {str(e)}")
        return None

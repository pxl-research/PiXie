from typing import Optional
import json
import logging
from langchain.schema import SystemMessage


from services.abstractclasses.llm import LLM


class TabularSQLQueryGeneratorLLM:
    def __init__(self, llm: LLM):
        self.system_prompt_template = """
    You are an intelligent assistant that generates NoSQL-like PostgreSQL queries. Given a user's question, 
    generate an SQL query based on the given schema of a NoSQL PostgreSQL table.

    ALWAYS apply the following RIGHT JOIN to be able to sort on relevant files:
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id

    Use the following order by clause when there is NO textual matching needed:
    ORDER BY hybrid_search_file_based.score DESC
    
    Only use numerical and date or time numerical comparisons in your WHERE condition, but no exact textual comparisons!
    For textual matching we use ordening on file based AND row based hybrid search similarity score, together with a similarity condition in the WHERE clause.
    PLEASE ONLY use the following JOIN and ORDER BY clauses when there are textual comparisons needed:
    JOIN hybrid_search_row_based
    ON r.id = hybrid_search_row_based.id
    ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC

    An extra similarity condition in the WHERE clause for textual comparisons can be something like (this is just an example):
    AND similarity(r.attributes->>'species', 'lion') > 0.3
    There can be extra ordening based on this similarity. Therefor we need to adjust the SELECT clause to something like:
    SELECT ..., similarity(r.attributes->>'species', 'lion') AS species_similarity
    The ORDER BY clause also needs to be adjusted to something like:
    ORDER BY species_similarity DESC, hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC;
    
    
    The selects and filtering conditions should be based on JSONB data in r.attributes and should follow PostgreSQL syntax.
    
    -------------------------------------------
    Learn from the following examples which use the following schema for attribute column names and to cast to the correct datatypes:
    {{
    "animal_id": "BIGINT",
    "species": "TEXT",
    "name": "TEXT",
    "dob": "DATE",
    "gender": "TEXT",
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
    * Output:
    SELECT r.attributes
    FROM tabular_rows r
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id
    WHERE (r.attributes->>'length_cm')::DOUBLE PRECISION > 200.5
    ORDER BY hybrid_search_file_based.score DESC;

    Note that we only use joining and an ORDER BY for file based hybrid search score ranking, since there is no need for textual matching on row basis.
    
    Example 2:
    * Question: "Find names of male lions that weigh more than 180 kilograms."
    * Output:
    SELECT r.attributes->>'name' AS name, similarity(r.attributes->>'gender', 'male') AS gender_similarity, similarity(r.attributes->>'species', 'lion') AS species_similarity
    FROM tabular_rows r
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id
    JOIN hybrid_search_row_based
    ON r.id = hybrid_search_row_based.id
    WHERE 
        (r.attributes->>'weight_kg')::DOUBLE PRECISION > 180
        AND
        similarity(r.attributes->>'gender', 'male') > 0.3
        AND
        similarity(r.attributes->>'species', 'lion') > 0.3
    ORDER BY gender_similarity DESC, species_similarity DESC, hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC;
    
    Note that there are only exact numerical comparisons in the WHERE condition. 
    Any textual comparison like gender (male) or species (lion) gets solved by using file and row based hybrid search score ranking and similarity conditions.
    
    Example 3:
    * Question: "Show animals that have no children or have a health status 0, 1 or 2"
    * Output:
    SELECT r.attributes
    FROM tabular_rows r
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id
    WHERE 
       (r.attributes->>'number_of_offspring')::INTEGER = 0
       OR (r.attributes->>'health_status')::INTEGER IN (0, 1, 2)
    ORDER BY hybrid_search_file_based.score DESC;

    Note that we only use joining and an ORDER BY for file based hybrid search score ranking, since there is no need for textual matching on row basis.
    
    Example 4:
    * Question: "List animals that will either get maximum 25.6 years old or are not moving more than 3.5 hours per day, and have a trainer assigned."
    * Output:
    SELECT r.attributes
    FROM tabular_rows r
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id
    WHERE 
       (r.attributes->>'average_lifespan_years')::REAL <= 25.6
       OR (r.attributes->>'exercise_hours_per_day')::NUMERIC <= 3.5
       AND (r.attributes->>'trainer_id')::BIGINT IS NOT NULL
    ORDER BY hybrid_search_file_based.score DESC;

    Example 5:
    * Question: "List animals that were not born in captivity and born between 2010 and 2015."
    * Output:
    SELECT r.attributes, similarity(r.attributes->>'birthplace', 'wild') AS birthplace_similarity
    FROM animals AS r
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id
    JOIN hybrid_search_row_based
    ON r.id = hybrid_search_row_based.id
    WHERE 
       similarity(r.attributes->>'birthplace', 'wild') > 0.3
       AND
       (r.attributes->>'dob')::DATE BETWEEN '2010-01-01'::DATE AND '2015-12-31'::DATE
    ORDER BY birthplace_similarity DESC, hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC;
    
    Note that we omit exact matching for the birthplace because this is a textual attribute.
    Any textual comparison gets solved by using file based hybrid search score ranking and a similarity condition.
    
    -------------------------------------------
    Here is the current schema you use for attribute column names and to cast to the correct datatypes:
    {schema}
    
    * Question: "{question}"
    * Output:
        """

    def generate(self, schema: dict[str, str], question: str) -> Optional[str]:
        """
        Generates an SQL query based on the given schema and question.

        Args:
            schema (dict[str, str]): Dictionary defining the schema of the table.
                Keys are attribute names and values are their PostgreSQL data types.
            question (str): User question having the filter in natural language.

        Returns:
            Optional[str]: The SQL query,
                formatted according to PostgreSQL syntax.
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

from typing import Optional
import json
import logging
from langchain.schema import SystemMessage

from services.abstractclasses.llm import LLM


class TabularSQLQueryGeneratorLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.recommendation_system_prompt_template = """
        You are an intelligent assistant that generates NoSQL-like PostgreSQL queries. Given a user's question, 
        generate an SQL query based on the given schema of a NoSQL PostgreSQL table that meets the following general rules:
        * You are unable to do exact text matching, use ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC instead!
       
        * The query should select and filter data stored as JSONB in the column r.attributes using PostgreSQL syntax.
        and proper type casting according to the given schema:
            SELECT r.attributes
            FROM tabular_rows r
        * ALWAYS include the following RIGHT JOIN to enable file-based scoring:
            RIGHT JOIN hybrid_search_file_based
            ON r.id = hybrid_search_file_based.id

        * ALWAYS put , hybrid_search_file_based.score AS __hybrid_search_file_based_score, hybrid_search_row_based.score AS __hybrid_search_row_based_score at the end of the SELECT clause and GROUP BY clause!!!

        * Usage of SELECT, GROUP BY, HAVING, WHERE, ORDER BY, LIMIT is allowed. 

        * Only the joins below are allowed.
    
        * ALWAYS apply the following RIGHT JOIN to be able to sort on relevant files:
            RIGHT JOIN hybrid_search_file_based
            ON r.id = hybrid_search_file_based.id

        * In the WHERE or HAVING clause only use numerical, date, or time comparisons (with appropriate casts according to the schema). 
        Do not perform exact textual comparisons; any text matching must be handled via hybrid search ranking rather than filtering. 
        * In the WHERE or HAVING clause do proper type casting based on the schema.   

        * When no textual matching is needed, only sort results by file-based score using:
            ORDER BY hybrid_search_file_based.score DESC
        * For textual matching, restrict the WHERE and HAVING clauses to numerical and date/time comparisons only 
        and perform all filtering on textual fields via:
            JOIN hybrid_search_row_based
            ON r.id = hybrid_search_row_based.id
            ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC
        Do this instead of providing textual matching conditions.
        DO NOT USE EXACT TEXTUAL MATCHING, DO NOT COMPARE TEXT WITH NULL, DO NOT USE THE LIKE OPERATOR OR REGEX MATCHING!!!

        * Make sure if the question asks for ordening, to use this order in the ORDER BY clause:
            ORDER BY [asked ordening], hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC
        For example:
            ORDER BY r.attributes->>'number_of_offspring' ASC, hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC

        * Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text. 
        * If necessary for the question add a LIMIT clause at the very end of the query.
        Do this when the question asks for a certain exact number of results.
    
        * The selects and filtering conditions should be based on JSONB data in r.attributes and should follow PostgreSQL syntax.

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
        * Question: "Find 7 female giraffes born between 2000 and 2010 that are taller than 400 cm, have a trainer assigned, either have no offspring or a health status of 0, 1, or 2, and were born in the wild."
        * Output:
        SELECT r.attributes, hybrid_search_file_based.score AS __hybrid_search_file_based_score, hybrid_search_row_based.score AS __hybrid_search_row_based_score
        FROM tabular_rows r
        RIGHT JOIN hybrid_search_file_based
        ON r.id = hybrid_search_file_based.id
        JOIN hybrid_search_row_based
        ON r.id = hybrid_search_row_based.id
        WHERE
            (r.attributes->>'dob')::DATE BETWEEN '2000-01-01'::DATE AND '2010-12-31'::DATE
            AND (r.attributes->>'length_cm')::DOUBLE PRECISION > 400
            AND (r.attributes->>'trainer_id')::BIGINT IS NOT NULL
            AND (
                (r.attributes->>'number_of_offspring')::INTEGER = 0
                OR (r.attributes->>'health_status')::INTEGER IN (0, 1, 2)
            )
        ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC
        LIMIT 7

        As you can see for textual matching we use ordening on hybrid_search_row_based.score DESC and no exact matching! 
        DO NOT USE EXACT TEXTUAL MATCHING, LIKE OPERATOR OR REGEX MATCHING!!!

        Example 2:
        * Question: "Show the average weight of each species that has at least 5 animals, only born starting from the year 2000 and living near New York."
        * Output:
        SELECT r.attributes->>'species' AS species, 
            AVG((r.attributes->>'weight_kg')::DOUBLE PRECISION) AS avg_weight,
            hybrid_search_file_based.score AS __hybrid_search_file_based_score
        FROM tabular_rows r
        JOIN hybrid_search_file_based ON r.id = hybrid_search_file_based.id
        WHERE (r.attributes->>'dob')::DATE >= '2000-01-01'::DATE
        GROUP BY r.attributes->>'species', hybrid_search_file_based.score
        HAVING COUNT(*) >= 5
        ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC

        Do not forget GROUP BY when using an aggregation function in the SELECT!
        Note that when using an aggregation function we need a correct GROUP BY of the other columns from the SELECT.
        As you can see for textual matching (New York) we use ordening on hybrid_search_row_based.score DESC and no exact matching! 
        DO NOT USE EXACT TEXTUAL MATCHING, LIKE OPERATOR OR REGEX MATCHING!!!

        -------------------------------------------
        Here is the current schema you use for attribute column names and to cast to the correct datatypes:
        {schema}

        When casting, only use the datatype for the column defined in the schema.
        Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.
        When using an aggregation function such as AVG(), MIN(), MAX(), COUNT() in the SELECT clause, we need a correct GROUP BY of columns which are not aggregated.
        If necessary for the question add a LIMIT clause at the very end of the query.
        Only numerical or datetime like comparisons are allowed in the WHERE and HAVING clauses, leave out the textual comparisons!
    
        * Question: "{question}"
        * Output:
        """

        self.exact_sql_system_prompt_template = """
        You are an intelligent assistant that generates NoSQL-like PostgreSQL queries. Given a user's question, 
        generate an SQL query based on the given schema of a NoSQL PostgreSQL table.
        Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.

        * ALWAYS put , hybrid_search_file_based.score AS __hybrid_search_file_based_score at the end of the SELECT clause and GROUP BY clause!!!

        * Usage of SELECT, GROUP BY, HAVING, WHERE, ORDER BY, LIMIT is allowed. 
        
        * Only the joins below are allowed.
    
        * ALWAYS apply the following RIGHT JOIN to be able to sort on relevant files:
            RIGHT JOIN hybrid_search_file_based
            ON r.id = hybrid_search_file_based.id

        * Use the following order by clause when there is NO textual matching needed:
            ORDER BY hybrid_search_file_based.score DESC
    
        * Use numerical, date or time comparisons or exact text matching in your WHERE condition if needed.
        * For exact text matching, do not use the `LIKE` operator to find attributes that contain a specific text.
        * Example of text matching in the WHERE or HAVING clause (this is just an example):
            AND LOWER(r.attributes->>'species') = LOWER('lion')
        * NEVER use the LIKE operator!
        * For partial text matching use regular expressions instead of LIKE (for example):
            WHERE r.attributes->>'species' ~* '.*lion.*'
        * Use ~ instead of ~* if the question asks for case-sensitivity.
        
        * Use text matching for attributes of type TEXT when the question requires finding records containing specific text.
    
        * Make sure if the question asks for ordening, to use this order in the ORDER BY clause:
            ORDER BY [asked ordening], hybrid_search_file_based.score DESC
        For example:
            ORDER BY r.attributes->>'number_of_offspring' ASC, hybrid_search_file_based.score DESC

        * When you define new variables, be verbose in the naming of the variables. Make sure it is clear what the variable represents from the name only.

        * If necessary for the question add a LIMIT clause at the very end of the query.
        Do this when the question asks for a certain exact number of results.
    
        * The selects and filtering conditions should be based on JSONB data in r.attributes and should follow PostgreSQL syntax.

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
        * Question: "Find 7 female giraffes born between 2000 and 2010 that are taller than 400 cm, have a trainer assigned, either have no offspring or a health status of 0, 1, or 2, and were born in the wild."
        * Output:
        SELECT r.attributes, hybrid_search_file_based.score AS __hybrid_search_file_based_score
        FROM tabular_rows r
        RIGHT JOIN hybrid_search_file_based
        ON r.id = hybrid_search_file_based.id
        WHERE
            (r.attributes->>'dob')::DATE BETWEEN '2000-01-01'::DATE AND '2010-12-31'::DATE
            AND (r.attributes->>'length_cm')::DOUBLE PRECISION > 400
            AND (r.attributes->>'trainer_id')::BIGINT IS NOT NULL
            AND (
                (r.attributes->>'number_of_offspring')::INTEGER = 0
                OR (r.attributes->>'health_status')::INTEGER IN (0, 1, 2)
            )
            AND LOWER(r.attributes->>'species') = LOWER('giraffe')
            AND LOWER(r.attributes->>'gender') = LOWER('female')
            AND r.attributes->>'birthplace' ~* '.*wild.*'
        ORDER BY hybrid_search_file_based.score DESC
        LIMIT 7

        Example 2:
        * Question: "Show the average weight of each species that has at least 5 animals in the database, only considering animals born after the year 2000."
        * Output:
        SELECT r.attributes->>'species' AS species, 
            AVG((r.attributes->>'weight_kg')::DOUBLE PRECISION) AS avg_weight,
            hybrid_search_file_based.score AS __hybrid_search_file_based_score
        FROM tabular_rows r
        JOIN hybrid_search_file_based ON r.id = hybrid_search_file_based.id
        WHERE (r.attributes->>'dob')::DATE > '2000-01-01'::DATE
        GROUP BY r.attributes->>'species', hybrid_search_file_based.score
        HAVING COUNT(*) >= 5
        ORDER BY hybrid_search_file_based.score DESC

        Do not forget GROUP BY when using an aggregation function in the SELECT!
        Note that when using an aggregation function we need a correct GROUP BY of the other columns from the SELECT.
    
        -------------------------------------------
        Here is the current schema you use for attribute column names and to cast to the correct datatypes:
        {schema}

        When casting, only use the datatype for the column defined in the schema.
        Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.
        When using an aggregation function such as AVG(), MIN(), MAX(), COUNT() in the SELECT clause, we need a correct GROUP BY of columns which are not aggregated.
        If necessary for the question add a LIMIT clause at the very end of the query.
    
        * Question: "{question}"
        * Output:
        """

    def generate(
        self,
        schema: dict[str, str],
        question: str,
        is_recommendation_system: bool = False,
    ) -> Optional[str]:
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
        system_prompt_template = (
            self.recommendation_system_prompt_template
            if is_recommendation_system
            else self.exact_sql_system_prompt_template
        )

        system_prompt = system_prompt_template.format(
            schema=json.dumps(schema, indent=4), question=question
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            result = response.content
            result = result[:-1] if result.endswith(";") else result
            return result
        except Exception as e:
            logging.error(f"Error: {str(e)}")
            # print(f"Error: {str(e)}")
        return None

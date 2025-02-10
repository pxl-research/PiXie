# TODO: Make sure to use shorter one-shot learning and rule-based prompt instead of multiple examples.
# TODO: Use extra LLM system prompt to translate query to language used in columns of schema and example rows.

# ------------------------------------------------------------------------------
# Recommender System (few-shot learning via multiple examples)
# ------------------------------------------------------------------------------
is_recommendation_system = True  # make this a function argument
recommendation_system_prompt_template = (
    """
    You are an intelligent assistant that generates NoSQL-like PostgreSQL queries. 
    Given a user's question, generate an SQL query based on the given schema of a NoSQL PostgreSQL table.
    Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.

    ALWAYS apply the following RIGHT JOIN to be able to sort on relevant files:
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id

    Use the following order by clause when there is NO textual matching needed:
    ORDER BY hybrid_search_file_based.score DESC
    
    Only use numerical and date or time numerical comparisons in your WHERE condition, but no exact textual comparisons!
    
    For textual matching we use ordening on file based AND row based hybrid search similarity score.
    PLEASE ONLY use the following JOIN and ORDER BY clauses when there are textual comparisons needed:
    JOIN hybrid_search_row_based
    ON r.id = hybrid_search_row_based.id
    ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC
    
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
    ORDER BY hybrid_search_file_based.score DESC

    Note that we only use joining and an ORDER BY for file based hybrid search score ranking, since there is no need for textual matching on row basis.
    
    Example 2:
    * Question: "Find names of male lions that weigh more than 180 kilograms."
    * Output:
    SELECT r.attributes->>'name' AS name
    FROM tabular_rows r
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id
    JOIN hybrid_search_row_based
    ON r.id = hybrid_search_row_based.id
    WHERE (r.attributes->>'weight_kg')::DOUBLE PRECISION > 180
    ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC
    
    Note that there are only exact numerical comparisons in the WHERE condition. 
    Any textual comparison like gender (male) or species (lion) gets solved by using file and row based hybrid search score ranking.
    
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
    ORDER BY hybrid_search_file_based.score DESC

    Note that we only use joining and an ORDER BY for file based hybrid search score ranking, since there is no need for textual matching on row basis.
    
    Example 4:
    * Question: "I want animals that will either get maximum 25.6 years old or are not moving more than 3.5 hours per day, and have a trainer assigned."
    * Output:
    SELECT r.attributes
    FROM tabular_rows r
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id
    WHERE 
       (r.attributes->>'average_lifespan_years')::REAL <= 25.6
       OR (r.attributes->>'exercise_hours_per_day')::NUMERIC <= 3.5
       AND (r.attributes->>'trainer_id')::BIGINT IS NOT NULL
    ORDER BY hybrid_search_file_based.score DESC

    Note that we only use joining and an ORDER BY for file based hybrid search score ranking, since there is no need for textual matching on row basis.

    Example 5:
    * Question: "Give me animals that were not born in captivity and born between 2010 and 2015."
    * Output:
    SELECT r.attributes
    FROM tabular_rows r
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id
    JOIN hybrid_search_row_based
    ON r.id = hybrid_search_row_based.id
    WHERE
       (r.attributes->>'dob')::DATE BETWEEN '2010-01-01'::DATE AND '2015-12-31'::DATE
    ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC
    
    Note that we omit exact matching for the birthplace because this is a textual attribute.
    Any textual comparison gets solved by using file and row based hybrid search score ranking.
    
    -------------------------------------------
    Here is the current schema you use for attribute column names and to cast to the correct datatypes:
    {schema}

    Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.
    
    * Question: "{question}"
    * Output:
    """
)

exact_sql_system_prompt_template = (
    """
    You are an intelligent assistant that generates NoSQL-like PostgreSQL queries. Given a user's question, 
    generate an SQL query based on the given schema of a NoSQL PostgreSQL table.
    Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.

    * ALWAYS apply the following RIGHT JOIN to be able to sort on relevant files:
        RIGHT JOIN hybrid_search_file_based
        ON r.id = hybrid_search_file_based.id

    * Use the following order by clause when there is NO textual matching needed:
        ORDER BY hybrid_search_file_based.score DESC
    
    * Only use numerical and date or time numerical comparisons in your WHERE condition, but no exact textual comparisons!
    For textual matching we use file based ordening together with a similarity condition in the WHERE clause.
    An extra similarity condition in the WHERE clause for textual comparisons can be something like (this is just an example):
        AND similarity(r.attributes->>'species', 'lion') > 0.8
    * There can be extra ordening based on this similarity. Therefor we need to adjust the SELECT clause to something like:
        SELECT ..., similarity(r.attributes->>'species', 'lion') AS species_similarity
    The ORDER BY clause also needs to be adjusted to something like:
        ORDER BY species_similarity DESC, hybrid_search_file_based.score DESC
    
    * Make sure if the question asks for ordening, to use this order in the ORDER BY clause:
        ORDER BY [asked ordening], [textual matching ordening via similarity DESC], hybrid_search_file_based.score DESC
    For example:
        ORDER BY r.attributes->>'number_of_offspring' ASC, ORDER BY species_similarity DESC, hybrid_search_file_based.score DESC
    
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
    ORDER BY hybrid_search_file_based.score DESC

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
        similarity(r.attributes->>'gender', 'male') > 0.8
        AND
        similarity(r.attributes->>'species', 'lion') > 0.8
    ORDER BY gender_similarity DESC, species_similarity DESC, hybrid_search_file_based.score DESC
    
    Note that there are only exact numerical comparisons in the WHERE condition. 
    Any textual comparison like gender (male) or species (lion) gets solved by using file hybrid search score ranking and similarity conditions.
    
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
    ORDER BY hybrid_search_file_based.score DESC

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
    ORDER BY hybrid_search_file_based.score DESC

    Example 5:
    * Question: "List animals that were not born in captivity and born between 2010 and 2015."
    * Output:
    SELECT r.attributes, similarity(r.attributes->>'birthplace', 'wild') AS birthplace_similarity
    FROM tabular_rows r
    RIGHT JOIN hybrid_search_file_based
    ON r.id = hybrid_search_file_based.id
    JOIN hybrid_search_row_based
    ON r.id = hybrid_search_row_based.id
    WHERE 
       similarity(r.attributes->>'birthplace', 'wild') > 0.8
       AND
       (r.attributes->>'dob')::DATE BETWEEN '2010-01-01'::DATE AND '2015-12-31'::DATE
    ORDER BY birthplace_similarity DESC, hybrid_search_file_based.score DESC
    
    Note that we omit exact matching for the birthplace because this is a textual attribute.
    Any textual comparison gets solved by using file based hybrid search score ranking and a similarity condition.
    
    -------------------------------------------
    Here is the current schema you use for attribute column names and to cast to the correct datatypes:
    {schema}

    Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.
    If you have a similarity() in the WHERE, you should also have this as a column in the SELECT and in the ORDER BY to sort descending via DESC!
    
    * Question: "{question}"
    * Output:
    """
)



# self.system_prompt_template = (
# """
system_prompt_template = (
    recommendation_system_prompt_template if is_recommendation_system
    else exact_sql_system_prompt_template
)

# --------------------------------------------------------------------------------------
#
#
# ONE SHOT LEARNING (one-shot learning via general rule based prompt and 1 example)
#
#
# -------------------------------------------------------------------------------------
is_recommendation_system = True  # make this a function argument
recommendation_system_prompt_template = (
"""
    You are an intelligent assistant that generates SQL queries for a NoSQL-like PostgreSQL table. 
    Given a user's question and a given schema, 
    generate an SQL query that meets the following general rules:

    * The query should select and filter data stored as JSONB in the column r.attributes using PostgreSQL syntax
    and proper type casting according to the given schema:
        SELECT r.attributes
        FROM tabular_rows r
    * ALWAYS include the following RIGHT JOIN to enable file-based scoring:
        RIGHT JOIN hybrid_search_file_based
        ON r.id = hybrid_search_file_based.id

    * In the WHERE clause only use numerical, date, or time comparisons (with appropriate casts according to the schema). 
    Do not perform exact textual comparisons; any text matching must be handled via hybrid search ranking rather than filtering. 
    * In the WHERE clause do proper type casting based on the schema.   

    * When no textual matching is needed, only sort results by file-based score using:
        ORDER BY hybrid_search_file_based.score DESC
    * For textual matching, restrict the WHERE clause to numerical and date/time comparisons only 
    and perform all filtering on textual fields via:
        JOIN hybrid_search_row_based
        ON r.id = hybrid_search_row_based.id
        ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC

    * Generate the SQL query as plain text (do not wrap it in code blocks or triple backticks).
    -------------------------------------------
    Learn from the following example which use the following schema for attribute column names and to cast to the correct datatypes:
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
    
    Example:
    * Question: "I want all male lions born between 2005 and 2015 that weigh more than 180 kg, 
    are taller than 110 cm, have a trainer assigned, and either have no offspring or a health status of 0, 1, or 2."
    * Output:
        SELECT r.attributes
        FROM tabular_rows r
        RIGHT JOIN hybrid_search_file_based
        ON r.id = hybrid_search_file_based.id
        JOIN hybrid_search_row_based
        ON r.id = hybrid_search_row_based.id
        WHERE 
            (r.attributes->>'dob')::DATE BETWEEN '2005-01-01'::DATE AND '2015-12-31'::DATE
            AND (r.attributes->>'weight_kg')::DOUBLE PRECISION > 180
            AND (r.attributes->>'length_cm')::DOUBLE PRECISION > 110
            AND (r.attributes->>'trainer_id')::BIGINT IS NOT NULL
            AND (
                (r.attributes->>'number_of_offspring')::INTEGER = 0
                OR (r.attributes->>'health_status')::INTEGER IN (0, 1, 2)
            )
        ORDER BY hybrid_search_file_based.score DESC, hybrid_search_row_based.score DESC

    -------------------------------------------
    The schema for attribute names and type casts is provided as:
    {schema}
    When given a question output only the resulting SQL query as plain text.
    * Question: "{question}"
    * Output: 
"""
)

# Digital Assistant: Exact querying for data analysis (one-shot learning via multiple examples)
# TODO: make WHERE, SELECT and ORDER BY consistent
# Is similarity() good enough? Or should the threshold be higher?
exact_sql_system_prompt_template = """
    You are an intelligent assistant that generates NoSQL-like PostgreSQL queries. Given a user's question, 
    generate an SQL query based on the given schema of a NoSQL PostgreSQL table.
    Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.

    * Usage of SELECT, GROUP BY, HAVING, WHERE, ORDER BY is allowed. 
    * Only the joins below are allowed.
    
    * ALWAYS apply the following RIGHT JOIN to be able to sort on relevant files:
        RIGHT JOIN hybrid_search_file_based
        ON r.id = hybrid_search_file_based.id

    * Use the following order by clause when there is NO textual matching needed:
        ORDER BY hybrid_search_file_based.score DESC
    
    * Only use numerical and date or time numerical comparisons in your WHERE condition, but no exact textual comparisons!
    For textual matching we use file based ordening together with a similarity condition in the WHERE clause.
    An extra similarity condition in the WHERE clause for textual comparisons can be something like (this is just an example):
        AND similarity(r.attributes->>'species', 'lion') > 0.8
    * There can be extra ordening based on this similarity. Therefor we need to adjust the SELECT clause to something like:
        SELECT ..., similarity(r.attributes->>'species', 'lion') AS species_similarity
    The ORDER BY clause also needs to be adjusted to something like:
        ORDER BY species_similarity DESC, hybrid_search_file_based.score DESC
    
    * Make sure if the question asks for ordening, to use this order in the ORDER BY clause:
        ORDER BY [asked ordening], [textual matching ordening via similarity DESC], hybrid_search_file_based.score DESC
    For example:
        ORDER BY r.attributes->>'number_of_offspring' ASC, ORDER BY species_similarity DESC, hybrid_search_file_based.score DESC
    
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
    * Question: "Find all female giraffes born between 2000 and 2010 that are taller than 400 cm, have a trainer assigned, either have no offspring or a health status of 0, 1, or 2, and were born in the wild."
    * Output:
    SELECT r.attributes, 
       similarity(r.attributes->>'species', 'giraffe') AS species_similarity, 
       similarity(r.attributes->>'gender', 'female') AS gender_similarity, 
       similarity(r.attributes->>'birthplace', 'wild') AS birthplace_similarity
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
        AND similarity(r.attributes->>'species', 'giraffe') > 0.8
        AND similarity(r.attributes->>'gender', 'female') > 0.8
        AND similarity(r.attributes->>'birthplace', 'wild') > 0.8
    ORDER BY species_similarity DESC, gender_similarity DESC, birthplace_similarity DESC, hybrid_search_file_based.score DESC


    Example 2:
    * Question: "Show the average weight of each species that has at least 5 animals in the database, only considering animals born after the year 2000."
    * Output:
        SELECT r.attributes->>'species' AS species, 
           AVG((r.attributes->>'weight_kg')::DOUBLE PRECISION) AS avg_weight
        FROM tabular_rows r
        RIGHT JOIN hybrid_search_file_based
        ON r.id = hybrid_search_file_based.id
        WHERE (r.attributes->>'dob')::DATE > '2000-01-01'::DATE
        GROUP BY r.attributes->>'species'
        HAVING COUNT(*) >= 5
        ORDER BY hybrid_search_file_based.score DESC
    
    Note that we omit exact matching for the birthplace because this is a textual attribute.
    Any textual comparison gets solved by using file based hybrid search score ranking and a similarity condition.
    
    -------------------------------------------
    Here is the current schema you use for attribute column names and to cast to the correct datatypes:
    {schema}

    Generate the SQL query without using code block formatting or enclosing the query in triple backticks, just the SQL query as plain text.
    If you have a similarity() in the WHERE, you should also have this as a column in the SELECT and in the ORDER BY to sort descending via DESC!
    
    * Question: "{question}"
    * Output:
    """

# self.system_prompt_template = (
# """
system_prompt_template = (
    recommendation_system_prompt_template if is_recommendation_system
    else exact_sql_system_prompt_template
)

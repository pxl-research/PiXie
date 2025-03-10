# --------------------
# TabularPGVectorStore
# --------------------
import os
import re
import logging
from typing import Optional
from decimal import Decimal
import json
import pandas as pd
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import execute_values, RealDictCursor
from langdetect import detect as langdetect_detect


from services.abstractclasses.embedding_model import EmbeddingModel

# from services.llms.tabular_where_filter_generator_llm import TabularWhereFilterGeneratorLLM
from services.llms.tabular_sql_query_generator_llm import TabularSQLQueryGeneratorLLM
from services.llms.question_queryable_llm import QuestionQueryableLLM
from services.llms.sql_query_corrector_llm import SQLQueryCorrectorLLM
from services.llms.recommendation_sql_post_processor_llm import (
    RecommendationSQLPostProcessorLLM,
)


def detect_language(text: str) -> str:
    """
    Detect the language of a given text and map it to one of the following:
    "english", "dutch", "french", "german". Defaults to "english".

    Parameters:
        text (str): The input text string.

    Returns:
        str: One of "english", "dutch", "french", "german".
    """
    # Mapping of langdetect codes to target languages
    language_mapping = {"en": "english", "nl": "dutch", "fr": "french", "de": "german"}
    try:
        detected_lang = langdetect_detect(text)
    except Exception:
        return "english"

    return language_mapping.get(detected_lang, "english")


def dict_pandas_to_postgres_dtype() -> dict[str, str]:
    """
    Maps Pandas datatypes to Postgres datatypes.

    Returns:
        dict[str, str]: Dictionary where the key is the Pandas datatype
            and the value is the Postgres datatype.
    """

    return {
        "int8": "SMALLINT",
        "int16": "SMALLINT",
        "int32": "INTEGER",
        "int64": "BIGINT",
        "UInt8": "SMALLINT",
        "UInt16": "INTEGER",
        "UInt32": "BIGINT",
        "UInt64": "NUMERIC",
        "float16": "REAL",
        "float32": "REAL",
        "float64": "DOUBLE PRECISION",
        "float": "DOUBLE PRECISION",
        "decimal": "NUMERIC",
        # Complex numbers are not directly supported in Postgres
        "complex64": "TEXT",
        "complex128": "TEXT",
        "bool": "BOOLEAN",
        "object": "TEXT",
        "category": "TEXT",
        "string": "TEXT",
        "Null": "TEXT",
        "Empty": "TEXT",
        "Interval": "TEXT",
        "Mixed": "TEXT",
        "json": "JSONB",
        "dict": "JSONB",
        "list": "JSONB",
        "tuple": "JSONB",
        "time": "TIME",
        "date": "DATE",
        "datetime64[D]": "DATE",
        "datetime64[M]": "DATE",
        "datetime64[Y]": "DATE",
        "datetime64": "TIMESTAMP",
        "datetime64[ns]": "TIMESTAMP",
        "datetime64[ns, tz]": "TIMESTAMPTZ",
        "timedelta": "INTERVAL",
        "timedelta64[ns]": "INTERVAL",
        "Period[D]": "DATE",
        "Period[M]": "DATE",
        "Period[Y]": "DATE",
        "Period[H]": "TIMESTAMP",
        "Period[min]": "TIMESTAMP",
        "Period[S]": "TIMESTAMP",
        "bytes": "BYTEA",
        "bytearray": "BYTEA",
    }


class TabularPGVectorStore:
    """
    Postgres pgvector implementation of a TabularVectorStore working on tabular data.
    """

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        tabular_sql_query_generator_llm: TabularSQLQueryGeneratorLLM,
        question_queryable_llm: QuestionQueryableLLM,
        sql_query_corrector_llm: SQLQueryCorrectorLLM,
        recommendation_sql_post_processor_llm: RecommendationSQLPostProcessorLLM,
        # tabular_where_filter_generator_llm: TabularWhereFilterGeneratorLLM
    ):
        self.embedding_model = embedding_model
        self.tabular_sql_query_generator_llm = tabular_sql_query_generator_llm
        self.question_queryable_llm = question_queryable_llm
        self.sql_query_corrector_llm = sql_query_corrector_llm
        self.recommendation_sql_post_processor_llm = (
            recommendation_sql_post_processor_llm
        )
        # self.tabular_where_filter_generator_llm = tabular_where_filter_generator_llm

        current_collections = self.list_collections()
        if not current_collections:
            default_collection_name = "pixie"
            self._create_collection(default_collection_name)

    def _get_db_connection(self) -> psycopg2.extensions.connection:
        """
        Establish and return a connection to the PostgreSQL database.

        The connection parameters are retrieved from environment variables.

        Returns:
            psycopg2.extensions.connection: A connection object to the PostgreSQL database.
        """
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host="db",  # TODO: change to "db" or "tabular_vectorstore" when integrating into Pixie
            port="5432",
        )
        with conn.cursor() as c:
            try:
                register_vector(c)  # should be done each time we connect
            except Exception as e:
                logging.error(f"Error: {str(e)}")

        return conn

    def infer_postgres_schema(self, df: pd.DataFrame) -> dict[str, str]:
        """
        Infers the datatypes for a Pandas DataFrame and map Pandas
        datatypes to Postgres datatypes.
        When Pandas cannot infer the datatype it defaults to 'object'.
        The 'object' datatype will get mapped to TEXT in Postgres by default.
        This is needed for correct WHERE-clause generation.

        Args:
            df (pd.DataFrame): DataFrame for which we want to determine the datatypes of the columns.
        Returns:
            dict[str, str]: Dictionary mapping columns as the key to Postgres datatypes as the value.
        """
        schema = {}
        # print("Schema inference is starting...")
        # print(f"Row count: {df.shape[0]}")
        datatype_mapper = dict_pandas_to_postgres_dtype()

        for column in df.columns:
            dtype = str(df[column].dtype)
            pg_type = "TEXT"  # Default Postgres datatype is TEXT (fallback)

            # Custom inference if object
            if dtype == "object":
                # Try to infer numeric type
                numeric_series = pd.to_numeric(df[column], errors="coerce")
                if not numeric_series.isnull().all():
                    # Successfully converted to numeric (at least partially)
                    # Further refine numeric type if needed (e.g., integer vs float)
                    if pd.api.types.is_integer_dtype(numeric_series.dropna()):
                        pg_type = "INTEGER"  # or BIGINT/SMALLINT if more or less precision required
                    elif pd.api.types.is_float_dtype(numeric_series.dropna()):
                        pg_type = (
                            "DOUBLE PRECISION"  # use REAL if single precision is enough
                        )
                    else:
                        # Fallback to NUMERIC if mixed numeric types or other issues
                        pg_type = "NUMERIC"
                    dtype = "numeric_inferred"  # Indicate inferred numeric

                else:
                    # Try to infer datetime type if numeric inference failed
                    datetime_series = pd.to_datetime(df[column], errors="coerce")
                    if not datetime_series.isnull().all():
                        pg_type = "TIMESTAMP"  # Assume timestamp for datetime (can refine to DATE if needed)
                        dtype = "datetime_inferred"  # Indicate inferred datetime
                    else:
                        pg_type = "TEXT"  # Still object and cannot be converted to number or date, remain TEXT
                        dtype = "object_text"
            else:
                # Use the standard mapping for non-object types
                pg_type = datatype_mapper.get(dtype, "TEXT")

            # print(f"Column '{column}': Pandas dtype '{dtype}', Postgres type '{pg_type}'")
            schema[column] = pg_type

        return schema

    def add_tabular_document(
        self,
        collection_name: str,
        file_name: str,
        file_hash: str,
        file_description: Optional[str],
        file_schema: dict[str, str],
        language: str,
        df: pd.DataFrame,
    ) -> None:
        """
        Adds a tabular document to the database,
        associates it with a collection, and processes its rows.

        Args:
            collection_name (str): The name of the collection to associate the document with.
            file_name (str): Unique name of the file.
            file_hash (str): A unique hash of the file for identification.
            file_description (Optional[str]): Summary of the file's content. Can be None.
            file_schema (dict[str, str]): Dictionary for the schema of the tabular data,
                where keys are column names and values are their data types.
            df (pd.DataFrame): A DataFrame containing the tabular data to be added.
        """

        conn = self._get_db_connection()
        embedding_model = self.embedding_model

        # Generate the embedding for the file description
        file_description_embedding = embedding_model.embed_query(
            text=file_description, normalize=False, to_list=True
        )

        file_schema_str = json.dumps(file_schema)
        with conn.cursor() as c:
            try:
                # Get collection ID
                c.execute(
                    f"""
                    SELECT id 
                    FROM tabular_collections 
                    WHERE name = %s
                    LIMIT 1
                    """,
                    (collection_name,),
                )
                collection_id = c.fetchone()[0]

                # Insert document data into tabular_documents
                c.execute(
                    f"""
                    INSERT INTO tabular_documents (
                        file_name, file_hash, last_updated, language,
                        file_description, file_description_embedding, file_schema
                    )
                    VALUES (%s, %s, NOW(), %s, %s, %s, %s::jsonb)
                    ON CONFLICT (file_name) DO UPDATE
                    SET 
                        file_hash = EXCLUDED.file_hash,
                        last_updated = EXCLUDED.last_updated,
                        language = EXCLUDED.language,
                        file_description = EXCLUDED.file_description,
                        file_description_embedding = EXCLUDED.file_description_embedding,
                        file_schema = EXCLUDED.file_schema
                    RETURNING id,
                        CASE 
                            WHEN xmax::text::int > 0 THEN TRUE -- indicates an update (conflict)
                            ELSE FALSE -- Indicates an insert (no conflict)
                        END AS is_updated
                    """,
                    (
                        file_name,
                        file_hash,
                        language,
                        file_description,
                        file_description_embedding,
                        file_schema_str,
                    ),
                )
                res = c.fetchone()
                file_id, is_updated = res[0], res[1]

                # print("collection_id:", collection_id)
                # print("file_id:", file_id)
                # print(str(is_updated))

                if is_updated:
                    # When it is updated, remove all tabular_rows for this file,
                    # and insert the fresh onces again later.
                    c.execute(
                        f"""
                        DELETE FROM tabular_rows
                        WHERE file_id = %s
                        """,
                        (file_id,),
                    )
                else:
                    # not updated, but a new document
                    # Associate the document with the collection
                    c.execute(
                        f"""
                        INSERT INTO tabular_documents_collections (
                        collection_id, document_id)
                        VALUES (%s, %s)
                        """,
                        (collection_id, file_id),
                    )

                # Generate embeddings and descriptions for each row in tabular_rows
                row_descriptions = df.apply(
                    lambda row: ", ".join([f"{col}: {row[col]}" for col in df.columns]),
                    axis=1,
                ).to_list()

                row_embedding_vectors = embedding_model.embed_documents(
                    texts=row_descriptions, normalize=False, to_list=True
                )

                # Prepare data for insertion into tabular_rows
                rows_to_insert = [
                    (file_id, row_emb, row.to_json())
                    for (_, row), row_emb in zip(df.iterrows(), row_embedding_vectors)
                ]

                # Insert row data into tabular_rows
                execute_values(
                    c,
                    f"""
                        INSERT INTO tabular_rows (file_id, row_embedding, attributes)
                        VALUES %s
                    """,
                    rows_to_insert,
                    template="(%s, %s, %s::jsonb)",
                )

                # Commit all changes if successful
                conn.commit()
            except psycopg2.DatabaseError as e:
                conn.rollback()
                logging.error("Error: ", e)
            finally:
                conn.close()

    def delete_tabular_document(self, collection_name: str, file_name: str) -> bool:
        """
        Deletes one or more tabular documents from the tabular pgvector vector store
        based on the collection and file name or file name pattern.

        Args:
            collection_name (str): The name of the collection the document(s) belong to.
            file_name (str): The name or pattern of the files to delete.

        Returns:
            bool: True if at least one document was deleted, False otherwise.
        """

        conn = self._get_db_connection()
        success = False

        with conn.cursor() as c:
            try:
                # Get the collection ID
                c.execute(
                    f"""
                    SELECT id 
                    FROM tabular_collections 
                    WHERE name = %s
                    LIMIT 1
                    """,
                    (collection_name,),
                )
                result = c.fetchone()
                if result is None:
                    logging.error(f"Collection '{collection_name}' not found.")
                    return False
                collection_id = result[0]

                # Get all matching document IDs
                # It could be that one document has multiple sheets
                # and such a document is stored as secure_file_name#sheet_name
                c.execute(
                    f"""
                    SELECT id
                    FROM tabular_documents
                    WHERE file_name = %s OR file_name LIKE %s
                    """,
                    (
                        file_name,
                        f"{file_name}%#",
                    ),  # Match file_name and any pattern starting with it
                )
                document_ids = [row[0] for row in c.fetchall()]

                if not document_ids:
                    logging.error(
                        f"No documents matching '{file_name}' found in the database."
                    )
                    return False

                # Delete associations between the collection and the documents
                c.execute(
                    f"""
                    DELETE FROM tabular_documents_collections
                    WHERE collection_id = %s AND document_id = ANY(%s)
                    """,
                    (collection_id, document_ids),
                )

                # Delete the documents themselves
                c.execute(
                    f"""
                    DELETE FROM tabular_documents
                    WHERE id = ANY(%s)
                    """,
                    (document_ids,),
                )

                # Commit the transaction
                conn.commit()
                logging.info(
                    f"Successfully deleted {len(document_ids)} document(s) matching '{file_name}' "
                    f"from collection '{collection_name}'."
                )
                success = True
            except Exception as e:
                conn.rollback()
                logging.error(
                    f"Failed to delete documents matching '{file_name}' from collection '{collection_name}': {str(e)}"
                )
                success = False
            finally:
                conn.close()

        return success

    def _list_schemas(
        self, collection_name: str, question_embedding: list[float], max_file_count: int
    ) -> list[tuple[dict[str, str], str]]:
        """
        List unique schemas filtered by collection_name and sorted
        by similarity to the question_embedding.

        Args:
            collection_name (str): The name of the collection to filter by.
            question_embedding (list[float]): The embedding vector for sorting.
            max_file_count (int): The maximum number of schemas to return.

        Returns:
            list[tuple[dict[str, str], str]]: A list of tuples of unique schemas as dictionaries and languages as a string.
        """
        conn = self._get_db_connection()

        list_unique_schemas: list[dict[str, str]] = []

        with conn.cursor() as c:
            try:
                unique_schemas_query = f"""
                    WITH ranked_documents AS (
                        SELECT d.file_schema, d.language,
                            d.file_description_embedding <=> %(question_embedding)s::vector AS similarity
                        FROM tabular_documents AS d
                        JOIN tabular_documents_collections AS dc
                        ON d.id = dc.document_id
                        JOIN tabular_collections AS c
                        ON dc.collection_id = c.id
                        WHERE c.name = %(collection_name)s
                    ),
                    distinct_documents AS (
                        SELECT DISTINCT ON (file_schema) file_schema, language, similarity
                        FROM ranked_documents
                        ORDER BY file_schema, similarity ASC
                    )
                    SELECT file_schema, language
                    FROM distinct_documents
                    ORDER BY similarity ASC
                    LIMIT %(max_file_count)s
                """
                c.execute(
                    unique_schemas_query,
                    {
                        "collection_name": collection_name,
                        "question_embedding": question_embedding,
                        "max_file_count": max_file_count,
                    },
                )
                list_unique_schemas = [(row[0], row[1]) for row in c.fetchall()]
                # print(list_unique_schemas)
            except psycopg2.DatabaseError as e:
                logging.error(f"Failed to retrieve unique table schemas: {str(e)}")
                print(f"Failed to retrieve unique table schemas: {str(e)}")

        return list_unique_schemas

    '''
    def retrieve_top_rows(
        self,
        collection_name: str,
        question: str,
        top_k: int = 10,
        k_rrf: int = 60,
        weight_row_vs_file_based: float = 0.8,
        max_file_count: int = 3,
    ) -> pd.DataFrame:
        """
        Retrieve the top rows relevant to a question from a specified collection.

        Args:
            collection_name (str): Name of the collection to search within.
            question (str): The query or question for which relevant rows are retrieved.
            top_k (int, optional): Number of top rows to return. Default is 10.
            k_rrf (int, optional): Reciprocal rank fusion parameter. Default is 60.
            weight_row_vs_file_based (float, optional): Weight to balance 
                row-level vs. file-level relevance scores. Default is 0.8.
            max_file_count (int, optional): Maximum number of files to consider 
                based on schema matching. Default is 3.

        Returns:
            pd.DataFrame: DataFrame containing the attributes of the top matching rows.
        """

        # TODO: sanitize disjunction_filter_condition to avoid SQL-injection!
        # This will be done later.

        question_embedding = self.embedding_model.embed_query(
            text=question, normalize=False, to_list=True
        )

        list_unique_schemas = self._list_schemas(
            collection_name=collection_name,
            question_embedding=question_embedding,
            max_file_count=max_file_count,
        )

        disjunction_filter_condition = "1=1"  # no filtering by default
        if len(list_unique_schemas) > 0:
            disjunction_filter_condition = " OR ".join(
                [
                    f"({self.tabular_where_filter_generator_llm.generate(schema=s, question=question)})"
                    for s in list_unique_schemas
                ]
            )

        conn = self._get_db_connection()
        with conn.cursor() as c:
            try:
                language = detect_language(text=question)
                
                file_based_vector_query = f"""
                SELECT
                    tabular_rows.id AS id,
                    RANK () OVER (
                        ORDER BY tabular_documents.file_description_embedding 
                            <=> %(question_embedding)s::vector ASC
                    ) as rank
                FROM tabular_documents
                JOIN tabular_rows
                ON tabular_documents.id = tabular_rows.file_id

                -- Collection filtering
                JOIN tabular_documents_collections
                ON tabular_documents.id = tabular_documents_collections.document_id
                JOIN tabular_collections
                ON tabular_documents_collections.collection_id = tabular_collections.id
                WHERE tabular_collections.name = %(collection_name)s
                
                ORDER BY tabular_documents.file_description_embedding 
                <=> %(question_embedding)s::vector ASC
                """

                file_based_keyword_query = f"""
                SELECT
                    tabular_rows.id AS id,
                    RANK() OVER (
                        ORDER BY ts_rank_cd(
                            to_tsvector('{language}', tabular_documents.file_description),
                            plainto_tsquery('{language}', %(question)s)
                        ) DESC
                    ) AS rank
                FROM tabular_documents
                JOIN tabular_rows
                ON tabular_documents.id = tabular_rows.file_id

                -- Collection filtering
                JOIN tabular_documents_collections
                ON tabular_documents.id = tabular_documents_collections.document_id
                JOIN tabular_collections
                ON tabular_documents_collections.collection_id = tabular_collections.id
                WHERE tabular_collections.name = %(collection_name)s
                
                AND to_tsvector('{language}', tabular_documents.file_description) @@ plainto_tsquery('{language}', %(question)s)
                ORDER BY ts_rank_cd(
                    to_tsvector('{language}', tabular_documents.file_description), 
                    plainto_tsquery('{language}', %(question)s)
                ) DESC
                """

                row_based_vector_query = f"""            
                SELECT
                    tabular_rows.id AS id,
                    RANK () OVER (
                        ORDER BY tabular_rows.row_embedding 
                            <=> %(question_embedding)s::vector ASC
                    ) as rank
                FROM tabular_documents
                JOIN tabular_rows
                ON tabular_documents.id = tabular_rows.file_id

                -- Collection filtering
                JOIN tabular_documents_collections
                ON tabular_documents.id = tabular_documents_collections.document_id
                JOIN tabular_collections
                ON tabular_documents_collections.collection_id = tabular_collections.id
                WHERE tabular_collections.name = %(collection_name)s
                
                ORDER BY tabular_rows.row_embedding 
                    <=> %(question_embedding)s::vector ASC
                """

                row_based_keyword_query = f"""            
                SELECT
                    tabular_rows.id AS id,
                    RANK () OVER (
                        ORDER BY ts_rank_cd(
                            to_tsvector('{language}', (tabular_rows.attributes)::text), 
                            plainto_tsquery('{language}', %(question)s)
                        ) DESC
                    ) AS rank
                FROM tabular_documents
                JOIN tabular_rows 
                ON tabular_documents.id = tabular_rows.file_id

                -- Collection filtering
                JOIN tabular_documents_collections
                ON tabular_documents.id = tabular_documents_collections.document_id
                JOIN tabular_collections
                ON tabular_documents_collections.collection_id = tabular_collections.id
                WHERE tabular_collections.name = %(collection_name)s
  
                AND to_tsvector('{language}', (tabular_rows.attributes)::text) 
                    @@ plainto_tsquery('{language}', %(question)s)            
                ORDER BY ts_rank_cd(
                    to_tsvector('{language}', (tabular_rows.attributes)::text), 
                    plainto_tsquery('{language}', %(question)s)
                ) DESC
                """

                hybrid_query = f"""
                WITH file_based_vector_search AS ({file_based_vector_query}),
                    file_based_keyword_search AS ({file_based_keyword_query}),
                    row_based_vector_search AS ({row_based_vector_query}),
                    row_based_keyword_search AS ({row_based_keyword_query})
                SELECT
                    COALESCE(
                        file_based_vector_search.id, 
                        file_based_keyword_search.id,
                        row_based_vector_search.id, 
                        row_based_keyword_search.id
                    ) AS id,
                
                    ({weight_row_vs_file_based} * 
                    (COALESCE(1.0 / (%(k)s + row_based_vector_search.rank), 0.0) + 
                    COALESCE(1.0 / (%(k)s + row_based_keyword_search.rank), 0.0)))
                    +
                    ({1.0 - weight_row_vs_file_based} * 
                    (COALESCE(1.0 / (%(k)s + file_based_vector_search.rank), 0.0) + 
                    COALESCE(1.0 / (%(k)s + file_based_keyword_search.rank), 0.0))) AS score
                FROM file_based_vector_search
                FULL OUTER JOIN file_based_keyword_search 
                ON file_based_vector_search.id = file_based_keyword_search.id
                FULL OUTER JOIN row_based_vector_search
                ON file_based_vector_search.id = row_based_vector_search.id
                FULL OUTER JOIN row_based_keyword_search
                ON file_based_keyword_search.id = row_based_keyword_search.id
                ORDER BY score DESC
                """

                composite_query = f"""
                WITH hybrid_search AS (
                    {hybrid_query}
                )
                SELECT r.attributes AS attributes -- DEBUG: , hybrid_search.score::real AS score
                FROM tabular_rows r
                RIGHT JOIN hybrid_search
                ON r.id = hybrid_search.id
                WHERE {disjunction_filter_condition}
                ORDER BY hybrid_search.score DESC
                LIMIT %(top_k)s
                """

                # Execute the query with the question embedding parameter
                c.execute(
                    composite_query,
                    {
                        "collection_name": collection_name,
                        "question": question,
                        "question_embedding": question_embedding,
                        "k": k_rrf,
                        "top_k": top_k,
                    },
                )

                results = c.fetchall()
                columns = ["attributes"]  # DEBUG: ["attributes", "score"]
                df = pd.DataFrame(results, columns=columns)

            except Exception as e:
                logging.error(
                    f"Failed to retrieve rows for collection '{collection_name}': {str(e)}"
                )
                print(f"Error: {str(e)}")
                return pd.DataFrame()

        return df
    '''

    def _query_ends_with_limit(self, query: str) -> bool:
        """
        Checks if a SQL query string ends with a LIMIT clause.

        Args:
            query (str): The SQL query string.

        Returns:
            bool: True if the query ends with a LIMIT clause (case-insensitive), False otherwise.
        """
        query = query.strip()  # Remove leading/trailing whitespace
        limit_pattern = re.compile(
            r"\bLIMIT\s+\d+\s*;\s*$", re.IGNORECASE
        )  # Added semi colon and whitespace to the end of the regex.
        limit_pattern_no_semicolon = re.compile(r"\bLIMIT\s+\d+\s*$", re.IGNORECASE)
        return bool(
            limit_pattern.search(query) or limit_pattern_no_semicolon.search(query)
        )

    def retrieve_top_rows(
        self,
        collection_name: str,
        question: str,
        top_k: int = 30,
        k_rrf: int = 60,
        max_file_count: int = 3,
        try_iteration_max_count=3,
        is_recommendation_system: bool = False,
    ) -> pd.DataFrame:
        """
        Retrieve the top rows relevant to a question from a specified collection.

        Args:
            collection_name (str): Name of the collection to search within.
            question (str): The query or question for which relevant rows are retrieved.
            top_k (int, optional): Number of top rows to return. Default is 10.
            k_rrf (int, optional): Reciprocal rank fusion parameter. Default is 60.
            weight_row_vs_file_based (float, optional): Weight to balance
                row-level vs. file-level relevance scores. Default is 0.8.
            max_file_count (int, optional): Maximum number of files to consider
                based on schema matching. Default is 3.

        Returns:
            pd.DataFrame: DataFrame containing the attributes of the top matching rows.
        """

        # TODO: sanitize generated query to avoid SQL-injection!
        # This will be done later.

        # Question embedding in original language of question can be used to list unique schemas
        # Reason: embedding model is multilingual
        question_embedding = self.embedding_model.embed_query(
            text=question, normalize=False, to_list=True
        )
        # list[tuple[dict[str, str], str]]
        list_unique_schemas = self._list_schemas(
            collection_name=collection_name,
            question_embedding=question_embedding,
            max_file_count=max_file_count,
        )

        if len(list_unique_schemas) <= 0:
            return pd.DataFrame()

        all_results = []
        for schema, language in list_unique_schemas:
            question_reformulated = self.question_queryable_llm.generate(
                schema=schema, question=question, language=language
            )
            generated_sql_query = self.tabular_sql_query_generator_llm.generate(
                schema=schema,
                question=question_reformulated,
                is_recommendation_system=is_recommendation_system,
            )
            if is_recommendation_system:
                generated_sql_query = (
                    self.recommendation_sql_post_processor_llm.generate(
                        query_to_correct=generated_sql_query
                    )
                )
            # generated_sql_query = self.tabular_sql_query_generator_llm.generate(schema=schema, question=question)

            # print("Generated SQL query:\n")
            # print("<sql>")
            # print(generated_sql_query)
            # print("</sql>")
            for try_iteration in range(try_iteration_max_count):
                conn = self._get_db_connection()
                with conn.cursor() as c:
                    try:
                        language = detect_language(text=question)

                        file_based_vector_query = f"""
                        SELECT
                            tabular_rows.id AS id,
                            RANK () OVER (
                                ORDER BY tabular_documents.file_description_embedding 
                                    <=> %(question_embedding)s::vector ASC
                            ) as rank
                        FROM tabular_documents
                        JOIN tabular_rows
                        ON tabular_documents.id = tabular_rows.file_id

                        -- Collection filtering
                        JOIN tabular_documents_collections
                        ON tabular_documents.id = tabular_documents_collections.document_id
                        JOIN tabular_collections
                        ON tabular_documents_collections.collection_id = tabular_collections.id
                        WHERE tabular_collections.name = %(collection_name)s
                
                        ORDER BY tabular_documents.file_description_embedding 
                        <=> %(question_embedding)s::vector ASC
                        """

                        file_based_keyword_query = f"""
                        SELECT
                            tabular_rows.id AS id,
                            RANK() OVER (
                                ORDER BY ts_rank_cd(
                                    to_tsvector('{language}', tabular_documents.file_description),
                                    plainto_tsquery('{language}', %(question)s)
                                ) DESC
                            ) AS rank
                        FROM tabular_documents
                        JOIN tabular_rows
                        ON tabular_documents.id = tabular_rows.file_id

                        -- Collection filtering
                        JOIN tabular_documents_collections
                        ON tabular_documents.id = tabular_documents_collections.document_id
                        JOIN tabular_collections
                        ON tabular_documents_collections.collection_id = tabular_collections.id
                        WHERE tabular_collections.name = %(collection_name)s
                
                        AND to_tsvector('{language}', tabular_documents.file_description) @@ plainto_tsquery('{language}', %(question)s)
                        ORDER BY ts_rank_cd(
                            to_tsvector('{language}', tabular_documents.file_description), 
                            plainto_tsquery('{language}', %(question)s)
                        ) DESC
                        """

                        row_based_vector_query = f"""            
                        SELECT
                            tabular_rows.id AS id,
                            RANK () OVER (
                                ORDER BY tabular_rows.row_embedding 
                                    <=> %(question_embedding)s::vector ASC
                            ) as rank
                        FROM tabular_documents
                        JOIN tabular_rows
                        ON tabular_documents.id = tabular_rows.file_id

                        -- Collection filtering
                        JOIN tabular_documents_collections
                        ON tabular_documents.id = tabular_documents_collections.document_id
                        JOIN tabular_collections
                        ON tabular_documents_collections.collection_id = tabular_collections.id
                        WHERE tabular_collections.name = %(collection_name)s
                
                        ORDER BY tabular_rows.row_embedding 
                            <=> %(question_embedding)s::vector ASC
                        """

                        row_based_keyword_query = f"""            
                        SELECT
                            tabular_rows.id AS id,
                            RANK () OVER (
                                ORDER BY ts_rank_cd(
                                    to_tsvector('{language}', (tabular_rows.attributes)::text), 
                                    plainto_tsquery('{language}', %(question)s)
                                ) DESC
                            ) AS rank
                        FROM tabular_documents
                        JOIN tabular_rows 
                        ON tabular_documents.id = tabular_rows.file_id

                        -- Collection filtering
                        JOIN tabular_documents_collections
                        ON tabular_documents.id = tabular_documents_collections.document_id
                        JOIN tabular_collections
                        ON tabular_documents_collections.collection_id = tabular_collections.id
                        WHERE tabular_collections.name = %(collection_name)s
  
                        AND to_tsvector('{language}', (tabular_rows.attributes)::text) 
                            @@ plainto_tsquery('{language}', %(question)s)            
                        ORDER BY ts_rank_cd(
                            to_tsvector('{language}', (tabular_rows.attributes)::text), 
                            plainto_tsquery('{language}', %(question)s)
                        ) DESC
                        """

                        hybrid_query_file_based = f"""
                        WITH file_based_vector_search AS ({file_based_vector_query}),
                            file_based_keyword_search AS ({file_based_keyword_query})
                        SELECT
                            COALESCE(
                                file_based_vector_search.id, 
                                file_based_keyword_search.id
                            ) AS id,
                            (COALESCE(1.0 / (%(k)s + file_based_vector_search.rank), 0.0) + 
                            COALESCE(1.0 / (%(k)s + file_based_keyword_search.rank), 0.0)) AS score
                        FROM file_based_vector_search
                        FULL OUTER JOIN file_based_keyword_search 
                        ON file_based_vector_search.id = file_based_keyword_search.id
                        ORDER BY score DESC
                        """

                        hybrid_query_row_based = f"""
                        WITH row_based_vector_search AS ({row_based_vector_query}),
                            row_based_keyword_search AS ({row_based_keyword_query})
                        SELECT
                            COALESCE(
                                row_based_vector_search.id, 
                                row_based_keyword_search.id
                            ) AS id,
                            (COALESCE(1.0 / (%(k)s + row_based_vector_search.rank), 0.0) + 
                            COALESCE(1.0 / (%(k)s + row_based_keyword_search.rank), 0.0)) AS score
                        FROM row_based_vector_search
                        FULL OUTER JOIN row_based_keyword_search
                        ON row_based_vector_search.id = row_based_keyword_search.id
                        ORDER BY score DESC
                    """

                        composite_query = f"""
                        WITH hybrid_search_file_based AS (
                            {hybrid_query_file_based}),
                            hybrid_search_row_based AS (
                            {hybrid_query_row_based})
                        {generated_sql_query}
                        {'' if self._query_ends_with_limit(generated_sql_query) else 'LIMIT %(top_k)s'}
                        """

                        # Execute the query with the question embedding parameter
                        c.execute(
                            composite_query,
                            {
                                "collection_name": collection_name,
                                "question": question,
                                "question_embedding": question_embedding,
                                "k": k_rrf,
                                "top_k": top_k,
                            },
                        )

                        results = c.fetchall()

                        # Extract column names dynamically from cursor description
                        extracted_column_names = [desc[0] for desc in c.description]
                        df = pd.DataFrame(results, columns=extracted_column_names)
                        df = df.head(top_k)
                        df = df.apply(
                            lambda col: col.map(
                                lambda x: float(x) if isinstance(x, Decimal) else x
                            )
                        )
                        df = df.drop(
                            [
                                "__hybrid_search_file_based_score",
                                "__hybrid_search_row_based_score",
                            ],
                            axis=1,
                            errors="ignore",
                        )
                        if not df.empty:
                            all_results.append(df)
                        # Do not try again, because query works
                        break

                    except Exception as e:
                        if try_iteration < try_iteration_max_count - 1:
                            generated_sql_query = self.sql_query_corrector_llm.generate(
                                schema=schema,
                                question=question_reformulated,
                                query_to_correct=generated_sql_query,
                                error_message=repr(e),
                            )
                            # try again with corrected query
                            continue
                        else:
                            logging.error(
                                f"Failed to retrieve rows for collection '{collection_name}': {str(e)}"
                            )
                            print(f"Error: {str(e)}")

        # Combine results from all schemas (e.g., by concatenating DataFrames)
        combined_df = (
            pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
        )
        return combined_df

    def list_documents(self, collection_name: str) -> list[str]:
        """
        Retrieves a list of document file names associated with a specific collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            list[str]: A list of document file names in the collection.
        """

        conn = self._get_db_connection()

        document_list: list[str] = []
        with conn.cursor() as c:
            try:
                # Single query to fetch document names for the specified collection
                c.execute(
                    f"""
                    SELECT td.file_name 
                    FROM tabular_documents td
                    JOIN tabular_documents_collections tdc
                    ON td.id = tdc.document_id
                    JOIN tabular_collections tc
                    ON tdc.collection_id = tc.id
                    WHERE tc.name = %s
                    """,
                    (collection_name,),
                )
                rows = c.fetchall()
                document_list = [row[0] for row in rows]
            except Exception as e:
                logging.error(
                    f"Failed to retrieve documents for collection '{collection_name}': {str(e)}"
                )
            finally:
                conn.close()

        return document_list

    def is_doc_up_to_date_in_list(self, file_hash: str, collection_name: str) -> bool:
        """
        Check if a tabular document with a given hash is up-to-date
        in the tabular document list for a specific collection.

        Args:
            file_hash (str): The hash of the tabular document to check.
            collection (str): The collection the tabular document belongs to.

        Returns:
            bool: True if the document is up-to-date, False otherwise.
        """
        conn = self._get_db_connection()

        is_up_to_date = False
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT td.file_hash 
                    FROM tabular_documents td
                    JOIN tabular_documents_collections tdc
                    ON td.id = tdc.document_id
                    JOIN tabular_collections tc
                    ON tdc.collection_id = tc.id
                    WHERE td.file_hash = %s AND tc.name = %s
                    """,
                    (file_hash, collection_name),
                )
                result = cursor.fetchone()
            is_up_to_date = result is not None
        except Exception as e:
            logging.error(f"Error: {str(e)}")
        finally:
            conn.close()

        return is_up_to_date

    # Not used, but commented if needed in the future
    '''
    def is_doc_in_list(self, file_name: str, collection: str) -> bool:
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT td.file_name
                    FROM tabular_documents td
                    JOIN tabular_documents_collections tdc
                    ON td.id = tdc.document_id
                    JOIN tabular_collections tc
                    ON tdc.collection_id = tc.id
                    WHERE td.file_name = %s AND tc.name = %s
                    """,
                    (file_name, collection),
                )
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logging.error(f"Error: {str(e)}")
        finally:
            conn.close()
    '''

    def list_collections(self) -> list[str]:
        """
        Lists all collections in the tabular pgvector vector store.

        Returns:
            list[str]: A list of collection names.
        """
        conn = self._get_db_connection()

        existing_collections = []
        try:
            with conn.cursor() as c:
                c.execute(f"SELECT name FROM tabular_collections;")
                rows: list[tuple[str]] = c.fetchall()
                existing_collections: list[str] = [row[0] for row in rows]
        except Exception as e:
            logging.error(f"Failed to list collections: {str(e)}")
        finally:
            conn.close()

        return existing_collections

    def add_collection(self, collection_name: str) -> None:
        """
        Adds a collection to the tabular pgvector vector store.

        Args:
            collection_name (str): The name of the collection to add.
        """
        if not self._check_collection(collection_name):
            self._create_collection(collection_name)
        else:
            logging.info(f"Collection {collection_name} already exists.")

    def remove_collection(self, collection_name: str) -> None:
        """
        Deletes a collection and its associated relations from the tabular pgvector vector store.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        conn = self._get_db_connection()
        with conn.cursor() as c:
            try:
                c.execute(
                    f"""
                    WITH deleted_collection AS (
                        DELETE FROM tabular_collections
                        WHERE name = %s
                        RETURNING id
                    )
                    DELETE FROM tabular_documents
                    WHERE id IN (
                        SELECT document_id
                        FROM tabular_documents_collections
                        WHERE collection_id IN (SELECT id FROM deleted_collection)
                    )
                    RETURNING id
                    """,
                    (collection_name,),
                )
                # NOTE: The ON DELETE CASCADE constraint in tabular_documents_collections
                # ensures related rows in that table are automatically removed!
                conn.commit()
            except Exception as e:
                conn.rollback()
                logging.error(
                    f"Failed to delete collection '{collection_name}': {str(e)}"
                )
            finally:
                conn.close()

    def _check_collection(self, collection_name: str) -> bool:
        """
        Checks if a collection exists in the tabular pgvector vector store.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            bool: True if the collection exists, False otherwise.
        """

        conn = self._get_db_connection()
        with conn.cursor() as c:
            try:
                c.execute(
                    f"""
                    SELECT EXISTS 
                    (
                        SELECT 1 
                        FROM tabular_collections 
                        WHERE name = %s
                    )
                    """,
                    (collection_name,),
                )
                result = c.fetchone()
                return result[0] if result else False
            except Exception as e:
                logging.error(f"Error checking collection '{collection_name}': {e}")
            finally:
                conn.close()

    def _create_collection(self, collection_name: str) -> None:
        """
        Creates a collection in the tabular pgvector vector store.

        Args:
            collection_name (str): The name of the collection to create.
        """

        conn = self._get_db_connection()
        try:
            with conn.cursor() as c:
                # The ON CONFLICT (name) DO NOTHING clause ensures
                # that duplicate collection names are ignored and
                # no error is raised if the collection already exists.
                # We already check if a collection exists in the add_collection method,
                # so there normally will not be a conflict.
                c.execute(
                    f"""
                    INSERT INTO tabular_collections (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING;
                    """,
                    (collection_name,),
                )
                conn.commit()
                logging.info(f"Collection '{collection_name}' created successfully.")
        except Exception as e:
            conn.rollback()
            logging.error(f"Failed to create collection {collection_name}: {str(e)}")
        finally:
            conn.close()

    def debug_print_all(self) -> None:
        """
        Prints the contents of all tables for debugging purposes.
        """

        conn = self._get_db_connection()

        tables = [
            "tabular_collections",
            "tabular_documents",
            "tabular_documents_collections",
            "tabular_rows",
        ]

        with conn.cursor(cursor_factory=RealDictCursor) as c:
            for table in tables:
                print(f"--- Contents of {table} ---")
                try:
                    query = f"SELECT * FROM {table};"
                    c.execute(query)
                    rows = c.fetchall()

                    if rows:
                        for row in rows:
                            print(dict(row))
                    else:
                        print("(No rows found)")
                except Exception as e:
                    print(f"Error reading table {table}: {e}")
                print()  # Add spacing between table outputs

    def get_summaries_by_collection(self, collection_name: str) -> list[str]:
        """
        Retrieves a list of file_descriptions associated with a specific collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            list[str]: A list of file descriptions in the collection.
        """
        conn = self._get_db_connection()

        summaries_list: list[str] = []
        with conn.cursor() as c:
            try:
                # Retrieve file descriptions for the specified collection
                c.execute(
                    """
                    SELECT td.file_description
                    FROM tabular_documents td
                    JOIN tabular_documents_collections tdc
                    ON td.id = tdc.document_id
                    JOIN tabular_collections tc
                    ON tdc.collection_id = tc.id
                    WHERE tc.name = %s
                    """,
                    (collection_name,),
                )
                rows = c.fetchall()
                summaries_list = [row[0] for row in rows]
            except Exception as e:
                logging.error(
                    f"Failed to retrieve file descriptions for collection '{collection_name}': {str(e)}"
                )
            finally:
                conn.close()

        return summaries_list

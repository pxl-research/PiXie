from typing import Any
from services.abstractclasses.llm import LLM
from services.llms.azure_openai_llm import AzureOpenAILLM

# Import shared services for document management
from services.init_services import get_services

# Shared services for document management
_services = get_services()


# Example of usage code:
"""
llm = AzureOpenAILLM(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    model_version=os.getenv("AZURE_OPENAI_MODEL_VERSION")
)

# Create conversation_loop per new session
conversation_loop = ConversationLoop(llm=llm)
wait_for_user_input = True

while True:
    if not wait_for_user_input:
        break

    user_input = input("You: ").strip()

    if user_input.lower() == "stop":
        wait_for_user_input, ai_response = conversation_loop.send("stop")
        print("AI: " + ai_response)
        break

    wait_for_user_input, ai_response = conversation_loop.send(user_input)
    print("AI: " + ai_response)
"""


class InitialSentenceAnalyserLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        Your goal is to analyze the initial sentence of a user and convert it to a more sql-like type of sentence.
        Follow these rules:
        1. Identify the main entity or topic of the sentence. You can choose from the following allowed entities:
        {allowed_entities}
        2. Identify the main attributes or specifications of the entity. Use the information about the possible attributes of the entity to help you. Values in euro are indications of price (prijs).
        {spec_list}
        3. Reformulate the sentence in the following format:
        Ik zoek een <main entity> met <attribute 1> is <value 1> en <attribute 2> is <value 2> en ... en <attribute n> is <value n>.

        Note: When the value type is continuous, q1 and q3 are given. Small is smaller than q1, large is larger than q3, and medium is between q1 and q3. 

        Example:
        User sentence:
        Ik wil een blauwe trui maat M van niet meer dan 50 euro.

        Reformulated sentence:
        Ik zoek een trui met kleur is blauw en maat is M en prijs is kleiner dan 50.

        Given initial sentence:
        {sentence}

        Result:
        """

    def generate(
        self, sentence: str, allowed_entities: list[str], spec_list: dict[str, Any]
    ) -> str | None:
        allowed_entities_str = "\n".join([f"- {entity}" for entity in allowed_entities])
        spec_list_str = ""
        for key, value in spec_list.items():
            if isinstance(value, dict):
                if "description" in value:
                    spec_list_str += f"- {key}: {value['description']}\n"
                    if "values" in value:
                        spec_list_str += f"  Possible values: {', '.join(map(str, value['values']))}\n"
                    elif (
                        value.get("type") == "continuous"
                        and "q1" in value
                        and "q3" in value
                    ):
                        spec_list_str += f"  Range: {value['q1']} - {value['q3']}\n"
                else:
                    spec_list_str += f"- {key}: {str(value)}\n"
            else:
                spec_list_str += f"- {key}: {value}\n"

        system_prompt = self.system_prompt_template.format(
            sentence=sentence,
            allowed_entities=allowed_entities_str,
            spec_list=spec_list_str,
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content.strip()
        except Exception as e:
            print(f"Error: {str(e)}")
        return None


# -----------------------------------------------------------------
# ConversationTopicsCheckerLLM
# -----------------------------------------------------------------
from typing import Optional
import json
import logging
from langchain.schema import SystemMessage


class ConversationTopicsCheckerLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        Your role is to act as an expert task decomposer. Your sole goal is to break down a user's overarching task or question into a list of distinct, focused subtasks or subquestions.

        Decomposition Rules:
        1.  Identify Primary Subjects: Each item in the output list should represent a request concerning a *single, main subject*.
        Do not split in distinct subtasks for subclauses, only for main clauses. 
        2.  Include All Attributes: Ensure that all specifications, attributes, or related details directly associated with a primary entity are kept together in the same subtask. Do NOT separate an entity's characteristics into a new subtask.
        3.  Maintain Original Language: The language used in the output subtasks must be identical to the original user task.

        Output Format:
        Your response MUST be ONLY a JSON list of strings, like this:
        ["Subtask 1.", "Subtask 2.", "Subtask 3."]
        Do not include any other text, explanations, or formatting outside this list.
    
        Example Task and Expected Output:

        Given user task:
        I need a blue sweater size M, a white smartphone with 128GB storage and a 48MP camera, and a wireless mouse.

        Expected Result:
        ["I need a blue sweater size M.", "I need a white smartphone with 128GB storage and a 48MP camera.", "I need a wireless mouse."]

        Given user task:
        I need a knife which I can use to cut meat.

        Expected Result:
        ["I need a knife which I can use to cut meat."]

        Given user task:
        {question}

        Result:
        """   

    def allowed_entities_str(self, entities: list[str]) -> str:
        return "\n".join([f"- {entity}" for entity in entities])

    def generate(self, question: str, entities: list[str]) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(
            question=question, allowed_entities=self.allowed_entities_str(entities)
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            logging.error(f"Error: {str(e)}")
        return None

    def check(self, question: str, entities: list[str]) -> bool:
        result = self.generate(question, entities)
        if result is None:
            return False
        elif not "true" in result.lower():
            return False
        return True

    def non_suitable_response(self, entities: list[str]) -> str:
        return f"Sorry, ik kan alleen helpen met vragen over deze onderwerpen:\n{self.allowed_entities_str(entities)}\n Gelieve enkel hiernaar te vragen."


# -----------------------------------------------------------------
# TaskDecomposerLLM
# -----------------------------------------------------------------
import ast
from typing import Optional
import json
import logging
from langchain.schema import SystemMessage


class TaskDecomposerLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        Your role is to act as an expert task decomposer. Your sole goal is to break down a user's overarching task or question into a list of distinct, focused subtasks or subquestions.

        Decomposition Rules:
        1.  Identify Primary Subjects: Each item in the output list should represent a request concerning a *single, main subject*.
        Do not split in distinct subtasks for subclauses, only for main clauses. 
        2.  Include All Attributes: Ensure that all specifications, attributes, or related details directly associated with a primary entity are kept together in the same subtask. Do NOT separate an entity's characteristics into a new subtask.
        3.  Maintain Original Language: The language used in the output subtasks must be identical to the original user task.

        Output Format:
        Your response MUST be ONLY a JSON list of strings, like this:
        ["Subtask 1.", "Subtask 2.", "Subtask 3."]
        Do not include any other text, explanations, or formatting outside this list.
    
        Example Task and Expected Output:

        Given user task:
        I need a blue sweater size M, a white smartphone with 128GB storage and a 48MP camera, and a wireless mouse.

        Expected Result:
        ["I need a blue sweater size M.", "I need a white smartphone with 128GB storage and a 48MP camera.", "I need a wireless mouse."]

        Given user task:
        I need a device which I can use to cut carrots.

        Expected Result:
        ["I need a device which I can use to cut carrots."]

        Given user task:
        I'm looking for a new smartphone for myself. I'd like an Android phone, if possible, not too expensive—definitely not above 500 euros. 
        And preferably one with a good camera.  I'm trying to find a good recipe for vegetarian lasagna. I prefer one that's relatively easy to make and uses fresh vegetables.
        
        Expected Result:
        ["I'm looking for a new smartphone for myself. I'd like an Android phone, if possible, not too expensive—definitely not above 500 euros. And preferably one with a good camera.", "I'm trying to find a good recipe for vegetarian lasagna. I prefer one that's relatively easy to make and uses fresh vegetables."]

        See how conservatively I keep things of the same subject together as one piece. Only if the main topic changes I make a split!

        Given user task:
        {question}

        Result:
        """

    def generate(self, question: str) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(question=question)

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            print(f"Error: {str(e)}")
        return None

    def decomposed_tasks(self, task: str) -> Optional[list[str]]:
        tasks_str = self.generate(question=task)
        if tasks_str:
            try:
                tasks_list = ast.literal_eval(tasks_str)
            except Exception:
                return None
            return tasks_list
        return None


# -----------------------------------------------------------------
# TopSpecsSelectorLLM
# -----------------------------------------------------------------
import ast
from typing import Optional
import json
import logging
from langchain.schema import SystemMessage


class TopSpecsSelectorLLM:
    def __init__(self, llm: LLM, recommendation_system: bool = True):
        self.llm = llm
        self.recommendation_system = recommendation_system
        self.system_prompt_template = """
        You are skilled at mapping user needs to the most relevant and prioritized information within a given context.

        Your task is:  
        For a given domain or category, and a list of attributes (features, fields, or parameters), rank the attributes from most likely to be asked or needed by a user to least likely. Omit the attributes that are already mentioned in the initial given task.

        Instructions:
        - Always **preserve the original attribute names** as-is, even if they are in another language.
        - Always **place general or vague fields** (e.g. 'barcode', 'name', 'description', 'available', 'category') at the **end** of the list.
        - Always **prioritize critical or high-impact fields first**, especially those typically involved in decision-making (e.g. "price" or the key functional traits).
        
        - Consider what a user would ask **first** when trying to achieve a goal or make a decision in this category.
        - The result must only be a reordered list of strings between square brackets `[]`, with no additional text.
        - Leave out attributes which are already mentioned in the initial given task.

        Example output format:
        ["price", "duration_days", "service_level"]

        Initial given task:
        {task}

        Given category or domain:
        {category}

        Given list of attributes with their descriptions:
        {specs}

        Reordered list of attributes based on user priority:
        """

    def generate(self, task: str, category: str, specs: list[str]) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(
            task=task, category=category, specs=specs
        )
        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            print(f"Error: {str(e)}")
        return None

    def top_specs(
        self, task: str, category: str, specs: list[str], top_count: int = 4
    ) -> list[str]:
        top_str = self.generate(task=task, category=category, specs=specs)
        if top_str:
            try:
                if self.recommendation_system:
                    top_specs_list = ast.literal_eval(top_str)[: top_count - 1]
                    # top_specs_list = ["description"] + top_specs_list
                else:
                    top_specs_list = ast.literal_eval(top_str)[:top_count]
            except Exception:
                return []
            return top_specs_list
        return []


# -----------------------------------------------------------------
# AdditionalQuestionLLM
# -----------------------------------------------------------------
class AdditionalQuestionLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        Your goal is to formulate a polite question for the given task about a given specification.
        Always mention the given task!
        The question should be in the same language as the given task.
        Give a few short examples of possible values tied to example use cases and always give as a last example that the user does not not know. 
        When the column description contains a list of possible values, always mention them in the question and do not add extra examples.
        Reformulate this question so it contains the same information and explicitly mentions the spec, no rewording.
        If the task already contains the information of the given specification, just say this and nothing else:
        None
        
        Given task:
        {task}

        Given specification:
        {spec}
        
        Question to ask to user (after reformulation):
        """

    def generate(self, task: str, spec: str) -> Optional[str]:
        def remove_digits(input_string: str) -> str:
            translator = str.maketrans("", "", "0123456789")
            return input_string.translate(translator)

        spec_processed = remove_digits(spec)
        print(spec_processed)

        system_prompt = self.system_prompt_template.format(
            task=task, spec=spec_processed
        )
        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            if response.content.lower().strip() == "none":
                return None
            return response.content
        except Exception as e:
            print(f"Error: {str(e)}")
        return None


# -----------------------------------------------------------------
# SimilarQuestionRemoverLLM
# -----------------------------------------------------------------
class SimilarQuestionRemoverLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        You are a helpful assistant that filters out similar or duplicate questions from a given list.

        Your task:
        - Analyze the list of user questions.
        - Remove any questions that are semantically very similar or identical.
        - Keep only distinct questions based on meaning, not just wording.
        - The output must be a Python-style list of strings, like: ["What is X?", "How does Y work?"]

        Requirements:
        - Preserve the original wording of the remaining distinct questions.
        - Do not return any explanation — only the final list.

        Given list of questions:
        {questions}

        Return the list of distinct questions:
        """

    def generate(self, questions: list[str]) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(questions=questions)
        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            print(f"Error: {str(e)}")
        return None

    def remove_similar_questions(self, questions: list[str]) -> list[str]:
        result_str = self.generate(questions=questions)
        if result_str:
            return ast.literal_eval(result_str)
        else:
            return []


# -----------------------------------------------------------------
# RAGQueryGeneratorLLM
# -----------------------------------------------------------------
from typing import Optional
from enum import Enum, auto
import json
import logging
from langchain.schema import SystemMessage


class RAGQueryGeneratorLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        Your goal is to formulate a single, accurate question for a RAG (Retrieval-Augmented Generation) system.

        You will be given:
        - A task (initial user request)
        - A list of (question, answer) tuples that may contain relevant details

        Your job:
        1. **Normalize the task** by identifying implicit attributes like brand, year, or type and making them explicit.
           - Always mention the column name and its value. For example:
           - "An Opel car" → "A car of brand Opel"
           - "A Samsung TV" → "A TV of brand Samsung"
           - "I want a Nike running shoe" → "I want a running shoe of brand Nike"
           - This applies to **any identifiable attribute** (brand, year, genre, length, etc.)

        2. Analyze the (question, answer) tuples:
           - Only include details that **add new, specific, relevant** information to the task.
           - Discard generic, irrelevant, or "not important" answers.
           - Add useful answers as additional constraints in the reformulated question.

        3. The reformulated question must:
           - Be as **concise** as possible not mentioning generic or not important or do not know answers.
           - Preserve all valuable search information.
           - Always use attribute names (e.g., brand, year, genre, length) with their corresponding values.
           - Be in the same language as the given task.

        Example:

        Task:
        I want a 1999's cd.

        Tuples:
        [("What genre is the cd?", "metal"),
         ("How long should the cd be?", "More than 1 hour"),
         ("From which country is the cd?", "Not important")]

        Reformulated question:
        I want a cd from the year 1999 in the genre metal with a length greater than 1 hour.

        Another example:

        Task:
        I want a Nike running shoe.

        Tuples:
        [("What size?", "43"),
         ("Color?", "Not important"),
         ("Do you prefer a specific material?", "Mesh")]

        Reformulated question:
        I want a running shoe of brand Nike in size 43 and made of material mesh.

        Now do the same with the following:

        Given task:
        {task}

        List of tuples (additional_question, answer):
        {couple_list}

        Reformulated question:
        """

    def generate(self, task: str, couple_list: list[tuple[str, str]]) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(
            task=task, couple_list=couple_list
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            result = response.content
            result = result.strip()
            return result
        except Exception as e:
            print(f"Error: {str(e)}")
        return None


# -----------------------------------------------------------------
# FinalAnswerLLM
# -----------------------------------------------------------------
class FinalAnswerLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        Your goal is to generate a final answer based on the given task and the data retrieved from the database.

        Given task:
        {task}

        Given data:
        {data}

        Final answer:
        """

    def generate(self, task: str, data: list[dict[str, dict[str, Any]]]) -> str:

        system_prompt = self.system_prompt_template.format(task=task, data=data)

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            print(f"Error: {str(e)}")
        return "no answer found"


# --------------------------------------------------
# Mock stuff
# TODO: delete and replace with actual functionality
# --------------------------------------------------
from typing import Optional
import json
import logging
from langchain.schema import SystemMessage
import pandas as pd
import json


class MockTableChooserLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        Your goal is to choose 1 item of the table list which matches to given task the most.

        Given task:
        {task}

        List of tables:
        {table_list}
        
        Choosen item:
        """

    def generate(self, task: str, table_list: list[str]) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(
            task=task, table_list=table_list
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            result = response.content
            if (result.startswith("'") and result.endswith("'")) or (
                result.startswith('"') and result.endswith('"')
            ):
                result = result[1:-1]
            return result
        except Exception as e:
            print(f"Error: {str(e)}")
        return None


# TODO: replace with actual MCP RAG tool functions
def mock_tabular_rag_choose_table(
    llm: LLM, task: str
) -> tuple[str, dict[str, dict[str, dict[str, Any]]]]:
    mapping = {
        "printers": {
            "barcode": {
                "type": "continuous",
                "description": "This is the unique identifier for the printer.",
                "q1": 4977766788861,
                "q3": 4977766824644,
            },
            "merk": {
                "type": "categorical",
                "description": "This is the brand of the printer",
                "values": ["HP", "Canon", "Epson", "Brother", "Kyocera"],
            },
            "categorie": {
                "type": "categorical",
                "description": "This is the internal path for the webshop.",
                "values": [
                    "All / Computer - Multimedia / Printers Scanners / Printers"
                ],
            },
            "beschikbaar": {
                "type": "boolean",
                "description": "This boolean indicates if the printer is available in the store.",
            },
            "beschrijving": {
                "type": "text",
                "description": "This is the long description used in promotional material.",
            },
            "printtechnologie": {
                "type": "categorical",
                "description": "This is the print technology used by the printer.",
                "values": ["inkjet", "laser", "LED", "thermal inkjet"],
            },
            "printen": {
                "type": "categorical",
                "description": "This string makes a distinction between colour and mono printers.",
                "values": ["Colour printing", "Mono printing"],
            },
            "maximale_resolutie_0_dpi": {
                "type": "categorical",
                "description": "This is the maximum resolution of the printer in dots per inch (DPI) for the first colour channel.",
                "values": [600, 1200, 2400, 4800, 5760],
            },
            "maximale_resolutie_1_dpi": {
                "type": "categorical",
                "description": "This is the maximum resolution of the printer in dots per inch (DPI) for the second colour channel.",
                "values": [600, 1200, 1440, 2400, 4800, 6000],
            },
            "scannen": {
                "type": "categorical",
                "description": "This string indicates if the printer can scan and if so in color or not.",
                "values": ["Colour scanning", "Mono scanning", "No"],
            },
            "optische_scanresolutie_0_dpi": {
                "type": "categorical",
                "description": "This is the maximum resolution of the printer in dots per inch (DPI) for the first colour channel when scanning.",
                "values": [600, 1200],
            },
            "optische_scanresolutie_1_dpi": {
                "type": "categorical",
                "description": "This is the maximum resolution of the printer in dots per inch (DPI) for the second colour channel when scanning.",
                "values": [600, 1200, 2400],
            },
            "wifi": {
                "type": "categorical",
                "description": "This string indicates whether the printer has Wi-Fi connectivity.",
                "values": ["Yes", "No"],
            },
            "ethernet_lan": {
                "type": "categorical",
                "description": "This string indicates whether the printer has Ethernet LAN connectivity.",
                "values": ["Yes", "No"],
            },
            "printsnelheid_zwart_standaardkwaliteit_a_ppm": {
                "type": "continuous",
                "description": "This is the print speed of the printer in pages per minute (PPM) for black and white standard quality.",
                "q1": 10.0,
                "q3": 20.0,
            },
        }
    }

    chosen_key = "printers"
    spec_list = {}
    if chosen_key:
        spec_list = mapping[chosen_key]

    return (chosen_key, spec_list)


def mock_tabular_rag_toolcall(query: str) -> pd.DataFrame:
    print(f"Searching database: executing query '{query}'...")
    data = {"product": ["X", "Y"], "price": [0.0, 0.0]}
    return pd.DataFrame(data)
    # return pd.DataFrame()


def mock_tabular_rag_allowed_entities() -> list[str]:
    allowed_entities = [
        "laptops",
        "PCs",
        "printers",
        "computer monitors",
        "inkt cartridges",
        "toners",
    ]
    return allowed_entities


def mock_final_answer(task: str, data: pd.DataFrame) -> str:
    context = data.to_dict(orient="records")
    context_str = json.dumps(context)
    return f"Data: {context_str}"


# Use the following stuff in the algorithm:
"""
Mock functions:
mock_tabular_rag_choose_table(llm: LLM, task: str) -> tuple[Optional[str], list[str]]:
mock_tabular_rag_toolcall(query: str) -> pd.DataFrame
mock_tabular_rag_allowed_entities() -> list[str]
"""

# -----------------------------------------------------------------
# ConversationStateLLM
# -----------------------------------------------------------------
from typing import Optional
from enum import Enum, auto
import json
import logging
from langchain.schema import SystemMessage

# TODO: Uncomment when doing integration into Pixie
"""
from services.abstractclasses.llm import LLM
"""


class ConversationState(Enum):
    WAITING_FOR_INITIAL_TASK = auto()
    INITIAL_TASK_GIVEN = auto()
    INITIAL_TASK_DECOMPOSED = auto()
    PROCESSING_DECOMPOSED_TASK = auto()
    ADDITIONAL_QUESTIONS_ASKED = auto()
    SEARCH_DATABASE_ENTITIES_RESULTS = auto()
    SEARCH_DATABASE_ENTITIES_NO_RESULTS = auto()
    INITIAL_TASK_DONE = auto()
    USER_STOP_CONVERSATION = auto()


# -----------------------------------------------------------------
# ConversationEndingDeciderLLM
# -----------------------------------------------------------------
from typing import Optional
from enum import Enum, auto
import json
import logging
from langchain.schema import SystemMessage

# TODO: Uncomment when doing integration into Pixie
"""
from services.abstractclasses.llm import LLM
"""


class ConversationEndingDeciderLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        Your goal is to decide if the conversation can be ended based on the last answer of an AI assistant and the last answer of the user.
        - If the conversation should be ended, return:
        True
        - If the conversation should continue, return:
        False

        Last question:
        {last_question}

        Last answer:
        {last_answer}

        Result:
        """

    def generate(self, last_question: str, last_answer: str) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(
            last_question=last_question, last_answer=last_answer
        )
        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            result = response.content
            return result
        except Exception as e:
            print(f"Error: {str(e)}")
        return None

    def should_end(self, last_question: str, last_answer: str) -> bool:
        result = self.generate(last_question, last_answer)
        if result is None:
            return False
        elif not "true" in result.lower():
            return False
        return True


# -----------------------------------------------------------------
# EndingConversationLLM
# -----------------------------------------------------------------
from typing import Optional
from enum import Enum, auto
import json
import logging
from langchain.schema import SystemMessage

# TODO: Uncomment when doing integration into Pixie
"""
from services.abstractclasses.llm import LLM
"""


class EndingConversationLLM:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt_template = """
        Your goal is to appropriately say goodbye based on the last answer of an AI assistant and the last answer of the user.
        Choose between:
        - Informing the user to address their questions to the staff if they still have any or are not helped.
        - Informing the user that he is free to ask questions in the future and you will be glad to help.
        Keep the language the same as this last answer, prefer Dutch as much as possible.

        Last question:
        {last_question}

        Last answer:
        {last_answer}

        Result:
        """

    def generate(self, last_question: str, last_answer: str) -> Optional[str]:
        system_prompt = self.system_prompt_template.format(
            last_question=last_question, last_answer=last_answer
        )
        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            result = response.content
            return result
        except Exception as e:
            print(f"Error: {str(e)}")
        return None


# -----------------
# Conversation loop
# -----------------
from typing import Generator


class ConversationLoop:
    def __init__(self, llm: LLM, max_tasks: int = 3, max_additional_questions: int = 4):
        # LLM with different system prompts and behavior
        self.llm = llm
        self.conversation_topics_checker_llm = ConversationTopicsCheckerLLM(llm=llm)
        self.task_decomposer_llm = TaskDecomposerLLM(llm=llm)
        self.top_specs_selector_llm = TopSpecsSelectorLLM(llm=llm)
        self.additional_question_llm = AdditionalQuestionLLM(llm=llm)
        self.similar_question_remover_llm = SimilarQuestionRemoverLLM(llm=llm)
        self.rag_query_generator_llm = RAGQueryGeneratorLLM(llm=llm)
        self.conversation_ending_decider_llm = ConversationEndingDeciderLLM(llm=llm)
        self.ending_conversation_llm = EndingConversationLLM(llm=llm)
        self.final_answer_llm = FinalAnswerLLM(llm=llm)
        self.initial_sentence_analyser_llm = InitialSentenceAnalyserLLM(llm=llm)
        # TODO: LLM which transforms answers in the preferred style

        # Constants
        self.max_tasks = max_tasks
        self.max_additional_questions = max_additional_questions

        # Generator
        self.conversation_generator = self.loop_generator()
        next(self.conversation_generator)

    def send(self, user_message: str) -> tuple[bool, str]:
        wait_for_user_input, ai_response = self.conversation_generator.send(
            user_message
        )
        return wait_for_user_input, ai_response

    def loop_generator(self) -> Generator[tuple[bool, str], str, None]:
        """
        Starts the conversational loop as a generator which represents a Finite State Machine.
        Yields a bool and AI response and expects the next user input via `send()` if the bool is True.
        Send `stop` to end the loop.
        """
        # TODO: replace mock in future
        allowed_entities = _services["tabular_vector_store"].get_allowed_entities(
            collection_name="auva"
        )  # mock_tabular_rag_allowed_entities()

        # Mutable state
        previous_state = ConversationState.WAITING_FOR_INITIAL_TASK
        current_state = ConversationState.WAITING_FOR_INITIAL_TASK
        current_task = None
        additional_qna_couples = []
        decomposed_tasks_queue = []
        current_task_query_result = pd.DataFrame()
        category = None

        def reset_state() -> None:
            nonlocal previous_state, current_state, current_task, additional_qna_couples, decomposed_tasks_queue, current_task_query_result, category
            previous_state = ConversationState.WAITING_FOR_INITIAL_TASK
            current_state = ConversationState.WAITING_FOR_INITIAL_TASK
            current_task = None
            additional_qna_couples = []
            decomposed_tasks_queue = []
            current_task_query_result = pd.DataFrame()
            category = None

        def update_state(state: ConversationState) -> None:
            nonlocal previous_state, current_state
            previous_state = current_state
            current_state = state

        ai_text = ""
        user_input = yield (True, "")
        # Conversation Loop

        while user_input is not None and user_input.lower() not in ["stop"]:
            # ------------------------------------------
            # ConversationState.WAITING_FOR_INITIAL_TASK
            # ------------------------------------------
            # Starting point
            # --------------
            if current_state == ConversationState.WAITING_FOR_INITIAL_TASK:
                reset_state()
                user_input = user_input.strip()
                is_suitable = self.conversation_topics_checker_llm.check(
                    question=user_input, entities=allowed_entities
                )
                if not is_suitable:
                    ai_text += (
                        self.conversation_topics_checker_llm.non_suitable_response(
                            entities=allowed_entities
                        )
                    )
                    user_input = yield (True, ai_text)
                    ai_text = ""
                    # Loop back to start until appropriate question is asked
                    update_state(ConversationState.WAITING_FOR_INITIAL_TASK)
                    continue

                update_state(ConversationState.INITIAL_TASK_GIVEN)
                continue

            # ------------------------------------------
            # ConversationState.INITIAL_TASK_GIVEN
            # ------------------------------------------
            elif current_state == ConversationState.INITIAL_TASK_GIVEN:
                decomposed_tasks_queue = [user_input]

                # self.task_decomposer_llm.decomposed_tasks(
                #    task=user_input
                # )
                empty_task_queue_or_error = (
                    not decomposed_tasks_queue or decomposed_tasks_queue == [""]
                )
                if empty_task_queue_or_error:
                    ai_text += (
                        self.conversation_topics_checker_llm.non_suitable_response(
                            entities=allowed_entities
                        )
                    )
                    user_input = yield (True, ai_text)
                    ai_text = ""
                    update_state(ConversationState.WAITING_FOR_INITIAL_TASK)
                    continue
                elif len(decomposed_tasks_queue) > self.max_tasks:
                    ai_text += f"Sorry, ik kan maximaal {self.max_tasks} deeltaken tegelijkertijd uitvoeren. Probeer je vraag hiertot te beperken."
                    user_input = yield (True, ai_text)
                    ai_text = ""
                    update_state(ConversationState.WAITING_FOR_INITIAL_TASK)
                    continue

                update_state(ConversationState.INITIAL_TASK_DECOMPOSED)
                continue

            # ------------------------------------------
            # ConversationState.INITIAL_TASK_DECOMPOSED
            # ------------------------------------------
            elif current_state == ConversationState.INITIAL_TASK_DECOMPOSED:
                print(
                    f">>>DECOMPOSED_TASKS_QUEUE in INITIAL_TASK_DECOMPOSED: {decomposed_tasks_queue}"
                )
                if decomposed_tasks_queue:
                    current_task = decomposed_tasks_queue.pop(
                        0
                    )  # dequeue the next task
                    update_state(ConversationState.PROCESSING_DECOMPOSED_TASK)
                else:
                    update_state(ConversationState.ADDITIONAL_QUESTIONS_ASKED)
                continue

            # --------------------------------------------
            # ConversationState.PROCESSING_DECOMPOSED_TASK
            # --------------------------------------------
            elif current_state == ConversationState.PROCESSING_DECOMPOSED_TASK:
                # TODO: replace mock in future
                # category, specs = _services[
                #    "tabular_vector_store"
                # ].get_recommended_table(question=current_task, collection_name="auva")

                category, specs_and_descriptions = mock_tabular_rag_choose_table(
                    llm=self.llm, task=current_task
                )

                reformulated_query = self.initial_sentence_analyser_llm.generate(
                    sentence=current_task,
                    allowed_entities=[category],
                    spec_list=specs_and_descriptions,
                )

                print(reformulated_query)

                top_specs = self.top_specs_selector_llm.top_specs(
                    task=reformulated_query,
                    category=category,
                    specs=specs_and_descriptions,
                    top_count=self.max_additional_questions,
                )
                additional_questions = []
                for spec in top_specs:
                    additional_question = self.additional_question_llm.generate(
                        task=current_task, spec=spec
                    )
                    if not additional_question:
                        continue
                    additional_questions.append(additional_question)
                additional_questions = (
                    self.similar_question_remover_llm.remove_similar_questions(
                        questions=additional_questions
                    )
                )

                for additional_question in additional_questions:
                    ai_text += additional_question
                    user_answer = yield (True, ai_text)
                    ai_text = ""
                    user_answer = user_answer.strip()
                    additional_qna_couples.append((additional_question, user_answer))

                update_state(ConversationState.ADDITIONAL_QUESTIONS_ASKED)
                continue

            # --------------------------------------------
            # ConversationState.ADDITIONAL_QUESTIONS_ASKED
            # --------------------------------------------
            elif (
                current_state == ConversationState.ADDITIONAL_QUESTIONS_ASKED
            ):  # and previous_state == ConversationState.PROCESSING_DECOMPOSED_TASK:
                reformulated_query = self.rag_query_generator_llm.generate(
                    task=current_task, couple_list=additional_qna_couples
                )
                additional_qna_couples = []
                # TODO: replace mock in future
                current_task_query_result = _services[
                    "tabular_vector_store"
                ].product_search(
                    collection_name="auva",
                    product_name=category,
                    question=reformulated_query,
                    top_k=3,
                )

                # mock_tabular_rag_toolcall(
                #    query=reformulated_query
                # )
                if current_task_query_result:
                    update_state(ConversationState.SEARCH_DATABASE_ENTITIES_RESULTS)
                else:
                    update_state(ConversationState.SEARCH_DATABASE_ENTITIES_NO_RESULTS)
                continue

            # --------------------------------------------------
            # ConversationState.SEARCH_DATABASE_ENTITIES_RESULTS
            # --------------------------------------------------
            elif current_state == ConversationState.SEARCH_DATABASE_ENTITIES_RESULTS:
                # TODO: replace mock in future
                ai_text += (
                    self.final_answer_llm.generate(
                        task=current_task,
                        data=current_task_query_result,
                    )
                    # mock_final_answer(task=current_task, data=current_task_query_result)
                    + "\n"
                )
                print(f">>>DECOMPOSED_TASKS_QUEUE: {decomposed_tasks_queue}")
                if decomposed_tasks_queue:
                    current_task = decomposed_tasks_queue.pop(0)
                    update_state(ConversationState.PROCESSING_DECOMPOSED_TASK)
                    continue

                update_state(ConversationState.INITIAL_TASK_DONE)
                continue

            # -----------------------------------------------------
            # ConversationState.SEARCH_DATABASE_ENTITIES_NO_RESULTS
            # -----------------------------------------------------
            elif current_state == ConversationState.SEARCH_DATABASE_ENTITIES_NO_RESULTS:
                # print(">>>DEBUG>>>")
                ai_text += "Sorry, dat ik niets gevonden heb wat je zocht. Je kan je voor deze vraag best richten tot een van onze medewerkers!\n"
                if decomposed_tasks_queue:
                    current_task = decomposed_tasks_queue.pop(0)
                    update_state(ConversationState.PROCESSING_DECOMPOSED_TASK)
                    continue
                update_state(ConversationState.INITIAL_TASK_DONE)
                continue

            # -----------------------------------------------------
            # ConversationState.INITIAL_TASK_DONE
            # -----------------------------------------------------
            elif current_state == ConversationState.INITIAL_TASK_DONE:
                # No more tasks to handle
                ai_text += "Kan ik je verder nog helpen met iets, zo ja waarmee?"
                user_input = yield (True, ai_text)
                ai_text = ""
                user_input = user_input.strip()
                should_end = self.conversation_ending_decider_llm.should_end(
                    last_question=ai_text, last_answer=user_input
                )
                if should_end:
                    update_state(ConversationState.USER_STOP_CONVERSATION)
                    continue
                # print(">>>DEBUG>>>")
                update_state(ConversationState.WAITING_FOR_INITIAL_TASK)
                continue

            # -----------------------------------------------------
            # ConversationState.USER_STOP_CONVERSATION
            # -----------------------------------------------------
            # Ending point
            # -------------
            elif current_state == ConversationState.USER_STOP_CONVERSATION:
                break

        # End of conversation
        ending_message = self.ending_conversation_llm.generate(
            last_question=ai_text, last_answer=user_input
        )
        if ending_message:
            yield (False, ending_message)
        yield (False, "Tot ziens!")

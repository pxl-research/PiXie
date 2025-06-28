# Example of usage code:
'''
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
'''

from services.abstractclasses.llm import LLM
from services.llms.azure_openai_llm import AzureOpenAILLM


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
        You are an AI classifier. Your task is to determine whether a user's question is suitable for a dialogue with an AI assistant about specific allowed topics, including their close synonyms and the broader category they fall under.

        Allowed topics (including all close synonyms and related terminology):
        {allowed_entities}

        Your job:
        1. Internally generalize these allowed topics into a broader concept or domain.
        2. Consider synonyms, hyponyms, and hypernyms (e.g., if "running shoes" is allowed, then "sneakers", "athletic shoes", and the broader term "footwear" are also acceptable).
        3. Determine if the user's text is clearly related to any of:
           - the explicitly listed topics,
           - the general category encompassing those topics,
           - or typical subtopics such as: specifications, prices, work-relatance to these topics, or practical usage.

        Rules:
        - Return True if the user text is about the allowed topics, their synonyms, or the general category (even loosely).
        - Return False if it's not meaningfully related.

        Given user text:
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
        1.  Identify Primary Entities/Topics: Each item in the output list should represent a request concerning a *single, main entity or topic*.
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
        For a given domain or category, and a list of attributes (features, fields, or parameters), rank the attributes from most likely to be asked or needed by a user to least likely.

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

        Given list of attributes:
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
                    top_specs_list = ["for_what_you_should_use_this"] + top_specs_list
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
        Reformulate this question so it contains the same information but does not sound stiff, make it sound grammatically correct.
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
) -> tuple[Optional[str], list[str]]:
    mapping = {
        "laptops": [
            "barcode",
            "naam",
            "merk",
            "categorie",
            "prijs",
            "beschikbaar",
            "beschrijving",
            "vormfactor",
            "beeldschermdiagonaal_cm",
            "touchscreen",
            "processorfamilie",
            "processorfabrikant",
            "processormodel",
            "aantal_processorkernen",
            "intern_geheugen_GB",
            "intern_geheugentype",
            "totale_opslagcapaciteit_GB",
            "opslagmedia",
            "aparte_grafische_adapter",
            "discreet_grafische_adapter_model",
            "ingebouwde_microfoon",
            "camera_voorzijde",
            "aantal_usb_20_poorten",
            "aantal_poorten_usb_32_gen_1_31_gen_1_typ",
            "aantal_hdmi_poorten",
            "numeriek_toetsenblok",
            "aanwijsapparaat",
            "inclusief_besturingssysteem",
            "batterijcapaciteit_Wh",
            "ac_adapter_vermogen_W",
            "gewicht_kg",
            "breedte_mm",
            "diepte_mm",
            "totale_opslagcapaciteit_TB",
            "aantal_geinstalleerde_ssds",
            "ssd_capaciteit_TB",
            "ssd_capaciteit_GB",
        ],
        "pcs": [
            "barcode",
            "naam",
            "merk",
            "categorie",
            "prijs",
            "beschikbaar",
            "beschrijving",
            "processorfamilie",
            "processorfabrikant",
            "processormodel",
            "processorgeneratie",
            "aantal_processorkernen",
            "processor_aantal_threads",
            "maximale_turbofrequentie_van_processor_GHz",
            "processor_cache_MB",
            "processor_cache_type",
            "intern_geheugen_GB",
            "maximum_intern_geheugen_GB",
            "intern_geheugentype",
            "opslagmedia",
            "aantal_geinstalleerde_ssds",
            "aparte_grafische_adapter",
            "ingebouwde_grafische_adapter",
            "discreet_grafische_adapter_model",
            "on_board_graphics_adapter_model",
            "ethernet_lan_data_overdrachtsnelheden_Mbit",
            "aantal_ethernet_lan_rj_45_poorten",
            "type_behuizing",
            "inclusief_besturingssysteem",
            "netvoeding_W",
            "breedte_mm",
            "gewicht_kg",
        ],
        "printers": [
            "barcode",
            "naam",
            "merk",
            "categorie",
            "prijs",
            "beschikbaar",
            "beschrijving",
            "printtechnologie",
            "duplex_printen",
            "maximale_resolutie_0_dpi",
            "maximale_resolutie_1_dpi",
            "scannen",
            "totale_invoercapaciteit",
            "totale_uitvoercapaciteit",
            "maximale_iso_a_series_papierformaat",
            "printsnelheid_zwart_standaardkwaliteit_a_ppm",
            "inclusief_besturingssysteem",
            "netvoeding_W",
            "breedte_mm",
            "gewicht_kg",
        ],
        "inktpatronen": [
            "barcode",
            "naam",
            "merk",
            "categorie",
            "prijs",
            "beschikbaar",
            "beschrijving",
            "merkcompatibiliteit",
            "compatibiliteit",
            "aantal_per_verpakking",
            "paginaopbrengst_gekleurde_inkt",
            "paginaopbrengst_zwarte_inkt",
            "type_zwarte_inkt",
            "type_kleureninkt",
            "inkjet_cartridge_type",
            "oem_code",
            "inkttype",
        ],
        "toners": [
            "barcode",
            "naam",
            "merk",
            "categorie",
            "prijs",
            "beschikbaar",
            "beschrijving",
            "printkleuren",
            "merkcompatibiliteit",
            "compatibiliteit",
            "zwarte_toner_paginaopbrengst",
            "kleurentoner_paginaopbrengst",
            "type_verpakking",
            "printtechnologie",
        ],
        "computermonitoren": [
            "barcode",
            "naam",
            "merk",
            "categorie",
            "prijs",
            "beschikbaar",
            "beschrijving",
            "beeldschermdiagonaal_cm",
            "resolutie_0_pixels",
            "resolutie_1_pixels",
            "display_technologie",
            "soort_paneel",
            "responstijd_ms",
            "typische_contrastverhouding_0_None",
            "typische_contrastverhouding_1_None",
            "maximale_refresh_snelheid_Hz",
            "helderheid_typisch_cd",
            "hdmi",
            "aantal_hdmi_poorten",
            "vesa_montage",
            "paneelmontage_interface_0_mm",
            "paneelmontage_interface_1_mm",
        ],
    }
    mock_table_chooser_llm = MockTableChooserLLM(llm=llm)
    chosen_key = mock_table_chooser_llm.generate(
        task=task, table_list=list(mapping.keys())
    )
    spec_list = []
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
        allowed_entities = mock_tabular_rag_allowed_entities()

        # Mutable state
        previous_state = ConversationState.WAITING_FOR_INITIAL_TASK
        current_state = ConversationState.WAITING_FOR_INITIAL_TASK
        current_task = None
        additional_qna_couples = []
        decomposed_tasks_queue = []
        current_task_query_result = pd.DataFrame()

        def reset_state() -> None:
            nonlocal previous_state, current_state, current_task, additional_qna_couples, decomposed_tasks_queue, current_task_query_result
            previous_state = ConversationState.WAITING_FOR_INITIAL_TASK
            current_state = ConversationState.WAITING_FOR_INITIAL_TASK
            current_task = None
            additional_qna_couples = []
            decomposed_tasks_queue = []
            current_task_query_result = pd.DataFrame()

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
                decomposed_tasks_queue = self.task_decomposer_llm.decomposed_tasks(
                    task=user_input
                )
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
                category, specs = mock_tabular_rag_choose_table(
                    llm=self.llm, task=current_task
                )
                top_specs = self.top_specs_selector_llm.top_specs(
                    task=current_task,
                    category=category,
                    specs=specs,
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
                rag_query_generator_llm = RAGQueryGeneratorLLM(llm=llm)
                reformulated_query = rag_query_generator_llm.generate(
                    task=current_task, couple_list=additional_qna_couples
                )
                additional_qna_couples = []
                # TODO: replace mock in future
                current_task_query_result = mock_tabular_rag_toolcall(
                    query=reformulated_query
                )
                if not current_task_query_result.empty:
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
                    mock_final_answer(task=current_task, data=current_task_query_result)
                    + "\n"
                )
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

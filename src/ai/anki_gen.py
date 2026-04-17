import concurrent.futures
import json
import logging
import math
import os
import pathlib
import sys
from typing import TYPE_CHECKING

import customtkinter as ctk
import ollama
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from ai import embedding
from ai.model_type import ModelType, CallType
from handler.pdf_handler import pdf_handler

if TYPE_CHECKING:
    from ui.app import App


class AnkiGen:
    def __init__(self, model_type: ModelType, model: str, app_instance: App):
        self.app_instance = app_instance
        self.window_active = True
        self.threshold_value = 0.8
        self.progress = 0
        self.model = model
        self.model_type = model_type
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        if self.model_type == ModelType.API:
            self.workers = 30
            self.rework_size = 50
        else:
            self.workers = 3
            self.rework_size = 30

    def set_pdf_handler(self, path: pathlib.Path):
        self.handler = pdf_handler(path)

    def set_threshold_value(self, threshold_value: float):
        self.threshold_value = threshold_value

    def load_embedding_model(self):
        if getattr(sys, 'frozen', False):
            model_path = os.path.join(sys._MEIPASS, "ai", "model_data")
            self.embedding_model = SentenceTransformer(model_path, local_files_only=True)
        else:
            model_path = os.path.join("src", "ai", "model_data")
            if not os.path.exists(model_path):
                self.logger.warning("Model not found. Downloading for the first time...")
                temp_model = SentenceTransformer('all-MiniLM-L6-v2')
                temp_model.save(model_path)
                self.logger.warning(f"Model got saved in  {model_path}")
            self.embedding_model = SentenceTransformer(model_path)

    def set_model(self, model: str):
        self.model = model

    def rework_part(self, cards: list[dict]):
        system_prompt = r"""You are an expert Anki Content Optimizer. Your task is to filter, categorize, and refine a list of flashcards.

        ### DECISION MATRIX:
        You MUST return a valid JSON object with the following structure:
        {
          "keep": [
            {"front": "...", "back": "...", "topic": "..."}
          ],
          "rework": [
           {
              "front": "...", 
              "back": "...", 
              "topic": "...", 
              "reason": "Why it needs rework"
            }
          ],
          "delete_count": 5
        }
        1. KEEP (Direct JSON Output):
           - Use this for cards that are factually correct, concise, and exam-ready.
           - Criteria: The answer (back) must be shorter than 3 sentences and formatted clearly (e.g., bullet points).
        
        2. DELETE (Ignore):
           - Organizational data (dates, room numbers, job offers, professor contact info).
           - Cards where the front is a single generic word (e.g., "Note", "Context") that is not a technical term.
           - Exact duplicates or redundant information already covered in better cards.
        
        3. REWORK :
           - WHEN: The content is exam-relevant, but the formatting or phrasing is poor.
           - WHY (Specific Criteria):
             * 'Wall of Text': The answer is a long, unstructured paragraph.
             * 'Vague Question': The question is too broad (e.g., "What about Ethics?").
             * 'Single-Word Issue': The front is an important technical term (e.g., "Cosine Similarity"), but the back is incomplete, messy, or lacks a clear definition.
             * 'Incomplete Answer': The back provides fewer items than requested (e.g., list of 5 instead of 6).
             * 'Generation Cut-off': The answer ends abruptly mid-sentence or mid-structure.
             * 'Context Leak': Mentions slide numbers, page numbers, or "previous sections".
             * 'Formatting Glitch': Broken LaTeX ($...$) or Markdown syntax.
            - MANDATORY: For every card in the 'rework' list, you MUST provide a 'reason' field 
                explaining exactly what is wrong (e.g., 'Wall of Text', 'No Question Mark').
           - HOW: Add them in the "rework" section.
        
        IMPORTANT: 
        - Every input card must be assigned to exactly ONE category (keep, rework, or delete).
        - The "rework" section contains the original fields plus the "reason".
        """

        user_prompt = f"""
                Filter and condense the following list of cards. Ensure the result is manageable and focuses on the most important exam-relevant knowledge.

                INPUT_CARDS:
                {json.dumps(cards)}
                """
        self.logger.info(f"Checking {len(cards)} cards")
        return self.run_prompt(system_prompt, user_prompt, "Rework error", CallType.FILTER_AND_SPLIT)

    def rework_flashcard(self, flashcard: list[dict]):
        """Improves flashcards
        Input: A worse Flashcard to improve
        Output: Reworked Flashcard"""
        rework_system_prompt = r"""You are an Anki Refinement Specialist. Your task is to take a list of sub-optimal flashcards and transform them into high-quality, atomic learning units.

        ### OBJECTIVES:
        - 'Wall of Text': The answer is a long, unstructured paragraph. -> Fix by using clear bullet points (max 3 per card).
        - 'Vague Question': The question is too broad (e.g., "What about Ethics?"). -> Clarify by making the front specific and targeted.
        - 'Single-Word Issue': The front is an important technical term (e.g., "Cosine Similarity"), but the back is incomplete, messy, or lacks a clear definition. -> Expand into clear, comprehensive definitions.
        - 'Incomplete Answer': The back provides fewer items than requested (e.g., list of 5 instead of 6). -> Ensure the back matches the requested number of items.
        - 'Generation Cut-off': The answer ends abruptly mid-sentence or mid-structure. -> Complete the sentence and restore the full logical structure.
        - 'Context Leak': Mentions slide numbers, page numbers, or "previous sections". -> Remove all external references to make the card self-contained.
        - 'Formatting Glitch': Broken LaTeX ($...$) or Markdown syntax. -> Repair the syntax to ensure all elements render correctly.
        - 'MANDATORY': Every 'front' must be a grammatically correct, self-contained question ending with a question mark; if the input is a statement or a noun, you MUST rephrase it into a 'How', 'What', 'Why', or 'Which' question.

        ### OUTPUT FORMAT:
        You MUST return a valid JSON object with a single list called 'cards':
        {
          "cards": [
            {"front": "...", "back": "...", "topic": "..."},
            {"front": "...", "back": "...", "topic": "..."}
          ]
        }
        """
        rework_user_prompt = f"""
        Improve the following flashcards. Use the provided 'reason' to guide your refinement for each card.

        INPUT_CARDS_TO_FIX:
        {json.dumps(flashcard)}
        """
        self.logger.info(f"Reworking {len(flashcard)} flashcards.")
        self.logger.debug(f"Flashcards to rework: {flashcard}")
        return self.run_prompt(rework_system_prompt, rework_user_prompt, "Rework error", CallType.CARD_IMPROVEMENT)

    def rework(self, cards: list[dict]):
        """reworks created anki cards deletes unnecessary and bad cards"""
        self.logger.info("Reworking anki cards...")
        if hasattr(self.app_instance, "details_window"):
            self.app_instance.details_window.reset_progress_bar()
        self.progress = 0

        self.rework_iterations = math.ceil(len(cards) / self.rework_size)
        rework_cards = []
        pending_tasks = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            for i in range(0, self.rework_iterations):
                task = executor.submit(self.rework_part, cards[i * self.rework_size:(i + 1) * self.rework_size])
                pending_tasks.append(task)
            for future in concurrent.futures.as_completed(pending_tasks):
                if not self.window_active:
                    self.logger.warning("Window closed generation stopped")
                    return
                try:
                    rework_cards.extend(future.result())
                except Exception as e:
                    self.logger.error(f"Error: {e}")
        self.logger.info(f"Reworked cards: {len(rework_cards)}")
        embeddet = embedding.delete_dupes(rework_cards, self.embedding_model, self.logger, self.threshold_value)
        self.logger.info(f"Cards after duplicate deletion: {len(embeddet)}")
        return embeddet

    def createCards(self, language: str, info_label: ctk.CTkLabel):
        """running different threads for multiple tasks, AI api calls, creating cards"""
        cards = []
        all_cards = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            for i in range(self.handler.pages):
                page = self.handler.get_pdf_page()
                page_cards = executor.submit(self._createCard_part, page, language, i)
                cards.append(page_cards)
            for future in concurrent.futures.as_completed(cards):
                if not self.window_active:
                    self.logger.warning("Window closed generation stopped")
                    return
                try:
                    page_cards = future.result()
                    all_cards.extend(page_cards)
                except Exception as e:
                    self.logger.error(f"Error: {e}")
        info_label.configure(text="execute card rework ...")
        self.logger.info(f"Created {len(all_cards)} cards.")
        final_cards = self.rework(all_cards)
        return final_cards

    def _createCard_part(self, input: str, language: str, page_num: int):
        self.logger.info(f"Creating {language} cards for page {page_num}")
        system_prompt = r"""
        You are a professional Flashcard creator. 
        Analyze the provided text and extract the core concepts into flashcards.
        Output MUST be a valid JSON object containing a list called 'cards'.
        Each card must have 'front' and 'back' fields.
        Example:
                {
        "cards": [
            {
        "front": "What is a apple?",
              "back": "A fruit",
              "topic": "Fruits"
            }
          ]
        }
        TECHNICAL FORMATTING:
        -  Use $...$ for ALL math/technical variables (e.g., $P_n$, $\rho$, $E[T]$).
        - Ensure valid JSON output. Double-escape backslashes in LaTeX (e.g., \\frac{1}{2}).
        - Topic field must be a high-level category 
        STRICT FRONT-SIDE RULE:
        - Every 'front' MUST start with a question word (What, How, Why, Which, etc.).
        - A 'front' that is only a noun or a phrase (e.g., "DNS Purpose") is a CRITICAL ERROR.
        - Imagine the user is being tested: The 'front' must provide enough context to give a precise answer.
        PEDAGOGICAL RULES:
        - Use Active Recall: Ask specific questions.
        - Atomic Cards: One concept per card. 
        - No "Yes/No" questions.
        - If the input text is just an organizational slide or lacks technical substance, return {"cards": []}.
        Keep the answers concise and focused on one concept per card. Also add a field with 'topic' this should store 
        the core topic which the card is about only 1-4 words. 
        """

        user_prompt = f"""
        Convert the following lecture notes into necessary high-quality Anki cards use all important things.
        LANGUAGE RULE:
        - All content (front, back, topic) MUST be in {language}. If {language} is "default", use the primary language found in the provided text. Do not translate technical terms that are commonly used in their original form.
        STRICT RULES:
        1. IGNORE all organizational data: Do not create cards about professor names, university names, course IDs, dates, slide numbers, or bibliography.
        2. FOCUS on: Definitions, technical concepts, algorithms, code logic, and factual relationships.
        3. SKIP meta-information: No cards about "Lecture 1", "Introduction", or "Thank you for your attention" slides.
        4. Q&A STYLE: The 'front' must be a specific question. The 'back' must be the direct answer.
        5.  Every 'front' MUST be a complete, self-contained question. Never use single words or sentence fragments as a question. 
        6. Ignore Example calculations and examples in general
         
        ---
        {input}
        
        ---
        """
        return self.run_prompt(system_prompt, user_prompt, "generation error", CallType.CARD_GENERATION)

    def run_prompt(self, system_prompt: str, user_prompt: str, error_message: str, mode: CallType):
        final_cards = []
        if not self.window_active:
            return
        if self.model_type is ModelType.API:
            client = OpenAI(
                api_key=self.app_instance.api_key,
                base_url="https://api.deepseek.com"
            )

            try:
                messages = [{"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}]
                params = {
                    "model": "deepseek-chat",
                    "messages": messages,
                    "stream": False,
                    "response_format": {"type": "json_object"}
                }
                response = client.chat.completions.create(**params)
                data = json.loads(response.choices[0].message.content)
                window = getattr(self.app_instance, "details_window", None)
                if window and (
                        mode is CallType.CARD_GENERATION or mode is CallType.CARD_IMPROVEMENT):
                    final_cards.extend(data.get("cards", []))
                    self.progress = self.progress + 1
                    if mode is CallType.CARD_GENERATION:
                        self.app_instance.details_window.bar.set(self.progress / self.handler.pages)
                    else:
                        self.app_instance.details_window.bar.set(self.progress / self.rework_iterations)


                else:
                    well_cards = data.get("keep", [])
                    cards_to_improve = data.get("rework", [])
                    final_cards.extend(well_cards)
                    if cards_to_improve:
                        final_cards.extend(self.rework_flashcard(cards_to_improve))

            except Exception as e:
                self.logger.error(f"{error_message} {e}")
                return []

        elif self.model_type is ModelType.LOCALE:
            try:
                response = ollama.chat(model=self.model, format='json', options={"num_ctx": 4096},
                                       messages=[{"role": "system", "content": system_prompt},
                                                 {"role": "user", "content": user_prompt}])
                data = json.loads(response.message.content)
                window = getattr(self.app_instance, "details_window", None)
                if window and (
                        mode is CallType.CARD_GENERATION or mode is CallType.CARD_IMPROVEMENT):
                    final_cards.extend(data.get("cards", []))
                    self.progress = self.progress + 1
                    if mode is CallType.CARD_GENERATION:
                        self.app_instance.details_window.bar.set(self.progress / self.handler.pages)
                    else:
                        self.app_instance.details_window.bar.set(self.progress / self.rework_iterations)
                else:
                    cards_to_improve = data.get("rework", [])
                    if cards_to_improve:
                        final_cards.extend(self.rework_flashcard(cards_to_improve))
                    final_cards.extend(data.get("keep", []))

            except Exception as e:
                self.logger.error(f"{error_message} {e}")
                return []
        return final_cards

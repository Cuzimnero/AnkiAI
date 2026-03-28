import concurrent.futures
import json
import math
import os
import pathlib
from ftplib import print_line

import customtkinter as ctk
import ollama
from dotenv import load_dotenv
from openai import OpenAI

from handler.pdf_handler import pdf_handler
from . import embedding


class AnkiGen:
    def __init__(self, model_type: int, model: str):
        self.model = model
        self.type = model_type
        load_dotenv()
        if self.type == 1:
            self.workers = 30
            self.rework_size = 50
        else:
            self.workers = 3
            self.rework_size = 30

    def set_pdf_handler(self, path: pathlib.Path):
        self.handler = pdf_handler(path)

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

        return self.run_prompt(system_prompt, user_prompt, "Rework error", 2)

    def rework_flashcard(self, flashcard: list[dict]):
        """Improves flashcards
        Input: A worse Flashcard to improve
        Output: Reworked Flashcard"""
        rework_system_prompt = r"""You are an Anki Refinement Specialist. Your task is to take a list of sub-optimal flashcards and transform them into high-quality, atomic learning units.

        ### OBJECTIVES:
        - MANDATORY: Every 'front' must be a grammatically correct, self-contained question ending with a question mark; if the input is a statement or a noun, you MUST rephrase it into a 'How', 'What', 'Why', or 'Which' question.
        - Fix 'Wall of Text' by using clear bullet points (max 3 per card).
        - Clarify 'Vague Questions' by making the front specific.
        - Expand 'Single-Word Issues' into clear definitions.
        - Keep the language professional and concise.

        ### OUTPUT FORMAT:
        You MUST return a valid JSON object with a single list called 'refined_cards':
        {
          "refined_cards": [
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
        print("Rework Worse Cards")
        print("___________________________________________________________________________________________________")
        print(flashcard)
        return self.run_prompt(rework_system_prompt, rework_user_prompt, "Rework error", 1)

    def rework(self, cards: list[dict]):
        """reworks created anki cards deletes unnecessary and bad cards"""
        print("rework started")
        n = math.ceil(len(cards) / self.rework_size)
        rework_cards = []
        pending_tasks = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            for i in range(0, n):
                task = executor.submit(self.rework_part, cards[i * self.rework_size:(i + 1) * self.rework_size])
                pending_tasks.append(task)
            for future in concurrent.futures.as_completed(pending_tasks):
                try:
                    rework_cards.extend(future.result())
                except Exception as e:
                    print(f"Fehler{e}")
        print(rework_cards)
        embeddet = embedding.delete_dupes(rework_cards)
        print_line("_____________________________________")
        print(embeddet)
        return embeddet

    def createCards(self, language: str, info_label: ctk.CTkLabel):
        """running different threads for multiple tasks, AI api calls, creating cards"""
        cards = []
        all_cards = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            for i in range(self.handler.pages):
                page = self.handler.get_pdf_page()
                page_cards = executor.submit(self._createCard_part, page, language)
                cards.append(page_cards)
            for future in concurrent.futures.as_completed(cards):
                try:
                    page_cards = future.result()
                    all_cards.extend(page_cards)
                except Exception as e:
                    print(f"Fehler: {e}")
        info_label.configure(text="execute card rework ...")
        final_cards = self.rework(all_cards)
        return final_cards

    def _createCard_part(self, input: str, language: str):
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
        Convert the following lecture notes into necessary high-quality Anki cards use all important things. If its makes sense use Multiple-choice options use the language {language} default means the language of the lecture.
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
        return self.run_prompt(system_prompt, user_prompt, "generation error", 3)

    def run_prompt(self, system_prompt: str, user_prompt: str, error_message: str, case: int):
        final_cards = []
        if self.type == 1:
            client = OpenAI(
                api_key=os.environ.get('DEEPSEEK_API_KEY'),
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
                if case == 1:
                    final_cards.extend(data.get("refined_cards", []))
                elif case == 3:
                    final_cards.extend(data.get("cards", []))
                else:
                    well_cards = data.get("keep", [])
                    cards_to_improve = data.get("rework", [])
                    final_cards.extend(well_cards)
                    if cards_to_improve:
                        final_cards.extend(self.rework_flashcard(cards_to_improve))

            except Exception as e:
                print(f"{error_message} {e}")
                return []

        elif self.type == 2:
            try:
                response = ollama.chat(model=self.model, format='json', options={"num_ctx": 4096},
                                       messages=[{"role": "system", "content": system_prompt},
                                                 {"role": "user", "content": user_prompt}])
                data = json.loads(response.message.content)
                if case == 1:
                    final_cards.extend(data.get("refined_cards", []))
                elif case == 3:
                    final_cards.extend(data.get("cards", []))
                else:
                    cards_to_improve = data.get("rework", [])
                    if cards_to_improve:
                        final_cards.extend(self.rework_flashcard(cards_to_improve))
                    final_cards.extend(data.get("keep", []))

            except Exception as e:
                print(f"{error_message} {e}")
                return []
        return final_cards

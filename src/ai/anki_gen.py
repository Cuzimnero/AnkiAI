import concurrent.futures
import json
import math
import os
import pathlib
from ftplib import print_line
from pathlib import Path
import customtkinter as ctk
from . import embedding
import ollama
from dotenv import load_dotenv
from httpx import options
from openai import OpenAI
from handler.pdf_handler import pdf_handler


class AnkiGen:
    def __init__(self, model_type:int, model:str):
        self.model=model
        self.type=model_type
        load_dotenv()
        if self.type==1:
            self.workers=30
            self.rework_size=150
        else:
            self.workers=3
            self.rework_size=30

    def set_pdf_handler(self,path:pathlib.Path):
        self.handler = pdf_handler(path)

    def set_model(self,model:str):
        self.model = model
        

    def rework_part(self,cards: list[dict]):
        system_prompt = f"""
                You are an expert Anki content optimizer. 
                Your task is to take a large, redundant list of flashcards and refine it into a high-quality, concise study deck.
                
                RULES:
                1. DELETE: Remove all cards regarding organizational data, job offers, university-specific meta-info.
                2. PRIORITIZE: Keep only core definitions, technical concepts, and ethical theories.
                3. COMPLETENESS: Ensure that every technical term mentioned in the input cards is still represented in the final output.
                4. Delete cards only containing one word as front.
                Output MUST be a valid JSON object containing a list called 'cards' with 'front', 'back', and 'topic' fields.
                """

        user_prompt = f"""
                Filter and condense the following list of cards. Ensure the result is manageable and focuses on the most important exam-relevant knowledge.

                INPUT_CARDS:
                {json.dumps(cards)}
                """
        return self.run_prompt(system_prompt,user_prompt,"Rework error")




    def rework(self, cards: list[dict]):
        """reworks created anki cards deletes unnecessary and bad cards"""
        print("rework started")
        n=math.ceil(len(cards)/self.rework_size)
        rework_cards=[]
        pending_tasks=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            for i in range(0,n):
                task=executor.submit(self.rework_part,cards[i*self.rework_size:(i+1)*self.rework_size])
                pending_tasks.append(task)
            for future in concurrent.futures.as_completed(pending_tasks):
                try:
                    rework_cards.extend(future.result())
                except Exception as e:
                    print(f"Fehler{e}")
        print(rework_cards)
        embeddet=embedding.delete_dupes(rework_cards)
        print_line("_____________________________________")
        print(embeddet)
        return  embeddet



    def createCards(self,language:str,info_label:ctk.CTkLabel):
        """running different threads for multiple tasks, AI api calls, creating cards"""
        cards=[]
        all_cards=[]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            for i in range(self.handler.pages):
                page=self.handler.get_pdf_page()
                page_cards=executor.submit(self._createCard_part,page,language)
                cards.append(page_cards)
            for future in concurrent.futures.as_completed(cards):
                try:
                 page_cards = future.result()
                 all_cards.extend(page_cards)
                except Exception as e:
                 print(f"Fehler: {e}")
        info_label.configure(text="execute card rework ...")
        final_cards=self.rework(all_cards)
        return final_cards


    def _createCard_part(self,input:str,language:str):
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
        return self.run_prompt(system_prompt,user_prompt,"generation error")

    def run_prompt(self,system_prompt:str,user_prompt:str,error_message:str):
        if self.type==1:
            client = OpenAI(
                api_key=os.environ.get('DEEPSEEK_API_KEY'),
                base_url="https://api.deepseek.com"
            )

            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    stream=False,
                    response_format={'type': 'json_object'}
                )

                data = json.loads(response.choices[0].message.content)
                return data.get("cards", [])

            except Exception as e:
                print(f"{error_message} {e}")
                return []

        elif self.type==2:
             try:
                response = ollama.chat(model=self.model,format='json',options={"num_ctx":4096}, messages=[{"role": "system", "content": system_prompt},
                                                                   {"role": "user", "content": user_prompt}])
                data = json.loads(response.message.content)
                refined_cards = data.get("cards", [])
                return refined_cards
             except Exception as e:
                print(f"{error_message} {e}")
                return []







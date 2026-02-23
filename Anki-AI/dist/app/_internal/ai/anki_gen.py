import concurrent.futures
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from handler.pdf_handler import pdf_handler


class AnkiGen:
    def __init__(self):
        load_dotenv()

    def rework(self, cards: list[dict]):

        system_prompt = """
        You are an expert Anki content optimizer. 
        Your task is to take a large, redundant list of flashcards and refine it into a high-quality, concise study deck.

        RULES:
        1. MERGE: Combine cards that cover the same topic (e.g., individual GDPR principles) into a single, comprehensive card.
        2. DELETE: Remove all cards regarding organizational data, job offers, university-specific meta-info, or trivial filler content.
        3. DEDUPLICATE: Identify and remove nearly identical questions.
        4. PRIORITIZE: Keep only core definitions, technical concepts, and ethical theories.

        Output MUST be a valid JSON object containing a list called 'cards' with 'front', 'back', and 'topic' fields.
        """

        user_prompt = f"""
        Filter and condense the following list of cards. Ensure the result is manageable and focuses on the most important exam-relevant knowledge.

        INPUT_CARDS:
        {json.dumps(cards)}
        """

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
            refined_cards = data.get("cards", [])
            return refined_cards

        except Exception as e:
            print(f"Fehler beim Rework: {e}")
            return cards

    def createCards(self,path: Path,context:str,language:str):
        print("t")
        cards=[]
        all_cards=[]
        handler=pdf_handler(path)
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for i in range(handler.pages):
                print("t")
                page=handler.get_pdf_page()
                page_cards=executor.submit(AnkiGen._createCard_part,page,context,language)
                cards.append(page_cards)
            for future in concurrent.futures.as_completed(cards):
                try:
                 page_cards = future.result()
                 all_cards.extend(page_cards)
                except Exception as e:
                 print(f"Fehler: {e}")
        print("rework")
        final_cards=self.rework(all_cards)
        print(final_cards)
        return final_cards

    @staticmethod
    def _createCard_part(input:str,context:str,language:str):
        system_prompt = """
        You are a professional Anki card creator. 
        Analyze the provided text and extract the core concepts into flashcards.
        Output MUST be a valid JSON object containing a list called 'cards'.
        Each card must have 'front' and 'back' fields.
        Keep the answers concise and focused on one concept per card. Also add a field with 'topic' this should store 
        the core topic which the card is about only 1-4 words.
        """

        user_prompt = f"""
        Convert the following lecture notes into necessary high-quality Anki cards use all important things. If its makes sense use Multiple-choice options use the language {language} default means the language of the lecture.
        THE EXACT TOPIC OF THIS LECTURE IS: {context}
        
        STRICT RULES:
        1. IGNORE all organizational data: Do not create cards about professor names, university names, course IDs, dates, slide numbers, or bibliography.
        2. FOCUS on: Definitions, technical concepts, algorithms, code logic (e.g., OpenMP directives), and factual relationships.
        3. SKIP meta-information: No cards about "Lecture 1", "Introduction", or "Thank you for your attention" slides.
        4. Create cards EXCLUSIVELY for concepts, definitions, and theories that directly belong to the context mentioned above ({context}).
        ---
        {input}
        
        ---
        """
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

            data=json.loads(response.choices[0].message.content)
            return  data.get("cards",[])

        except Exception as e:
            print(f"Fehler beim Testen: {e}")
            return []

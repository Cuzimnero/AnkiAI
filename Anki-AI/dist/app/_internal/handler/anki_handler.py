import random
from pathlib import Path

import genanki


class anki_handler:

    def __init__(self,deck_name:str):
        self.deckname=deck_name
        style = """
            .card {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 20px;
                text-align: center;
                color: #2c3e50;
                background-color: #f9f9f9;
                padding: 20px;
            }

            .topic-box {
                display: inline-block;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                background-color: #3498db;
                color: white;
                padding: 4px 12px;
                border-radius: 15px;
                margin-bottom: 20px;
                font-weight: bold;
            }

            .question {
                font-weight: 600;
                line-height: 1.4;
                margin-top: 10px;
            }

            .answer {
                color: #2980b9;
                margin-top: 20px;
                font-weight: 400;
            }

            hr#answer {
                border: 0;
                height: 1px;
                background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(52, 152, 219, 0.75), rgba(0, 0, 0, 0));
                margin-top: 30px;
            }
            """
        id_m=random.randrange(1 << 30, 1 << 31)
        id_d=random.randrange(1 << 30, 1 << 31)
        self.model=genanki.Model(
            id_m, "default", fields=[ {'name': 'Question'},
            {'name': 'Answer'},{'name': 'Topic'},
             ],
            templates=[
                {
                    'name': 'Card 1',
                    'qfmt': """
                    <div class="topic-box">{{Topic}}</div>
                    <div class="question">{{Question}}</div>
                    """,
                    'afmt': """
                    {{FrontSide}}
                    <hr id="answer">
                    <div class="answer">{{Answer}}</div>
                    """,
                },
            ],
            css=style
        )
        self.deck=genanki.Deck(id_d,deck_name)
    def add_fields(self,cards: list[dict]):
        for card in cards:
            node=genanki.Note(model=self.model,fields=[card["front"],card["back"],card["topic"]])
            self.deck.add_note(node)

    def safe_tofile(self,path:Path):
        genanki.Package(self.deck).write_to_file(path/f"{self.deckname.strip()}.apkg")


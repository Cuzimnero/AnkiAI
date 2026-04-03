import logging
import re

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


def gen_vector(cards: list[dict], model: SentenceTransformer, logger: logging.Logger):
    fronts = [card.get("front") for card in cards]
    try:
        embeddings = model.encode([re.sub(r'[^\w\s]', '', f.lower()) for f in fronts])
        return embeddings
    except Exception as e:
        logger.error(f"{e}")
        return []


def delete_dupes(cards: list[dict], model: SentenceTransformer, logger: logging.Logger):
    deleting_value = 0.80
    if cards:
        if len(cards) > 200:
            logger.info("More than 200 cards, dropping similarity threshold to 0.65")
            deleting_value = 0.65
        elif len(cards) > 100:
            logger.info("More than 100 cards, dropping similarity threshold to 0.7")
            deleting_value = 0.7

        embeddings = gen_vector(cards, model, logger)
        indices_delete = set()
        sim_Matrix = cosine_similarity(embeddings)
        for i in range(0, sim_Matrix.__len__()):
            for a in range(i + 1, sim_Matrix.__len__()):
                if sim_Matrix[i][a] >= deleting_value:
                    indices_delete.add(a)
        
        logger.info(f"Deleting {len(indices_delete)} duplicate cards.")
        return [card for i, card in enumerate(cards) if i not in indices_delete]
    return cards

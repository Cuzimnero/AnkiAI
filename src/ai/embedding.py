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
            print("____________________________________________")
            print("TOO MANY CARDS dropping threshold VALUE >200 Cards")
            print("____________________________________________")
            logger.info("____________________________________________")
            logger.info("TOO MANY CARDS dropping threshold VALUE >200 Cards")
            logger.info("____________________________________________")
            deleting_value = 0.65
        elif len(cards) > 100:
            print("____________________________________________")
            print("TOO MANY CARDS dropping threshold VALUE >100 Cards")
            print("____________________________________________")
            logger.info("____________________________________________")
            logger.info("TOO MANY CARDS dropping threshold VALUE >100 Cards")
            logger.info("____________________________________________")
            deleting_value = 0.7

        embeddings = gen_vector(cards, model, logger)
        indices_delete = set()
        sim_Matrix = cosine_similarity(embeddings)
        for i in range(0, sim_Matrix.__len__()):
            for a in range(i + 1, sim_Matrix.__len__()):
                if sim_Matrix[i][a] >= deleting_value:
                    indices_delete.add(a)
        return [card for i, card in enumerate(cards) if i not in indices_delete]
    return cards

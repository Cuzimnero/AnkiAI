import re

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


def gen_vector(cards: list[dict]):
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    fronts = [card.get("front") for card in cards]
    embeddings = model.encode([re.sub(r'[^\w\s]', '', f.lower()) for f in fronts])
    return embeddings


def delete_dupes(cards: list[dict]):
    deleting_value = 0.80
    if cards:
        if len(cards) > 200:
            print("____________________________________________")
            print("TOO MANY CARDS dropping threshold VALUE >200 Cards")
            print("____________________________________________")
            deleting_value = 0.6
        elif len(cards) > 100:
            print("____________________________________________")
            print("TOO MANY CARDS dropping threshold VALUE >100 Cards")
            print("____________________________________________")
            deleting_value = 0.7

        embeddings = gen_vector(cards)
        indices_delete = set()
        sim_Matrix = cosine_similarity(embeddings)
        for i in range(0, sim_Matrix.__len__()):
            for a in range(i + 1, sim_Matrix.__len__()):
                if sim_Matrix[i][a] >= deleting_value:
                    indices_delete.add(a)
        return [card for i, card in enumerate(cards) if i not in indices_delete]
    return cards

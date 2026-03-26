
from sentence_transformers import SentenceTransformer
import torch
import torch.nn.functional as F
from sklearn.metrics.pairwise import cosine_similarity
import re


def gen_vector(cards:list[dict]):
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    fronts=[card.get("front") for card in cards]
    embeddings= model.encode([re.sub(r'[^\w\s]', '', f.lower()) for f in fronts])
    return embeddings

def delete_dupes(cards:list[dict]):
    embeddings=gen_vector(cards)
    indices_delete=set()
    sim_Matrix=cosine_similarity(embeddings)
    for i in range(0,sim_Matrix.__len__()):
        for a in range(i+1,sim_Matrix.__len__()):
            if sim_Matrix[i][a]>=0.80:
                indices_delete.add(a)
    return [card for i, card in enumerate(cards) if i not in indices_delete]


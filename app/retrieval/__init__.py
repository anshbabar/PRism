"""Regression retrieval: embeddings + similarity search over prior analyses.

``embeddings.py`` turns text into vectors (offline hashing provider by default,
real providers plug in later). ``store.py`` finds the most similar prior PR
analyses in the same repository via cosine similarity.
"""

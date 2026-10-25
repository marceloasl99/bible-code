"""Null models, frequency expectations, and entropy metrics."""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict

from .els import sequence_space


def entropy_metrics(text: str, max_order: int = 3) -> dict[str, float]:
    """H0 and conditional entropy H(X_i | previous r symbols), in bits per symbol."""
    if not text:
        raise ValueError("corpus is empty")
    result = {}
    n = len(text)
    counts = Counter(text)
    result["H0"] = -sum((c / n) * math.log2(c / n) for c in counts.values())
    for order in range(1, max_order + 1):
        if n <= order:
            break
        contexts: dict[str, Counter[str]] = defaultdict(Counter)
        for i in range(order, n):
            contexts[text[i - order:i]][text[i]] += 1
        total = n - order
        h = 0.0
        for next_counts in contexts.values():
            context_total = sum(next_counts.values())
            h_context = -sum((c / context_total) * math.log2(c / context_total) for c in next_counts.values())
            h += (context_total / total) * h_context
        result[f"H{order}"] = h
    return result


def expected_hits_iid(text: str, word: str, max_skip: int, direction: str = "both") -> float:
    """Exact expectation under an IID model with empirical per-symbol probabilities."""
    if not text or not word:
        return 0.0
    freq = Counter(text)
    n = len(text)
    p = math.prod(freq[ch] / n for ch in word)
    if len(word) == 1:
        return n * p
    return sequence_space(n, len(word), max_skip, direction) * p


def poisson_at_least_one(lam: float) -> float:
    return -math.expm1(-lam)


def corrected_p(p: float, tests: int) -> float:
    if not 0 <= p <= 1 or tests < 1:
        raise ValueError("p must be in [0,1] and tests>=1")
    return min(1.0, p * tests)


def bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg adjustment; preserve input order."""
    m = len(p_values)
    if not m:
        return []
    ordered = sorted(enumerate(p_values), key=lambda pair: pair[1])
    adjusted = [1.0] * m
    running = 1.0
    for rank0 in range(m - 1, -1, -1):
        original, p = ordered[rank0]
        rank = rank0 + 1
        running = min(running, p * m / rank)
        adjusted[original] = min(1.0, running)
    return adjusted


def resample(text: str, method: str, rng: random.Random, block_size: int = 8) -> str:
    """Controls: iid_perm preserves frequencies, block_perm preserves blocks, Markov approximates transitions."""
    n = len(text)
    if method == "iid_perm":
        chars = list(text)
        rng.shuffle(chars)
        return "".join(chars)
    if method == "block_perm":
        if block_size < 1:
            raise ValueError("block_size must be >=1")
        blocks = [text[i:i + block_size] for i in range(0, n, block_size)]
        rng.shuffle(blocks)
        return "".join(blocks)
    if method == "markov":
        if not text:
            return text
        transitions: dict[str, list[str]] = defaultdict(list)
        for a, b in zip(text, text[1:]):
            transitions[a].append(b)
        symbols = list(transitions)
        out = [text[0]]
        for _ in range(n - 1):
            choices = transitions.get(out[-1])
            out.append(rng.choice(choices) if choices else rng.choice(symbols))
        return "".join(out)
    raise ValueError(f"unknown null model: {method}")

"""Search ELS without wrap-around and count exactly within explicit skip limits."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from typing import Callable


@dataclass
class SearchResult:
    count: int
    locations: list[tuple[int, int]]  # (zero-based start index, signed skip)


def sequence_space(n: int, k: int, max_skip: int, direction: str = "both") -> int:
    """Count valid (start, skip) pairs for k>=2 without wrap-around."""
    if n < 0 or k < 1 or max_skip < 1:
        raise ValueError("n>=0, k>=1, and max_skip>=1 are required")
    if k == 1:
        return n * (2 if direction == "both" else 1)
    d = min(max_skip, (n - 1) // (k - 1)) if n else 0
    one_direction = d * n - (k - 1) * d * (d + 1) // 2
    return one_direction * (2 if direction == "both" else 1)


def find_els(
    text: str,
    word: str,
    max_skip: int = 1000,
    direction: str = "both",
    max_locations: int = 1000,
    progress: Callable[[int, int, int], None] | None = None,
    min_skip: int = 1,
) -> SearchResult:
    """Search for a literal target at skips 1..max_skip; directions: both/forward/backward."""
    if not word:
        raise ValueError("Target cannot be empty")
    if max_skip < 1 or min_skip < 1 or direction not in {"both", "forward", "backward"}:
        raise ValueError("max_skip must be >=1; direction must be both/forward/backward")
    n, k = len(text), len(word)
    if k == 1:
        hits = [i for i, ch in enumerate(text) if ch == word]
        return SearchResult(len(hits), [(i, 1) for i in hits[:max_locations]])
    limit = min(max_skip, max(0, (n - 1) // (k - 1)))
    first_skip = max(1, min_skip)
    if limit < first_skip:
        return SearchResult(0, [])
    positions = [i for i, ch in enumerate(text) if ch == word[0]]
    positive = range(first_skip, limit + 1)
    negative = range(-first_skip, -limit - 1, -1)
    steps = positive if direction == "forward" else negative if direction == "backward" else chain(positive, negative)
    total_steps = (limit - first_skip + 1) * (2 if direction == "both" else 1)
    count, locations = 0, []
    completed = 0
    for step in steps:
        low = 0 if step > 0 else (k - 1) * -step
        high = n - 1 - (k - 1) * step if step > 0 else n - 1
        for start in positions:
            if start < low or start > high:
                continue
            if all(text[start + j * step] == word[j] for j in range(1, k)):
                count += 1
                if len(locations) < max_locations:
                    locations.append((start, step))
        completed += 1
        if progress is not None:
            progress(completed, total_steps, step)
    return SearchResult(count, locations)


def extract(text: str, start: int, step: int, length: int) -> str:
    """Extract an ELS after validating all boundaries."""
    indices = [start + j * step for j in range(length)]
    if any(i < 0 or i >= len(text) for i in indices):
        raise ValueError("Sequence exceeds corpus boundaries")
    return "".join(text[i] for i in indices)

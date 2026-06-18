"""Local route optimizer: nearest-neighbor seed + 2-opt improvement.

Pure function over a cost matrix (durations or distances) — no external calls,
so "dynamic route optimization" works with no paid routing key. Open-path TSP
(start fixed, no forced return) suited to a day's sequence of stops.
"""
from __future__ import annotations

Matrix = list[list[float]]


def path_cost(tour: list[int], cost: Matrix) -> float:
    return sum(cost[tour[k]][tour[k + 1]] for k in range(len(tour) - 1))


def _nearest_neighbor(cost: Matrix, start: int) -> list[int]:
    n = len(cost)
    unvisited = set(range(n)) - {start}
    tour = [start]
    cur = start
    while unvisited:
        nxt = min(unvisited, key=lambda j: cost[cur][j])
        tour.append(nxt)
        unvisited.remove(nxt)
        cur = nxt
    return tour


def _two_opt(tour: list[int], cost: Matrix) -> list[int]:
    n = len(tour)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                a, b = tour[i - 1], tour[i]
                c, d = tour[j], tour[j + 1] if j + 1 < n else None
                before = cost[a][b] + (cost[c][d] if d is not None else 0.0)
                after = cost[a][c] + (cost[b][d] if d is not None else 0.0)
                if after + 1e-9 < before:
                    tour[i : j + 1] = reversed(tour[i : j + 1])
                    improved = True
    return tour


def optimize_order(cost: Matrix, start: int = 0) -> list[int]:
    """Return the visit order (indices) minimizing total path cost."""
    n = len(cost)
    if n <= 2:
        return list(range(n))
    tour = _nearest_neighbor(cost, start)
    return _two_opt(tour, cost)

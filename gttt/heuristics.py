"""Heuristic evaluation for generalized Tic-Tac-Toe.

Author: Kamal Ahmadov
"""

from __future__ import annotations

from dataclasses import dataclass

from gttt.board import Board
from gttt.models import Move


@dataclass(frozen=True)
class HeuristicWeights:
    """Tuneable constants for board evaluation and move ordering."""

    terminal_score: int = 10_000_000
    window_base: int = 10
    own_longest_weight: int = 500
    opp_longest_weight: int = 550
    center_weight: int = 20
    center_decay: int = 2
    own_pattern_scale: int = 100
    opp_pattern_scale: int = 120


DEFAULT_WEIGHTS = HeuristicWeights()


def positional_bonus(board_size: int, move: Move, weights: HeuristicWeights = DEFAULT_WEIGHTS) -> int:
    """Score center proximity bonus for a candidate move."""
    # Favor central control with linear Manhattan decay from board center.
    center = (board_size - 1) / 2.0
    manhattan_distance = abs(move.x - center) + abs(move.y - center)
    return int(weights.center_weight - weights.center_decay * manhattan_distance)


def score_window(
    window: list[str],
    my_symbol: str,
    opp_symbol: str,
    target: int,
    weights: HeuristicWeights = DEFAULT_WEIGHTS,
) -> int:
    """Score one contiguous target-length window for both players."""
    my_count = window.count(my_symbol)
    opp_count = window.count(opp_symbol)

    if my_count > 0 and opp_count > 0:
        # Mixed windows cannot produce a direct line for either side.
        return 0
    if my_count == target:
        return weights.terminal_score // 10
    if opp_count == target:
        return -(weights.terminal_score // 10)
    if my_count > 0:
        return weights.window_base**my_count
    if opp_count > 0:
        return -(weights.window_base**opp_count)
    # Small non-zero baseline keeps empty windows from being completely neutral.
    return 1


def evaluate_board(
    board: Board,
    target: int,
    my_symbol: str,
    opp_symbol: str,
    depth_remaining: int = 0,
    weights: HeuristicWeights = DEFAULT_WEIGHTS,
) -> int:
    """Compute a static board score from the perspective of ``my_symbol``."""
    if board.has_winner(my_symbol, target):
        return weights.terminal_score + depth_remaining
    if board.has_winner(opp_symbol, target):
        return -weights.terminal_score - depth_remaining
    if board.is_full():
        return 0

    score = 0
    for window in board.windows(target):
        score += score_window(window, my_symbol, opp_symbol, target, weights)

    # Reward own line growth and penalize opponent growth asymmetrically.
    score += weights.own_longest_weight * board.max_consecutive(my_symbol)
    score -= weights.opp_longest_weight * board.max_consecutive(opp_symbol)

    # Pattern-aware threat scoring helps convert attacking pressure into wins.
    own_pattern_score = _threat_pattern_score(board, my_symbol, target, weights)
    opp_pattern_score = _threat_pattern_score(board, opp_symbol, target, weights)
    score += (weights.own_pattern_scale * own_pattern_score) // 100
    score -= (weights.opp_pattern_scale * opp_pattern_score) // 100

    for y in range(board.size):
        for x in range(board.size):
            symbol = board.grid[y][x]
            bonus = positional_bonus(board.size, Move(x=x, y=y), weights)
            if symbol == my_symbol:
                score += bonus
            elif symbol == opp_symbol:
                score -= bonus

    return score


def _threat_pattern_score(
    board: Board,
    symbol: str,
    target: int,
    weights: HeuristicWeights,
) -> int:
    """Evaluate open/semi-open contiguous runs for one symbol."""
    score = 0
    for line in _board_lines(board):
        score += _line_threat_score(line, symbol, target, weights)
    return score


def _board_lines(board: Board) -> list[str]:
    """Collect rows, columns, and both diagonal directions as strings."""
    lines: list[str] = []
    size = board.size

    for y in range(size):
        lines.append("".join(board.grid[y]))

    for x in range(size):
        lines.append("".join(board.grid[y][x] for y in range(size)))

    for start_x in range(size):
        x = start_x
        y = 0
        diagonal: list[str] = []
        while x < size and y < size:
            diagonal.append(board.grid[y][x])
            x += 1
            y += 1
        lines.append("".join(diagonal))

    for start_y in range(1, size):
        x = 0
        y = start_y
        diagonal = []
        while x < size and y < size:
            diagonal.append(board.grid[y][x])
            x += 1
            y += 1
        lines.append("".join(diagonal))

    for start_x in range(size):
        x = start_x
        y = 0
        diagonal = []
        while x >= 0 and y < size:
            diagonal.append(board.grid[y][x])
            x -= 1
            y += 1
        lines.append("".join(diagonal))

    for start_y in range(1, size):
        x = size - 1
        y = start_y
        diagonal = []
        while x >= 0 and y < size:
            diagonal.append(board.grid[y][x])
            x -= 1
            y += 1
        lines.append("".join(diagonal))

    return lines


def _line_threat_score(
    line: str,
    symbol: str,
    target: int,
    weights: HeuristicWeights,
) -> int:
    """Score contiguous runs in a single line, weighted by open ends."""
    score = 0
    index = 0
    length = len(line)

    while index < length:
        if line[index] != symbol:
            index += 1
            continue

        run_start = index
        while index < length and line[index] == symbol:
            index += 1
        run_end = index

        run_length = run_end - run_start
        left_open = run_start > 0 and line[run_start - 1] == "-"
        right_open = run_end < length and line[run_end] == "-"
        open_ends = int(left_open) + int(right_open)
        score += _run_potential_score(run_length, open_ends, target, weights)

    return score


def _run_potential_score(
    run_length: int,
    open_ends: int,
    target: int,
    weights: HeuristicWeights,
) -> int:
    """Map a contiguous run and openness to a tactical potential score."""
    if open_ends == 0:
        return 0
    if run_length >= target:
        return weights.terminal_score

    stones_needed = target - run_length

    # Strong forcing ladders (open-ended threats) should dominate eval.
    if stones_needed == 1:
        if open_ends == 2:
            return weights.terminal_score // 6
        return weights.terminal_score // 18
    if stones_needed == 2:
        if open_ends == 2:
            return weights.terminal_score // 50
        return weights.terminal_score // 140
    if stones_needed == 3:
        if open_ends == 2:
            return weights.terminal_score // 600
        return weights.terminal_score // 1600
    if stones_needed == 4:
        if open_ends == 2:
            return weights.terminal_score // 4000
        return weights.terminal_score // 8000
    return 0

"""Heuristic evaluation for generalized Tic-Tac-Toe."""

from __future__ import annotations

from dataclasses import dataclass

from gttt.board import Board
from gttt.models import Move


@dataclass(frozen=True)
class HeuristicWeights:
    terminal_score: int = 10_000_000
    window_base: int = 10
    own_longest_weight: int = 500
    opp_longest_weight: int = 550
    center_weight: int = 20
    center_decay: int = 2


DEFAULT_WEIGHTS = HeuristicWeights()


def positional_bonus(board_size: int, move: Move, weights: HeuristicWeights = DEFAULT_WEIGHTS) -> int:
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
    my_count = window.count(my_symbol)
    opp_count = window.count(opp_symbol)

    if my_count > 0 and opp_count > 0:
        return 0
    if my_count == target:
        return weights.terminal_score // 10
    if opp_count == target:
        return -(weights.terminal_score // 10)
    if my_count > 0:
        return weights.window_base**my_count
    if opp_count > 0:
        return -(weights.window_base**opp_count)
    return 1


def evaluate_board(
    board: Board,
    target: int,
    my_symbol: str,
    opp_symbol: str,
    depth_remaining: int = 0,
    weights: HeuristicWeights = DEFAULT_WEIGHTS,
) -> int:
    if board.has_winner(my_symbol, target):
        return weights.terminal_score + depth_remaining
    if board.has_winner(opp_symbol, target):
        return -weights.terminal_score - depth_remaining
    if board.is_full():
        return 0

    score = 0
    for window in board.windows(target):
        score += score_window(window, my_symbol, opp_symbol, target, weights)

    score += weights.own_longest_weight * board.max_consecutive(my_symbol)
    score -= weights.opp_longest_weight * board.max_consecutive(opp_symbol)

    for y in range(board.size):
        for x in range(board.size):
            symbol = board.grid[y][x]
            bonus = positional_bonus(board.size, Move(x=x, y=y), weights)
            if symbol == my_symbol:
                score += bonus
            elif symbol == opp_symbol:
                score -= bonus

    return score

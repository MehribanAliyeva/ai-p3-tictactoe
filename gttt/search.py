"""Alpha-beta search with pruning and move ordering."""

from __future__ import annotations

import random
from typing import Optional

from gttt.board import Board
from gttt.errors import SearchError
from gttt.heuristics import DEFAULT_WEIGHTS, HeuristicWeights, evaluate_board, positional_bonus
from gttt.models import Move, SearchConfig


class AlphaBetaSearcher:
    def __init__(
        self,
        board: Board,
        target: int,
        my_symbol: str,
        opp_symbol: str,
        search_config: SearchConfig,
        weights: HeuristicWeights = DEFAULT_WEIGHTS,
    ) -> None:
        self.board = board
        self.target = target
        self.my_symbol = my_symbol
        self.opp_symbol = opp_symbol
        self.cfg = search_config
        self.weights = weights
        self._rng = random.Random()

    def choose_move(self) -> Move:
        legal_moves = self.board.candidate_moves(self.cfg.neighbor_radius)
        if not legal_moves:
            raise SearchError("No legal moves are available")

        # Immediate tactical win.
        for move in legal_moves:
            self.board.place(move, self.my_symbol)
            is_win = self.board.has_winner(self.my_symbol, self.target)
            self.board.clear(move)
            if is_win:
                return move

        # Immediate tactical block.
        for move in legal_moves:
            self.board.place(move, self.opp_symbol)
            is_loss = self.board.has_winner(self.opp_symbol, self.target)
            self.board.clear(move)
            if is_loss:
                return move

        _, best_move = self._minimax(
            depth=self.cfg.depth,
            alpha=-(10**18),
            beta=10**18,
            maximizing=True,
        )
        return best_move or legal_moves[0]

    def _terminal_score(self, depth: int) -> Optional[int]:
        if self.board.has_winner(self.my_symbol, self.target):
            return self.weights.terminal_score + depth
        if self.board.has_winner(self.opp_symbol, self.target):
            return -self.weights.terminal_score - depth
        if self.board.is_full():
            return 0
        return None

    def _ordered_moves(self, symbol: str) -> list[Move]:
        candidates = self.board.candidate_moves(self.cfg.neighbor_radius)
        scored: list[tuple[float, Move]] = []

        for move in candidates:
            self.board.place(move, symbol)
            score = evaluate_board(
                board=self.board,
                target=self.target,
                my_symbol=self.my_symbol,
                opp_symbol=self.opp_symbol,
                weights=self.weights,
            )
            score += positional_bonus(self.board.size, move, self.weights)
            self.board.clear(move)
            if self.cfg.random_tie_break:
                # Tiny jitter only to break score ties and reduce deterministic openings.
                score += self._rng.uniform(-1e-3, 1e-3)
            scored.append((score, move))

        reverse = symbol == self.my_symbol
        scored.sort(key=lambda item: item[0], reverse=reverse)
        return [move for _, move in scored[: self.cfg.top_k_moves]]

    def _minimax(
        self,
        depth: int,
        alpha: int,
        beta: int,
        maximizing: bool,
    ) -> tuple[int, Optional[Move]]:
        terminal = self._terminal_score(depth)
        if terminal is not None:
            return terminal, None
        if depth == 0:
            return (
                evaluate_board(
                    board=self.board,
                    target=self.target,
                    my_symbol=self.my_symbol,
                    opp_symbol=self.opp_symbol,
                    depth_remaining=depth,
                    weights=self.weights,
                ),
                None,
            )

        if maximizing:
            best_score = -(10**18)
            best_move: Optional[Move] = None
            for move in self._ordered_moves(self.my_symbol):
                self.board.place(move, self.my_symbol)
                score, _ = self._minimax(depth - 1, alpha, beta, False)
                self.board.clear(move)

                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    break
            return best_score, best_move

        best_score = 10**18
        best_move = None
        for move in self._ordered_moves(self.opp_symbol):
            self.board.place(move, self.opp_symbol)
            score, _ = self._minimax(depth - 1, alpha, beta, True)
            self.board.clear(move)

            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return best_score, best_move

"""Alpha-beta search with pruning and move ordering.

Author: Kamal Ahmadov, Mehriban Aliyeva
"""

from __future__ import annotations

import random
import time
from typing import Optional

from gttt.board import Board
from gttt.errors import SearchError
from gttt.heuristics import DEFAULT_WEIGHTS, HeuristicWeights, evaluate_board, positional_bonus
from gttt.models import Move, SearchConfig


class _SearchTimeout(Exception):
    """Internal control-flow exception for time-bounded search."""


class AlphaBetaSearcher:
    """Alpha-beta searcher with transposition caching and time controls."""

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
        self._deadline: float | None = None
        self._transposition: dict[tuple[str, int, bool], tuple[int, Optional[Move]]] = {}
        self.transposition_hits = 0

    @property
    def transposition_size(self) -> int:
        """Expose number of cached search states for diagnostics/tests."""
        return len(self._transposition)

    def _board_key(self) -> str:
        return self.board.to_ascii()

    def _check_timeout(self) -> None:
        if self._deadline is None:
            return
        if time.monotonic() >= self._deadline:
            raise _SearchTimeout()

    def choose_move(self) -> Move:
        """Return the best legal move according to current search settings."""
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

        if self.cfg.max_time_ms is not None:
            # Use monotonic clock so deadline is immune to system time jumps.
            self._deadline = time.monotonic() + (self.cfg.max_time_ms / 1000.0)
        else:
            self._deadline = None

        # Always keep a legal answer in case timeout interrupts deeper search.
        fallback_move = legal_moves[0]

        if self.cfg.iterative_deepening:
            best_move = fallback_move
            # Iterative deepening returns progressively better moves under time pressure.
            for depth in range(1, self.cfg.depth + 1):
                try:
                    _, candidate = self._minimax(
                        depth=depth,
                        alpha=-(10**18),
                        beta=10**18,
                        maximizing=True,
                    )
                except _SearchTimeout:
                    break
                if candidate is not None:
                    best_move = candidate
            return best_move

        try:
            _, best_move = self._minimax(
                depth=self.cfg.depth,
                alpha=-(10**18),
                beta=10**18,
                maximizing=True,
            )
        except _SearchTimeout:
            return fallback_move
        return best_move or fallback_move

    def _terminal_score(self, depth: int) -> Optional[int]:
        """Return terminal utility when game is finished, otherwise ``None``."""
        if self.board.has_winner(self.my_symbol, self.target):
            return self.weights.terminal_score + depth
        if self.board.has_winner(self.opp_symbol, self.target):
            return -self.weights.terminal_score - depth
        if self.board.is_full():
            return 0
        return None

    def _ordered_moves(self, symbol: str) -> list[Move]:
        """Generate candidate moves ordered by one-ply heuristic quality."""
        candidates = self.board.candidate_moves(self.cfg.neighbor_radius)
        scored: list[tuple[float, Move]] = []

        for move in candidates:
            # One-ply static scoring gives alpha-beta better pruning opportunities.
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
        """Depth-limited alpha-beta recursion returning score and best move."""
        self._check_timeout()

        # Depth and side-to-move are part of the key because values are depth-dependent.
        key = (self._board_key(), depth, maximizing)
        cached = self._transposition.get(key)
        if cached is not None:
            self.transposition_hits += 1
            return cached

        terminal = self._terminal_score(depth)
        if terminal is not None:
            result = (terminal, None)
            self._transposition[key] = result
            return result
        if depth == 0:
            result = (
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
            self._transposition[key] = result
            return result

        if maximizing:
            best_score = -(10**18)
            best_move: Optional[Move] = None
            for move in self._ordered_moves(self.my_symbol):
                self._check_timeout()
                self.board.place(move, self.my_symbol)
                score, _ = self._minimax(depth - 1, alpha, beta, False)
                self.board.clear(move)

                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    break
            result = (best_score, best_move)
            self._transposition[key] = result
            return result

        best_score = 10**18
        best_move = None
        for move in self._ordered_moves(self.opp_symbol):
            self._check_timeout()
            self.board.place(move, self.opp_symbol)
            score, _ = self._minimax(depth - 1, alpha, beta, True)
            self.board.clear(move)

            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        result = (best_score, best_move)
        self._transposition[key] = result
        return result

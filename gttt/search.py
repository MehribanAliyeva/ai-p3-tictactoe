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

    _HISTORY_ORDERING_WEIGHT = 64
    _QUIESCENCE_PLIES = 2

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
        self._history: dict[tuple[str, int, int], int] = {}
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
        immediate_wins = self._immediate_winning_moves(self.my_symbol, legal_moves)
        if immediate_wins:
            return immediate_wins[0]

        # Immediate tactical block.
        immediate_blocks = self._immediate_winning_moves(self.opp_symbol, legal_moves)
        if immediate_blocks:
            return immediate_blocks[0]

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
            return self._postprocess_root_choice(best_move, legal_moves)

        try:
            _, best_move = self._minimax(
                depth=self.cfg.depth,
                alpha=-(10**18),
                beta=10**18,
                maximizing=True,
            )
        except _SearchTimeout:
            return fallback_move
        return self._postprocess_root_choice(best_move or fallback_move, legal_moves)

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
        if not candidates:
            return []

        opponent_symbol = self.opp_symbol if symbol == self.my_symbol else self.my_symbol
        winning_moves = self._immediate_winning_moves(symbol, candidates)
        blocking_moves = self._immediate_winning_moves(opponent_symbol, candidates)
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

            # Threat-space inspired move ordering:
            # prioritize moves that create forcing threats and de-prioritize
            # moves that allow immediate opponent tactical wins.
            tactical_delta = self._forcing_tactical_delta(symbol)
            if symbol == self.my_symbol:
                score += tactical_delta
            else:
                score -= tactical_delta

            history_score = self._history.get((symbol, move.x, move.y), 0)
            if symbol == self.my_symbol:
                score += history_score * self._HISTORY_ORDERING_WEIGHT
            else:
                score -= history_score * self._HISTORY_ORDERING_WEIGHT

            self.board.clear(move)
            if self.cfg.random_tie_break:
                # Tiny jitter only to break score ties and reduce deterministic openings.
                score += self._rng.uniform(-1e-3, 1e-3)
            scored.append((score, move))

        reverse = symbol == self.my_symbol
        scored.sort(key=lambda item: item[0], reverse=reverse)

        ordered: list[Move] = []
        seen: set[tuple[int, int]] = set()

        # Tactical must-play moves are always kept, even beyond top_k pruning.
        for move in winning_moves + blocking_moves:
            key = (move.x, move.y)
            if key in seen:
                continue
            ordered.append(move)
            seen.add(key)

        for _, move in scored[: max(0, self.cfg.top_k_moves)]:
            key = (move.x, move.y)
            if key in seen:
                continue
            ordered.append(move)
            seen.add(key)

        if ordered:
            return ordered

        # Safety fallback for pathological configs such as top_k=0.
        return [scored[0][1]]

    def _immediate_winning_moves(self, symbol: str, candidates: list[Move]) -> list[Move]:
        """Return moves from ``candidates`` that win immediately for ``symbol``."""
        winning_moves: list[Move] = []
        for move in candidates:
            self.board.place(move, symbol)
            is_win = self.board.has_winner(symbol, self.target)
            self.board.clear(move)
            if is_win:
                winning_moves.append(move)
        return winning_moves

    def _forcing_tactical_delta(self, symbol: str) -> int:
        """Evaluate immediate tactical forcing potential after a hypothetical move.

        Positive values are good for ``symbol``:
        - two immediate wins next turn (double threat) is highly valuable
        - one immediate win next turn is strongly valuable
        - allowing opponent immediate wins is heavily penalized
        """
        opponent = self.opp_symbol if symbol == self.my_symbol else self.my_symbol
        next_candidates = self.board.candidate_moves(self.cfg.neighbor_radius)
        own_wins = len(self._immediate_winning_moves(symbol, next_candidates))
        opp_wins = len(self._immediate_winning_moves(opponent, next_candidates))

        own_bonus = self._forcing_bonus(own_wins)
        opp_bonus = self._forcing_bonus(opp_wins)
        return own_bonus - opp_bonus

    def _forcing_bonus(self, forcing_wins: int) -> int:
        """Map count of immediate winning continuations to an ordering bonus."""
        if forcing_wins >= 2:
            # Equivalent to creating a straight-four style fork.
            return self.weights.terminal_score // 3
        if forcing_wins == 1:
            return self.weights.terminal_score // 12
        return 0

    def _record_history_cutoff(self, symbol: str, move: Move, depth: int) -> None:
        """Update history heuristic for moves that caused alpha-beta cutoffs."""
        key = (symbol, move.x, move.y)
        self._history[key] = self._history.get(key, 0) + max(1, depth * depth)

    def _forcing_moves(self, symbol: str) -> list[Move]:
        """Return forcing moves: immediate wins and must-block defenses."""
        candidates = self.board.candidate_moves(self.cfg.neighbor_radius)
        if not candidates:
            return []
        opponent = self.opp_symbol if symbol == self.my_symbol else self.my_symbol
        winning_moves = self._immediate_winning_moves(symbol, candidates)
        blocking_moves = self._immediate_winning_moves(opponent, candidates)

        moves: list[Move] = []
        seen: set[tuple[int, int]] = set()
        for move in winning_moves + blocking_moves:
            key = (move.x, move.y)
            if key in seen:
                continue
            moves.append(move)
            seen.add(key)
        return moves

    def _quiescence(
        self,
        alpha: int,
        beta: int,
        maximizing: bool,
        plies_left: int,
    ) -> tuple[int, Optional[Move]]:
        """Extend search on forcing tactical moves to reduce horizon effects."""
        self._check_timeout()
        terminal = self._terminal_score(depth=0)
        if terminal is not None:
            return (terminal, None)

        stand_pat = evaluate_board(
            board=self.board,
            target=self.target,
            my_symbol=self.my_symbol,
            opp_symbol=self.opp_symbol,
            depth_remaining=0,
            weights=self.weights,
        )

        if plies_left <= 0:
            return (stand_pat, None)

        side_symbol = self.my_symbol if maximizing else self.opp_symbol
        forcing_moves = self._forcing_moves(side_symbol)
        if not forcing_moves:
            return (stand_pat, None)

        if maximizing:
            best_score = stand_pat
            best_move: Optional[Move] = None
            if best_score >= beta:
                return (best_score, None)
            alpha = max(alpha, best_score)

            for move in forcing_moves:
                self._check_timeout()
                self.board.place(move, side_symbol)
                score, _ = self._quiescence(alpha, beta, False, plies_left - 1)
                self.board.clear(move)

                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    self._record_history_cutoff(side_symbol, move, plies_left)
                    break
            return (best_score, best_move)

        best_score = stand_pat
        best_move = None
        if best_score <= alpha:
            return (best_score, None)
        beta = min(beta, best_score)

        for move in forcing_moves:
            self._check_timeout()
            self.board.place(move, side_symbol)
            score, _ = self._quiescence(alpha, beta, True, plies_left - 1)
            self.board.clear(move)

            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                self._record_history_cutoff(side_symbol, move, plies_left)
                break
        return (best_score, best_move)

    def _root_tactical_profile(self, move: Move) -> tuple[int, int, int]:
        """Return (opponent_immediate_wins, my_immediate_wins, static_score)."""
        self.board.place(move, self.my_symbol)
        candidates = self.board.candidate_moves(self.cfg.neighbor_radius)
        opponent_wins = len(self._immediate_winning_moves(self.opp_symbol, candidates))
        my_wins = len(self._immediate_winning_moves(self.my_symbol, candidates))
        static_score = evaluate_board(
            board=self.board,
            target=self.target,
            my_symbol=self.my_symbol,
            opp_symbol=self.opp_symbol,
            depth_remaining=0,
            weights=self.weights,
        )
        self.board.clear(move)
        return (opponent_wins, my_wins, static_score)

    def _postprocess_root_choice(self, preferred_move: Move, legal_moves: list[Move]) -> Move:
        """Conservative root override: safer and more forcing move when clearly better.

        The override only triggers when:
        - preferred move is tactically unsafe while safe alternatives exist, or
        - another safe move creates a double threat while preferred does not.
        """
        candidates = self._ordered_moves(self.my_symbol)
        if not candidates:
            candidates = legal_moves

        seen: set[tuple[int, int]] = set()
        deduped: list[Move] = []
        for move in [preferred_move] + candidates:
            key = (move.x, move.y)
            if key in seen:
                continue
            deduped.append(move)
            seen.add(key)

        preferred_profile = self._root_tactical_profile(preferred_move)
        best_safe_move = preferred_move
        best_safe_profile = preferred_profile

        for move in deduped:
            profile = self._root_tactical_profile(move)
            opp_wins, my_wins, static_score = profile
            if opp_wins != 0:
                continue

            best_opp, best_my, best_static = best_safe_profile
            if (
                my_wins > best_my
                or (my_wins == best_my and static_score > best_static)
            ):
                best_safe_move = move
                best_safe_profile = profile

        pref_opp, pref_my, _ = preferred_profile
        safe_opp, safe_my, _ = best_safe_profile

        if pref_opp > 0 and safe_opp == 0:
            return best_safe_move
        if safe_opp == 0 and safe_my >= 2 and pref_my < 2:
            return best_safe_move
        return preferred_move

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
            result = self._quiescence(
                alpha=alpha,
                beta=beta,
                maximizing=maximizing,
                plies_left=self._QUIESCENCE_PLIES,
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
                    self._record_history_cutoff(self.my_symbol, move, depth)
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
                self._record_history_cutoff(self.opp_symbol, move, depth)
                break
        result = (best_score, best_move)
        self._transposition[key] = result
        return result

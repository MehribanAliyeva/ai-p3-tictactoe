"""Typed models for API and search logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Credentials:
    user_id: str
    api_key: str
    base_url: str
    include_authorization_header: bool = True


@dataclass(frozen=True)
class Move:
    x: int
    y: int

    @classmethod
    def from_text(cls, value: str) -> "Move":
        left, right = value.split(",")
        return cls(x=int(left.strip()), y=int(right.strip()))

    def to_text(self) -> str:
        return f"{self.x},{self.y}"


@dataclass(frozen=True)
class SearchConfig:
    depth: int = 3
    top_k_moves: int = 12
    neighbor_radius: int = 1
    random_tie_break: bool = False


@dataclass(frozen=True)
class GameDetails:
    game_id: str
    game_type: str
    board_size: int
    target: int
    team1_id: str
    team1_name: str
    team2_id: str
    team2_name: str
    status: str
    moves: int
    turn_team_id: Optional[str] = None
    winner_team_id: Optional[str] = None
    seconds_per_move: Optional[int] = None


@dataclass(frozen=True)
class AutoMoveDecision:
    move: Move
    my_symbol: str
    opponent_symbol: str
    target: int

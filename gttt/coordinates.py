"""Coordinate conversion between internal board moves and API wire format."""

from __future__ import annotations

from gttt.constants import SERVER_COORDINATE_ORDER
from gttt.models import Move


def server_pair_to_move(first: int, second: int) -> Move:
    """Convert wire pair to internal move.

    Internal representation uses x,y where x is column and y is row.
    """
    if SERVER_COORDINATE_ORDER == "row_col":
        return Move(x=second, y=first)
    return Move(x=first, y=second)


def move_to_server_pair(move: Move) -> tuple[int, int]:
    """Convert internal move to wire pair."""
    if SERVER_COORDINATE_ORDER == "row_col":
        return (move.y, move.x)
    return (move.x, move.y)


def server_text_to_move(value: str) -> Move:
    left, right = value.split(",", 1)
    return server_pair_to_move(int(left.strip()), int(right.strip()))


def move_to_server_text(move: Move) -> str:
    first, second = move_to_server_pair(move)
    return f"{first},{second}"

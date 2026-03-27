"""Board representation and board-level operations."""

from __future__ import annotations

import math
from dataclasses import dataclass

from gttt.constants import EMPTY_SYMBOL
from gttt.errors import InvalidBoardError
from gttt.models import Move


@dataclass
class Board:
    """Mutable board with x,y coordinates mapped to grid[y][x]."""

    grid: list[list[str]]

    @classmethod
    def from_board_string(cls, board_text: str) -> "Board":
        raw_lines = [line.strip() for line in board_text.splitlines() if line.strip()]
        candidate_lines = ["".join(ch for ch in line if ch in {"X", "O", EMPTY_SYMBOL}) for line in raw_lines]
        candidate_lines = [line for line in candidate_lines if line]

        if candidate_lines and len(set(len(line) for line in candidate_lines)) == 1:
            size = len(candidate_lines)
            if len(candidate_lines[0]) != size:
                raise InvalidBoardError(
                    f"Board is not square: rows={size}, cols={len(candidate_lines[0])}"
                )
            return cls(grid=[list(line) for line in candidate_lines])

        compact = "".join(ch for ch in board_text if ch in {"X", "O", EMPTY_SYMBOL})
        size = int(math.isqrt(len(compact)))
        if size * size != len(compact) or size == 0:
            raise InvalidBoardError("Board text does not represent a square board")
        rows = [list(compact[i * size : (i + 1) * size]) for i in range(size)]
        return cls(grid=rows)

    @property
    def size(self) -> int:
        return len(self.grid)

    def clone(self) -> "Board":
        return Board([row[:] for row in self.grid])

    def to_ascii(self) -> str:
        return "\n".join("".join(row) for row in self.grid)

    def to_pretty(self) -> str:
        return "\n".join(" ".join(row) for row in self.grid)

    def in_bounds(self, move: Move) -> bool:
        return 0 <= move.x < self.size and 0 <= move.y < self.size

    def cell(self, move: Move) -> str:
        return self.grid[move.y][move.x]

    def place(self, move: Move, symbol: str) -> None:
        self.grid[move.y][move.x] = symbol

    def clear(self, move: Move) -> None:
        self.grid[move.y][move.x] = EMPTY_SYMBOL

    def empty_cells(self) -> list[Move]:
        return [
            Move(x=x, y=y)
            for y in range(self.size)
            for x in range(self.size)
            if self.grid[y][x] == EMPTY_SYMBOL
        ]

    def occupied_cells(self) -> list[Move]:
        return [
            Move(x=x, y=y)
            for y in range(self.size)
            for x in range(self.size)
            if self.grid[y][x] != EMPTY_SYMBOL
        ]

    def is_full(self) -> bool:
        return not self.empty_cells()

    def is_empty(self) -> bool:
        return not self.occupied_cells()

    def candidate_moves(self, radius: int) -> list[Move]:
        occupied = self.occupied_cells()
        if not occupied:
            center = self.size // 2
            center_move = Move(x=center, y=center)
            if self.cell(center_move) == EMPTY_SYMBOL:
                return [center_move]
            return self.empty_cells()

        candidates: set[tuple[int, int]] = set()
        for piece in occupied:
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    nx = piece.x + dx
                    ny = piece.y + dy
                    if not (0 <= nx < self.size and 0 <= ny < self.size):
                        continue
                    if self.grid[ny][nx] != EMPTY_SYMBOL:
                        continue
                    candidates.add((nx, ny))

        if not candidates:
            return self.empty_cells()
        return [Move(x=x, y=y) for (x, y) in sorted(candidates)]

    def max_consecutive(self, symbol: str) -> int:
        best = 0
        size = self.size

        for y in range(size):
            run = 0
            for x in range(size):
                run = run + 1 if self.grid[y][x] == symbol else 0
                best = max(best, run)

        for x in range(size):
            run = 0
            for y in range(size):
                run = run + 1 if self.grid[y][x] == symbol else 0
                best = max(best, run)

        for start_y in range(size):
            x = 0
            y = start_y
            run = 0
            while x < size and y < size:
                run = run + 1 if self.grid[y][x] == symbol else 0
                best = max(best, run)
                x += 1
                y += 1

        for start_x in range(1, size):
            x = start_x
            y = 0
            run = 0
            while x < size and y < size:
                run = run + 1 if self.grid[y][x] == symbol else 0
                best = max(best, run)
                x += 1
                y += 1

        for start_y in range(size):
            x = size - 1
            y = start_y
            run = 0
            while x >= 0 and y < size:
                run = run + 1 if self.grid[y][x] == symbol else 0
                best = max(best, run)
                x -= 1
                y += 1

        for start_x in range(size - 1):
            x = start_x
            y = 0
            run = 0
            while x >= 0 and y < size:
                run = run + 1 if self.grid[y][x] == symbol else 0
                best = max(best, run)
                x -= 1
                y += 1

        return best

    def has_winner(self, symbol: str, target: int) -> bool:
        return self.max_consecutive(symbol) >= target

    def windows(self, target: int) -> list[list[str]]:
        windows: list[list[str]] = []
        size = self.size

        for y in range(size):
            for x in range(size - target + 1):
                windows.append([self.grid[y][x + offset] for offset in range(target)])

        for x in range(size):
            for y in range(size - target + 1):
                windows.append([self.grid[y + offset][x] for offset in range(target)])

        for y in range(size - target + 1):
            for x in range(size - target + 1):
                windows.append([self.grid[y + offset][x + offset] for offset in range(target)])

        for y in range(size - target + 1):
            for x in range(target - 1, size):
                windows.append([self.grid[y + offset][x - offset] for offset in range(target)])

        return windows

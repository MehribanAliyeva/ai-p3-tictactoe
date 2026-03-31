"""Terminal rendering utilities for board visualization.

Author: Kamal Ahmadov, Mehriban Aliyeva
"""

from __future__ import annotations


def parse_board_rows(board_text: str) -> list[str]:
    """Extract clean board rows from raw board-string output."""
    rows = []
    for line in board_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Ignore separators/noise and keep only board symbols.
        filtered = "".join(ch for ch in stripped if ch in {"X", "O", "-"})
        if filtered:
            rows.append(filtered)
    return rows


def render_board(board_text: str, show_coords: bool = True) -> str:
    """Render a plain-text board, optionally with row/column labels."""
    rows = parse_board_rows(board_text)
    if not rows:
        return "<empty board>"

    size = len(rows[0])
    if any(len(row) != size for row in rows):
        return "<invalid board output>"

    cell_sep = " "
    row_label_width = max(2, len(str(len(rows) - 1))) if show_coords else 0

    output: list[str] = []

    if show_coords:
        # Build a compact coordinate guide for easier manual move validation.
        header_cells = cell_sep.join(f"{col:>{len(str(size - 1))}}" for col in range(size))
        output.append(" " * (row_label_width + 3) + header_cells)
        output.append(" " * (row_label_width + 1) + "+" + "-" * (len(header_cells) + 2))

    for row_idx, row in enumerate(rows):
        pretty_row = cell_sep.join(row)
        if show_coords:
            output.append(f"{row_idx:>{row_label_width}} | {pretty_row}")
        else:
            output.append(pretty_row)

    return "\n".join(output)

"""Game agent orchestration and symbol inference.

Author: Kamal Ahmadov
"""

from __future__ import annotations

from gttt.api_client import APIClient
from gttt.board import Board
from gttt.errors import SearchError
from gttt.models import AutoMoveDecision, GameDetails, Move, SearchConfig
from gttt.parsing import parse_symbol_by_team
from gttt.search import AlphaBetaSearcher


def infer_symbols(
    my_team_id: str,
    game_details: GameDetails,
    moves_payload: dict[str, object] | None,
    board: Board,
) -> tuple[str, str]:
    """Infer ``(my_symbol, opponent_symbol)`` from details, moves, or board state."""
    # Fast path when team ids are present and trustworthy in game details.
    if str(game_details.team1_id) == str(my_team_id):
        return "X", "O"
    if str(game_details.team2_id) == str(my_team_id):
        return "O", "X"

    if moves_payload:
        symbol_from_moves = parse_symbol_by_team(moves_payload, my_team_id)
        if symbol_from_moves == "X":
            return "X", "O"
        if symbol_from_moves == "O":
            return "O", "X"

    x_count = sum(cell == "X" for row in board.grid for cell in row)
    o_count = sum(cell == "O" for row in board.grid for cell in row)
    # Fallback heuristic: if counts are equal, next player is X; otherwise O.
    return ("X", "O") if x_count == o_count else ("O", "X")


def infer_target(target_override: int | None, game_details: GameDetails, board_size: int) -> int:
    """Determine connect-length target with safe fallback behavior."""
    # Priority: explicit override > server-reported target > board-size heuristic.
    if target_override is not None:
        return target_override
    if game_details.target > 0:
        return game_details.target
    return max(3, min(board_size, max(3, board_size // 2)))


def choose_auto_move(
    client: APIClient,
    game_id: str,
    team_id: str,
    search_config: SearchConfig,
    target_override: int | None = None,
    recent_moves_count: int = 20,
    verify_turn: bool = True,
) -> tuple[AutoMoveDecision, Board, GameDetails]:
    """Fetch game state, run search, and return the selected move decision."""
    details = client.get_game_details(game_id)
    board_text = client.get_board_string(game_id)
    board = Board.from_board_string(board_text)
    target = infer_target(target_override, details, board.size)

    my_symbol, opp_symbol = infer_symbols(team_id, details, None, board)
    if not details.team1_id and not details.team2_id and not board.is_empty():
        # Some responses omit team mapping; recover symbol from recent move history.
        try:
            moves_payload = client.get_moves_raw(game_id, max(recent_moves_count, 20))
            my_symbol, opp_symbol = infer_symbols(team_id, details, moves_payload, board)
        except Exception:
            pass

    if verify_turn and details.turn_team_id and str(details.turn_team_id) != str(team_id):
        raise SearchError(
            f"It is not team {team_id}'s turn (current turn team: {details.turn_team_id})."
        )

    searcher = AlphaBetaSearcher(
        board=board,
        target=target,
        my_symbol=my_symbol,
        opp_symbol=opp_symbol,
        search_config=search_config,
    )
    chosen_move = searcher.choose_move()

    return (
        AutoMoveDecision(
            move=Move(x=chosen_move.x, y=chosen_move.y),
            my_symbol=my_symbol,
            opponent_symbol=opp_symbol,
            target=target,
        ),
        board,
        details,
    )

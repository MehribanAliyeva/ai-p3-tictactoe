"""Command-line interface for API operations and auto-move execution.

Authors: Kamal Ahmadov, Murad Valiyev, Mehriban Aliyeva
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from typing import Any

from gttt.agent import choose_auto_move
from gttt.api_client import APIClient
from gttt.config import resolve_credentials
from gttt.constants import DEFAULT_BASE_URL
from gttt.coordinates import move_to_server_text, server_text_to_move
from gttt.models import SearchConfig
from gttt.parsing import board_map_to_json_dict, move_list_to_text


def build_parser() -> argparse.ArgumentParser:
    """Create the root argument parser and all supported subcommands."""
    parser = argparse.ArgumentParser(description="Generalized Tic-Tac-Toe API CLI")
    parser.add_argument("--user-id")
    parser.add_argument("--api-key")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--no-authorization-header", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)

    command = sub.add_parser("create-team")
    command.add_argument("--name", required=True)

    command = sub.add_parser("add-member")
    command.add_argument("--team-id", required=True)
    command.add_argument("--member-user-id", required=True)

    command = sub.add_parser("remove-member")
    command.add_argument("--team-id", required=True)
    command.add_argument("--member-user-id", required=True)

    command = sub.add_parser("team-members")
    command.add_argument("--team-id", required=True)

    sub.add_parser("my-teams")

    command = sub.add_parser("create-game")
    command.add_argument("--team1", required=True)
    command.add_argument("--team2", required=True)
    command.add_argument("--board-size", type=int, required=True)
    command.add_argument("--target", type=int, required=True)
    command.add_argument("--auto-play", action="store_true")
    command.add_argument("--my-team-id")
    command.add_argument("--depth", type=int, default=3)
    command.add_argument("--top-k-moves", type=int, default=12)
    command.add_argument("--neighbor-radius", type=int, default=1)
    command.add_argument("--recent-moves-count", type=int, default=20)
    command.add_argument("--no-turn-check", action="store_true")
    command.add_argument("--poll-seconds", type=float, default=2.0)
    command.add_argument("--max-seconds", type=float, default=3600.0)
    command.add_argument("--random-tie-break", action="store_true")
    command.add_argument("--max-time-ms", type=int)
    command.add_argument("--no-iterative-deepening", action="store_true")

    command = sub.add_parser("join-game")
    command.add_argument("--game-id", required=True)
    command.add_argument("--team-id", required=True)
    command.add_argument("--auto-play", action="store_true")
    command.add_argument("--depth", type=int, default=3)
    command.add_argument("--top-k-moves", type=int, default=12)
    command.add_argument("--neighbor-radius", type=int, default=1)
    command.add_argument("--recent-moves-count", type=int, default=20)
    command.add_argument("--no-turn-check", action="store_true")
    command.add_argument("--poll-seconds", type=float, default=2.0)
    command.add_argument("--max-seconds", type=float, default=3600.0)
    command.add_argument("--random-tie-break", action="store_true")
    command.add_argument("--max-time-ms", type=int)
    command.add_argument("--no-iterative-deepening", action="store_true")

    command = sub.add_parser("my-games")
    command.add_argument("--open-only", action="store_true")

    command = sub.add_parser("game-details")
    command.add_argument("--game-id", required=True)

    command = sub.add_parser("board-string")
    command.add_argument("--game-id", required=True)

    command = sub.add_parser("board-map")
    command.add_argument("--game-id", required=True)

    command = sub.add_parser("moves")
    command.add_argument("--game-id", required=True)
    command.add_argument("--count", type=int, default=20)

    command = sub.add_parser("make-move")
    command.add_argument("--game-id", required=True)
    command.add_argument("--team-id", required=True)
    command.add_argument("--move")
    command.add_argument("--auto", action="store_true")
    command.add_argument("--dry-run", action="store_true")
    command.add_argument("--target", type=int)
    command.add_argument("--depth", type=int, default=3)
    command.add_argument("--top-k-moves", type=int, default=12)
    command.add_argument("--neighbor-radius", type=int, default=1)
    command.add_argument("--random-tie-break", action="store_true")
    command.add_argument("--max-time-ms", type=int)
    command.add_argument("--no-iterative-deepening", action="store_true")
    command.add_argument("--recent-moves-count", type=int, default=20)
    command.add_argument("--no-turn-check", action="store_true")

    return parser


def _build_search_config(args: argparse.Namespace) -> SearchConfig:
    """Build search configuration from CLI flags."""
    return SearchConfig(
        depth=args.depth,
        top_k_moves=args.top_k_moves,
        neighbor_radius=args.neighbor_radius,
        random_tie_break=args.random_tie_break,
        max_time_ms=args.max_time_ms,
        iterative_deepening=not args.no_iterative_deepening,
    )


def _status_indicates_finished(status: str | None) -> bool:
    """Return True when status text semantically indicates game completion."""
    status_text = (status or "").lower()
    return any(word in status_text for word in ("won", "draw", "finished", "complete", "closed"))


def _should_ignore_autoplay_error(message: str) -> bool:
    """Return True for transient errors expected during poll-and-play races."""
    lowered = message.lower()
    ignored_phrases = (
        "not your turn",
        "not team",
        "turn team",
        "not the move of the team",
        "no moves",
        "game is not started",
        "invalid move",
        "already occupied",
    )
    return any(phrase in lowered for phrase in ignored_phrases)


def run_auto_play_loop(
    client: APIClient,
    game_id: str,
    team_id: str,
    *,
    depth: int,
    top_k_moves: int,
    neighbor_radius: int,
    target: int | None,
    recent_moves_count: int,
    verify_turn: bool,
    poll_seconds: float,
    max_seconds: float,
    random_tie_break: bool,
    max_time_ms: int | None,
    iterative_deepening: bool,
) -> dict[str, Any]:
    """Poll a game and play moves automatically until finish or timeout window."""
    deadline = time.time() + max_seconds
    moves_made: list[dict[str, Any]] = []
    last_seen_status: str | None = None
    check_interval = max(1, poll_seconds)

    while time.time() < deadline:
        details = client.get_game_details(game_id)
        last_seen_status = details.status

        # If board is full, treat game as tie before evaluating turn ownership.
        if isinstance(details.board_size, int) and isinstance(details.moves, int):
            board_capacity = details.board_size * details.board_size
            if board_capacity > 0 and details.moves >= board_capacity:
                return {
                    "code": "OK",
                    "gameId": game_id,
                    "status": details.status,
                    "winnerTeamId": details.winner_team_id,
                    "outcome": "tie",
                    "movesMade": moves_made,
                    "message": (
                        f"Game finished as tie: board is full "
                        f"({details.moves}/{board_capacity} moves)."
                    ),
                }

        is_my_turn = str(details.turn_team_id or "") == team_id

        if str(details.turn_team_id or "") == "-1":
            winner_team_id = str(details.winner_team_id or "")
            if winner_team_id and winner_team_id != "-1":
                outcome = "win" if winner_team_id == team_id else "loss"
                message = f"Game finished. Winner team: {winner_team_id}. Outcome: {outcome}."
            else:
                outcome = "draw"
                message = "Game finished with no winner (draw)."
            return {
                "code": "OK",
                "gameId": game_id,
                "status": details.status,
                "winnerTeamId": details.winner_team_id,
                "outcome": outcome,
                "movesMade": moves_made,
                "message": message,
            }

        if _status_indicates_finished(details.status):
            return {
                "code": "OK",
                "gameId": game_id,
                "status": details.status,
                "movesMade": moves_made,
                "message": "Game finished during auto-play window.",
            }

        # API enforces strict turn ownership, so we only attempt when it is our turn.
        if not is_my_turn:
            time.sleep(check_interval)
            continue
            
        try:
            decision, board, details = choose_auto_move(
                client=client,
                game_id=game_id,
                team_id=team_id,
                search_config=SearchConfig(
                    depth=depth,
                    top_k_moves=top_k_moves,
                    neighbor_radius=neighbor_radius,
                    random_tie_break=random_tie_break,
                    max_time_ms=max_time_ms,
                    iterative_deepening=iterative_deepening,
                ),
                target_override=target,
                recent_moves_count=recent_moves_count,
                # Optional redundant turn verification for parity with one-shot auto mode.
                # Race-condition failures are safely retried by the polling loop.
                verify_turn=verify_turn,
            )
            move_id = client.make_move(game_id, team_id, decision.move)
            moves_made.append(
                {
                    "moveId": move_id,
                    "move": move_to_server_text(decision.move),
                    "mySymbol": decision.my_symbol,
                    "target": decision.target,
                }
            )
        except Exception as exc:
            # Ignore transient states from race conditions and keep polling.
            if _should_ignore_autoplay_error(str(exc)):
                time.sleep(check_interval)
                continue
            raise

        time.sleep(check_interval)

    return {
        "code": "OK",
        "gameId": game_id,
        "status": last_seen_status,
        "movesMade": moves_made,
        "message": f"Auto-play window ended after {max_seconds} seconds.",
    }


def _handle_create_game(client: APIClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle ``create-game`` command including optional autoplay."""
    game_id = client.create_game(args.team1, args.team2, args.board_size, args.target)
    result: dict[str, Any] = {"code": "OK", "gameId": game_id}

    if not args.auto_play:
        return result
    if not args.my_team_id:
        raise ValueError("--my-team-id is required when --auto-play is used.")

    auto_result = run_auto_play_loop(
        client=client,
        game_id=game_id,
        team_id=args.my_team_id,
        depth=args.depth,
        top_k_moves=args.top_k_moves,
        neighbor_radius=args.neighbor_radius,
        target=args.target,
        recent_moves_count=args.recent_moves_count,
        verify_turn=not args.no_turn_check,
        poll_seconds=args.poll_seconds,
        max_seconds=args.max_seconds,
        random_tie_break=args.random_tie_break,
        max_time_ms=args.max_time_ms,
        iterative_deepening=not args.no_iterative_deepening,
    )
    result["autoPlay"] = auto_result
    return result


def _handle_join_game(client: APIClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle ``join-game`` command including optional autoplay."""
    details = client.get_game_details(args.game_id)
    if args.team_id not in {str(details.team1_id or ""), str(details.team2_id or "")}:
        raise ValueError(
            f"Team {args.team_id} is not part of game {args.game_id}. "
            f"Expected one of: {details.team1_id}, {details.team2_id}"
        )

    result: dict[str, Any] = {
        "code": "OK",
        "gameId": args.game_id,
        "teamId": args.team_id,
        "game": asdict(details),
    }

    if not args.auto_play:
        return result

    auto_result = run_auto_play_loop(
        client=client,
        game_id=args.game_id,
        team_id=args.team_id,
        depth=args.depth,
        top_k_moves=args.top_k_moves,
        neighbor_radius=args.neighbor_radius,
        target=details.target,
        recent_moves_count=args.recent_moves_count,
        verify_turn=not args.no_turn_check,
        poll_seconds=args.poll_seconds,
        max_seconds=args.max_seconds,
        random_tie_break=args.random_tie_break,
        max_time_ms=args.max_time_ms,
        iterative_deepening=not args.no_iterative_deepening,
    )
    result["autoPlay"] = auto_result
    return result


def _handle_make_move(client: APIClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle one-shot move command in manual or automatic mode."""
    if bool(args.move) == bool(args.auto):
        raise ValueError("Use exactly one of --move or --auto.")

    if args.move:
        move = server_text_to_move(args.move)
        move_id = client.make_move(args.game_id, args.team_id, move)
        return {"code": "OK", "moveId": move_id, "move": move_to_server_text(move)}

    decision, board, details = choose_auto_move(
        client=client,
        game_id=args.game_id,
        team_id=args.team_id,
        search_config=_build_search_config(args),
        target_override=args.target,
        recent_moves_count=args.recent_moves_count,
        verify_turn=not args.no_turn_check,
    )

    if args.dry_run:
        return {
            "code": "OK",
            "selectedMove": move_to_server_text(decision.move),
            "mySymbol": decision.my_symbol,
            "opponentSymbol": decision.opponent_symbol,
            "target": decision.target,
            "status": details.status,
            "board": board.to_pretty(),
        }

    move_id = client.make_move(args.game_id, args.team_id, decision.move)
    return {
        "code": "OK",
        "moveId": move_id,
        "move": move_to_server_text(decision.move),
        "mySymbol": decision.my_symbol,
        "target": decision.target,
    }


def _handle_add_member(client: APIClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle add-member command."""
    client.add_member(args.team_id, args.member_user_id)
    return {"code": "OK"}


def _handle_remove_member(client: APIClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle remove-member command."""
    client.remove_member(args.team_id, args.member_user_id)
    return {"code": "OK"}


def execute(args: argparse.Namespace) -> dict[str, Any]:
    """Execute one CLI command and return JSON-serializable result payload."""
    credentials = resolve_credentials(
        user_id=args.user_id,
        api_key=args.api_key,
        base_url=args.base_url,
        env_file=args.env_file,
        include_authorization_header=not args.no_authorization_header,
    )
    client = APIClient(credentials)

    if args.command == "create-team":
        return {"code": "OK", "teamId": client.create_team(args.name)}
    if args.command == "add-member":
        return _handle_add_member(client, args)
    if args.command == "remove-member":
        return _handle_remove_member(client, args)
    if args.command == "team-members":
        return {"code": "OK", "userIds": client.get_team_members(args.team_id)}
    if args.command == "my-teams":
        return {"code": "OK", "teams": client.get_my_teams()}
    if args.command == "create-game":
        return _handle_create_game(client, args)
    if args.command == "join-game":
        return _handle_join_game(client, args)
    if args.command == "my-games":
        return {"code": "OK", "games": client.get_my_games(args.open_only)}
    if args.command == "game-details":
        return {"code": "OK", "game": asdict(client.get_game_details(args.game_id))}
    if args.command == "board-string":
        return {"code": "OK", "output": client.get_board_string(args.game_id)}
    if args.command == "board-map":
        return {"code": "OK", "output": board_map_to_json_dict(client.get_board_map(args.game_id))}
    if args.command == "moves":
        return {"code": "OK", "moves": move_list_to_text(client.get_moves(args.game_id, args.count))}
    if args.command == "make-move":
        return _handle_make_move(client, args)
    raise ValueError(f"Unknown command: {args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = execute(args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

"""Command-line interface for API operations and auto-move execution."""

from __future__ import annotations

import argparse
import json
import sys
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
    command.add_argument("--recent-moves-count", type=int, default=20)
    command.add_argument("--no-turn-check", action="store_true")

    return parser


def execute(args: argparse.Namespace) -> dict[str, Any]:
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
        client.add_member(args.team_id, args.member_user_id)
        return {"code": "OK"}

    if args.command == "remove-member":
        client.remove_member(args.team_id, args.member_user_id)
        return {"code": "OK"}

    if args.command == "team-members":
        return {"code": "OK", "userIds": client.get_team_members(args.team_id)}

    if args.command == "my-teams":
        return {"code": "OK", "teams": client.get_my_teams()}

    if args.command == "create-game":
        game_id = client.create_game(args.team1, args.team2, args.board_size, args.target)
        return {"code": "OK", "gameId": game_id}

    if args.command == "my-games":
        return {"code": "OK", "games": client.get_my_games(args.open_only)}

    if args.command == "game-details":
        details = client.get_game_details(args.game_id)
        return {"code": "OK", "game": asdict(details)}

    if args.command == "board-string":
        return {"code": "OK", "output": client.get_board_string(args.game_id)}

    if args.command == "board-map":
        board_map = client.get_board_map(args.game_id)
        return {"code": "OK", "output": board_map_to_json_dict(board_map)}

    if args.command == "moves":
        moves = client.get_moves(args.game_id, args.count)
        return {"code": "OK", "moves": move_list_to_text(moves)}

    if args.command == "make-move":
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
            search_config=SearchConfig(
                depth=args.depth,
                top_k_moves=args.top_k_moves,
                neighbor_radius=args.neighbor_radius,
            ),
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

"""Parsing and normalization helpers for API payloads."""

from __future__ import annotations

import json
from ast import literal_eval
from typing import Any, Iterable

from gttt.coordinates import (
    move_to_server_text,
    move_to_server_pair,
    server_pair_to_move,
    server_text_to_move,
)
from gttt.errors import APITransportError
from gttt.models import GameDetails, Move


def parse_json_text(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise APITransportError(f"Non-JSON response: {raw}") from exc
    if not isinstance(payload, dict):
        raise APITransportError(f"Unexpected JSON payload type: {type(payload)!r}")
    return payload


def parse_json_if_string(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                try:
                    return literal_eval(stripped)
                except (ValueError, SyntaxError):
                    return value
    return value


def parse_id_list(value: Any) -> list[str]:
    def normalize_item(item: Any) -> list[str]:
        parsed_item = parse_json_if_string(item)
        if isinstance(parsed_item, dict):
            if len(parsed_item) == 1:
                return [str(next(iter(parsed_item.keys())))]
            return [str(key) for key in parsed_item.keys()]
        if isinstance(parsed_item, list):
            return [str(part) for part in parsed_item]
        return [str(parsed_item)]

    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(normalize_item(item))
        return items
    if isinstance(value, str):
        parsed = parse_json_if_string(value)
        if isinstance(parsed, list):
            items: list[str] = []
            for item in parsed:
                items.extend(normalize_item(item))
            return items
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, dict):
        if len(value) == 1:
            return [str(next(iter(value.keys())))]
        return [str(key) for key in value.keys()]
    return []


def parse_game_details(payload: dict[str, Any]) -> GameDetails:
    raw_game = parse_json_if_string(payload.get("game", {}))
    if not isinstance(raw_game, dict):
        raw_game = {}

    def first(*keys: str, default: Any = "") -> Any:
        for key in keys:
            if key in raw_game and raw_game[key] not in (None, ""):
                return raw_game[key]
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
        return default

    def to_int(value: Any, fallback: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    winner = first("winnerteamid", "winnerTeamId", default="")
    turn = first("turnteamid", "turnTeamId", default="")
    seconds = first("secondspermove", "secondsPerMove", default="")

    return GameDetails(
        game_id=str(first("gameid", "gameId")),
        game_type=str(first("gametype", "gameType", default="TTT")),
        board_size=to_int(first("boardsize", "boardSize", default=0)),
        target=to_int(first("target", default=0)),
        team1_id=str(first("team1id", "teamId1", default="")),
        team1_name=str(first("team1Name", default="")),
        team2_id=str(first("team2id", "teamId2", default="")),
        team2_name=str(first("team2Name", default="")),
        status=str(first("status", default="UNKNOWN")),
        moves=to_int(first("moves", default=0)),
        turn_team_id=(str(turn) if str(turn).strip() and str(turn) != "0" else None),
        winner_team_id=(str(winner) if str(winner).strip() and str(winner) != "0" else None),
        seconds_per_move=(to_int(seconds) if str(seconds).strip() else None),
    )


def parse_moves(payload: dict[str, Any]) -> list[Move]:
    raw_moves = payload.get("moves", [])
    if not isinstance(raw_moves, list):
        return []

    parsed: list[Move] = []
    for item in raw_moves:
        if not isinstance(item, dict):
            continue
        move_text = item.get("move")
        if isinstance(move_text, str) and "," in move_text:
            try:
                parsed.append(server_text_to_move(move_text))
                continue
            except (TypeError, ValueError):
                pass

        x_value = item.get("moveX")
        y_value = item.get("moveY")
        if x_value is None or y_value is None:
            continue

        try:
            parsed.append(server_pair_to_move(int(x_value), int(y_value)))
        except (TypeError, ValueError):
            continue
    return parsed


def parse_symbol_by_team(payload: dict[str, Any], team_id: str) -> str | None:
    raw_moves = payload.get("moves", [])
    if not isinstance(raw_moves, list):
        return None

    for item in raw_moves:
        if not isinstance(item, dict):
            continue
        if str(item.get("teamId")) != str(team_id):
            continue
        symbol = item.get("symbol")
        if symbol in {"X", "O"}:
            return str(symbol)
    return None


def parse_board_map(payload: dict[str, Any]) -> dict[tuple[int, int], str]:
    raw_output = parse_json_if_string(payload.get("output", {}))
    if not isinstance(raw_output, dict):
        return {}

    mapped: dict[tuple[int, int], str] = {}
    for key, value in raw_output.items():
        if not isinstance(key, str) or "," not in key:
            continue
        left, right = key.split(",", 1)
        try:
            move = server_pair_to_move(int(left.strip()), int(right.strip()))
        except ValueError:
            continue
        symbol = str(value)
        if symbol in {"X", "O"}:
            mapped[(move.x, move.y)] = symbol
    return mapped


def board_map_to_json_dict(board_map: dict[tuple[int, int], str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for x, y in sorted(board_map):
        first, second = move_to_server_pair(Move(x=x, y=y))
        output[f"{first},{second}"] = board_map[(x, y)]
    return output


def move_list_to_text(moves: Iterable[Move]) -> list[str]:
    return [move_to_server_text(move) for move in moves]

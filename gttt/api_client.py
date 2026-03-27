"""HTTP client wrapper for the single-endpoint game API."""

from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gttt.constants import DEFAULT_AUTHORIZATION_HEADER
from gttt.errors import APIResponseError, APITransportError
from gttt.models import Credentials, GameDetails, Move
from gttt.parsing import (
    parse_board_map,
    parse_game_details,
    parse_id_list,
    parse_json_text,
)


class APIClient:
    def __init__(self, credentials: Credentials, timeout_seconds: int = 30) -> None:
        self.credentials = credentials
        self.timeout_seconds = timeout_seconds

    def _headers(self, is_post: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "curl/8.0.1",
            "userid": self.credentials.user_id,
            "x-api-key": self.credentials.api_key,
        }
        if self.credentials.include_authorization_header:
            headers["Authorization"] = DEFAULT_AUTHORIZATION_HEADER
        if is_post:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        return headers

    def _request(self, method: str, params: dict[str, object]) -> dict[str, object]:
        normalized = {key: str(value) for key, value in params.items()}
        is_post = method.upper() == "POST"

        if is_post:
            url = self.credentials.base_url
            data = urlencode(normalized).encode("utf-8")
        else:
            query = urlencode(normalized)
            url = f"{self.credentials.base_url}?{query}"
            data = None

        request = Request(url=url, data=data, headers=self._headers(is_post), method=method.upper())

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace").strip()
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace").strip()
            raise APITransportError(f"HTTP {exc.code}: {error_body or exc.reason}") from exc
        except URLError as exc:
            raise APITransportError(f"Network error: {exc.reason}") from exc

        if not body:
            raise APITransportError("Empty response from API")
        if body.startswith("<"):
            raise APITransportError(f"Unexpected HTML response: {body[:200]}")

        payload = parse_json_text(body)
        if str(payload.get("code", "OK")).upper() == "FAIL":
            raise APIResponseError(str(payload.get("message", "Request failed")), payload)
        return payload

    def create_team(self, name: str) -> str:
        payload = self._request("POST", {"type": "team", "name": name})
        return str(payload.get("teamId", ""))

    def add_member(self, team_id: str, user_id: str) -> None:
        self._request("POST", {"type": "member", "teamId": team_id, "userId": user_id})

    def remove_member(self, team_id: str, user_id: str) -> None:
        self._request("POST", {"type": "removeMember", "teamId": team_id, "userId": user_id})

    def get_team_members(self, team_id: str) -> list[str]:
        payload = self._request("GET", {"type": "team", "teamId": team_id})
        return parse_id_list(payload.get("userIds", []))

    def get_my_teams(self) -> list[str]:
        payload = self._request("GET", {"type": "myTeams"})
        return parse_id_list(payload.get("teams") or payload.get("myTeams", []))

    def create_game(self, team1_id: str, team2_id: str, board_size: int, target: int) -> str:
        payload = self._request(
            "POST",
            {
                "type": "game",
                "teamId1": team1_id,
                "teamId2": team2_id,
                "gameType": "TTT",
                "boardSize": board_size,
                "target": target,
            },
        )
        return str(payload.get("gameId", ""))

    def get_my_games(self, open_only: bool = False) -> list[str]:
        request_type = "myOpenGames" if open_only else "myGames"
        payload = self._request("GET", {"type": request_type})
        if open_only:
            return parse_id_list(
                payload.get("games")
                or payload.get("myOpenGames")
                or payload.get("openGames", [])
            )
        return parse_id_list(payload.get("games") or payload.get("myGames", []))

    def get_game_details(self, game_id: str) -> GameDetails:
        payload = self._request("GET", {"type": "gameDetails", "gameId": game_id})
        return parse_game_details(payload)

    def get_board_string(self, game_id: str) -> str:
        payload = self._request("GET", {"type": "boardString", "gameId": game_id})
        for key in ("output", "board", "boardString", "string"):
            value = payload.get(key)
            if isinstance(value, str):
                compact = "".join(ch for ch in value if ch in {"X", "O", "-"})
                if compact:
                    return value
        for value in payload.values():
            if isinstance(value, str):
                compact = "".join(ch for ch in value if ch in {"X", "O", "-"})
                if compact:
                    return value
        raise APITransportError(f"Could not parse board string from payload: {payload}")

    def get_board_map(self, game_id: str) -> dict[tuple[int, int], str]:
        payload = self._request("GET", {"type": "boardMap", "gameId": game_id})
        return parse_board_map(payload)

    def get_moves_raw(self, game_id: str, count: int = 20) -> dict[str, object]:
        return self._request("GET", {"type": "moves", "gameId": game_id, "count": count})

    def get_moves(self, game_id: str, count: int = 20) -> list[Move]:
        payload = self.get_moves_raw(game_id, count)
        raw_moves = payload.get("moves", [])
        if not isinstance(raw_moves, list):
            return []

        parsed: list[Move] = []
        for item in raw_moves:
            if not isinstance(item, dict):
                continue
            try:
                parsed.append(Move(x=int(item["moveX"]), y=int(item["moveY"])))
            except (KeyError, TypeError, ValueError):
                move_text = item.get("move")
                if isinstance(move_text, str) and "," in move_text:
                    try:
                        parsed.append(Move.from_text(move_text))
                    except (TypeError, ValueError):
                        continue
        return parsed

    def make_move(self, game_id: str, team_id: str, move: Move) -> str:
        payload = self._request(
            "POST",
            {
                "type": "move",
                "gameId": game_id,
                "teamId": team_id,
                "move": move.to_text(),
            },
        )
        return str(payload.get("moveId", ""))

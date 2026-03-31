"""Configuration helpers for CLI and API client.

Author: Kamal Ahmadov
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from gttt.constants import DEFAULT_BASE_URL
from gttt.models import Credentials


def load_env_file(path: str = ".env") -> Dict[str, str]:
    """Load basic ``KEY=VALUE`` pairs from an env file."""
    values: Dict[str, str] = {}
    env_path = Path(path)
    if not env_path.exists():
        return values

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        # Keep parser intentionally simple: KEY=VALUE per line.
        key, raw_value = stripped.split("=", 1)
        values[key.strip()] = raw_value.strip().strip('"').strip("'")
    return values


def resolve_credentials(
    user_id: Optional[str],
    api_key: Optional[str],
    base_url: Optional[str],
    env_file: str = ".env",
    include_authorization_header: bool = True,
) -> Credentials:
    """Resolve credentials from args first, then fall back to env file values."""
    env_values = load_env_file(env_file)
    resolved_user_id = user_id or env_values.get("USER_ID")
    resolved_api_key = api_key or env_values.get("API_KEY")

    if not resolved_user_id or not resolved_api_key:
        raise ValueError(
            "Missing credentials. Pass --user-id/--api-key or define USER_ID/API_KEY in .env."
        )

    return Credentials(
        user_id=str(resolved_user_id),
        api_key=str(resolved_api_key),
        base_url=base_url or DEFAULT_BASE_URL,
        include_authorization_header=include_authorization_header,
    )

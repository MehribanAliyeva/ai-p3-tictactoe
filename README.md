# Generalized Tic-Tac-Toe Agent (Modular Python)

This repository contains a modular Python client and AI agent for the NotExponential P2P generalized Tic-Tac-Toe API (`n x n`, target `m`).

## Current Capabilities

- Full API wrapper for team/game/move operations against a single endpoint
- Robust transport handling with retries/backoff for transient failures (`5xx`, network timeouts)
- Coordinate normalization between server wire format (`row,col`) and internal model (`x,y`)
- Minimax with alpha-beta pruning
- Iterative deepening with optional time budget (`--max-time-ms`)
- Transposition-table caching in search
- Optional random tie-breaks to reduce deterministic repeated openings
- CLI workflows for one-shot moves and continuous auto-play loops

## Project Layout

- `main.py`: thin entrypoint
- `gttt/config.py`: credential/env loading
- `gttt/api_client.py`: resilient API client (headers, retries, response validation)
- `gttt/parsing.py`: payload normalization and schema tolerance
- `gttt/coordinates.py`: server/internal coordinate conversion
- `gttt/board.py`: board representation and move generation
- `gttt/heuristics.py`: evaluation heuristics
- `gttt/search.py`: search engine (alpha-beta + iterative deepening + transposition cache)
- `gttt/agent.py`: AI orchestration and symbol inference
- `gttt/cli.py`: command parsing and execution
- `tests/`: unit tests for parsing, board logic, search, coordinates, and API retry behavior

## Setup

1. Create `.env` in repo root:

```bash
USER_ID=your_user_id
API_KEY=your_api_key
```

2. Run CLI help:

```bash
python3 main.py --help
```

## Common Commands

### Team management

```bash
python3 main.py create-team --name AlphaBots
python3 main.py add-member --team-id 1001 --member-user-id 3736
python3 main.py team-members --team-id 1001
python3 main.py my-teams
```

### Game setup and inspection

```bash
python3 main.py create-game --team1 1001 --team2 1002 --board-size 5 --target 4
python3 main.py my-games
python3 main.py game-details --game-id 1234
python3 main.py board-string --game-id 1234
python3 main.py board-map --game-id 1234
python3 main.py moves --game-id 1234 --count 20
```

### Single move execution

Manual move (`row,col`):

```bash
python3 main.py make-move --game-id 1234 --team-id 1001 --move 2,3
```

Auto move with dry-run:

```bash
python3 main.py make-move --game-id 1234 --team-id 1001 --auto --dry-run
```

Auto move with search tuning:

```bash
python3 main.py make-move --game-id 1234 --team-id 1001 --auto \
  --depth 4 --top-k-moves 14 --neighbor-radius 1 \
  --max-time-ms 1500 --random-tie-break
```

## Auto-Play Loops

Start a new game and auto-play as your team:

```bash
python3 main.py create-game --team1 1001 --team2 1002 --board-size 5 --target 4 \
  --auto-play --my-team-id 1001 --depth 3 --poll-seconds 2 --max-seconds 1200
```

Join an existing game and auto-play:

```bash
python3 main.py join-game --game-id 1234 --team-id 1001 \
  --auto-play --depth 3 --poll-seconds 2 --max-seconds 1200
```

## Search Flags

For `make-move --auto`:

- `--depth`: max nominal depth
- `--top-k-moves`: candidate move cap per ply
- `--neighbor-radius`: locality pruning radius
- `--max-time-ms`: time budget for iterative deepening
- `--no-iterative-deepening`: disable iterative deepening and run fixed-depth search
- `--random-tie-break`: add tiny score jitter for equal-score move ordering

## Coordinate Convention

- Server/API uses `row,col` strings
- Internal search/board uses `x,y`
- Conversion is handled centrally in `gttt/coordinates.py`

## Testing

Run all unit tests:

```bash
python3 -m unittest discover -s tests -v
```

# Generalized Tic-Tac-Toe Agent (Modular Python)

This project implements a generalized `n x n` Tic-Tac-Toe (`target = m`) agent and API CLI for the NotExponential P2P game server.

## Architecture

- `gttt/config.py`: loads credentials from CLI or `.env`
- `gttt/api_client.py`: single-endpoint API wrapper (GET/POST, auth headers, `code` handling)
- `gttt/parsing.py`: payload normalization and double-JSON decoding helpers
- `gttt/board.py`: board parsing and board operations
- `gttt/heuristics.py`: evaluation function (windows, longest chain, center control)
- `gttt/search.py`: depth-limited minimax with alpha-beta pruning and move ordering
- `gttt/agent.py`: symbol/target inference and auto-move orchestration
- `gttt/cli.py`: command dispatcher
- `main.py`: thin entrypoint

## Setup

1. Add credentials to `.env`:

```bash
USER_ID=your_user_id
API_KEY=your_api_key
```

2. Run commands:

```bash
python3 main.py --help
python3 main.py my-teams
```

## Key Commands

```bash
python3 main.py create-team --name MyanmarKyat
python3 main.py create-game --team1 1001 --team2 1002 --board-size 12 --target 6
python3 main.py game-details --game-id 1234
python3 main.py make-move --game-id 1234 --team-id 1001 --move 4,4
python3 main.py make-move --game-id 1234 --team-id 1001 --auto --dry-run
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

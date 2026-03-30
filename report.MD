# Generalized Tic Tac Toe Agent (n × n, target m)

## 1. Evaluation (Heuristic) Function

The evaluation function estimates the quality of non-terminal board states and guides the minimax search.

### Window-Based Exponential Scoring
The board is decomposed into all contiguous **windows of length m** across:
- rows  
- columns  
- diagonals  

Each window is evaluated using a composition-based scoring rule:

- If both players appear → score = 0 (blocked line)
- If only one player appears:
  - reward grows **exponentially** with count  
  - score = base^k, where k is the number of symbols
- If a window reaches length m:
  - large reward/penalty (~10^6)

This encourages:
- extending own sequences
- blocking opponent sequences early

---

### Longest Consecutive Chain Heuristic
The evaluation explicitly considers the maximum consecutive symbols for each player:

- reward own longest chain  
- penalize opponent’s longest chain (slightly stronger weight)

This captures:
- near-winning threats  
- long-term strategic pressure  

---

### Positional (Center) Bias
Each move is assigned a positional bonus based on Manhattan distance from center:

- central positions → higher score  
- edges → lower score  

This reflects:
- central cells participate in more winning combinations  
- improves early-game positioning  

---

### Terminal State Override
Terminal conditions dominate all heuristic values:

- win → large positive score (~ +10^7)  
- loss → large negative score (~ -10^7)  
- draw → 0  

Additionally:
- depth is incorporated to prefer:
  - faster wins  
  - delayed losses  

---

## 2. Minimax / Adversarial Search

We implement **depth-limited minimax with alpha-beta pruning**.

### Core Strategy
- Maximizing player → maximize evaluation score  
- Minimizing player → minimize evaluation score  
- Alpha-beta pruning eliminates irrelevant branches  

---

### Immediate Tactical Optimization
Before running search:

- check for **immediate winning moves**  
- check for **immediate opponent threats (blocks)**  

This avoids unnecessary recursion and ensures tactical correctness.

---

### Iterative Deepening (Optional)
Search can be performed using iterative deepening:

- progressively increase depth  
- return best move found within time constraint  

---

### Move Ordering
Moves are evaluated heuristically before recursion:

- uses evaluation function + positional bonus  
- best moves explored first  
- significantly improves alpha-beta pruning efficiency  

---

### Transposition Table (Caching)
A hash-based cache stores previously evaluated states:

- key = (board state, depth, player type)  
- avoids recomputation of identical positions  
- improves performance in deeper searches  

---

## 3. Performance Optimizations

### Local Move Pruning (Neighborhood Heuristic)
Instead of exploring all empty cells:

- only consider moves near existing pieces  
- reduces branching factor dramatically  

---

### Top-K Candidate Selection
Only the top K moves (based on heuristic score) are explored:

- reduces computation  
- maintains high-quality search  

---

### Alpha-Beta Pruning
Cuts off branches where:

- outcome cannot improve current best result  

This reduces complexity from:
- O(b^d) → much smaller effective search space  

---

### Time-Bounded Search
Search can be constrained by time:

- uses deadline-based cutoff  
- ensures responsiveness  
- returns best move found so far  

---

### Random Tie-Breaking
Small random noise is added to scores:

- prevents deterministic play  
- improves exploration diversity  

---

## Summary

The agent combines:

- exponential window-based evaluation  
- longest-chain strategic awareness  
- positional heuristics  
- alpha-beta pruning with move ordering  
- transposition caching and pruning  

to efficiently scale to generalized n × n Tic Tac Toe.

This design balances:

- tactical accuracy (immediate wins/blocks)  
- strategic depth (heuristics + minimax)  
- computational efficiency (pruning + caching)
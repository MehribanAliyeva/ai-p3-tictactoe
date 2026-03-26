# Generalized Tic Tac Toe Agent (n × n, target m)

## 1. Evaluation (Heuristic) Function

The evaluation function estimates the quality of non-terminal board states and guides the minimax search.

### Window-Based Scoring
The board is decomposed into all contiguous **windows of length m** across:
- rows
- columns
- diagonals

Each window is scored based on symbol composition:
- If both players appear → score = 0 (blocked line)
- If only one player appears → reward grows **exponentially** with count  
  - e.g., 10^k for k consecutive symbols
- Encourages extending longer sequences toward the target m

### Longest Consecutive Sequence
We compute the maximum consecutive symbols for each player:
- reward own longest chain
- penalize opponent’s longest chain

This captures near-win situations even if they span across different windows.

### Positional Heuristic (Center Control)
Cells closer to the center are weighted higher:
- central positions participate in more potential winning lines
- improves early-game move quality

### Terminal Override
Terminal states dominate heuristic values:
- win → large positive value (e.g., +10^7)
- loss → large negative value (e.g., -10^7)
- draw → 0

A depth-based adjustment prefers:
- faster wins
- slower losses

---

## 2. Minimax / Adversarial Search

We use **depth-limited minimax with alpha-beta pruning**:

- Maximizing player tries to maximize the evaluation score  
- Minimizing player tries to minimize it  
- Alpha-beta pruning removes branches that cannot influence the final decision  
- Depth limit ensures feasibility for large boards  

Additionally:
- Immediate winning moves are played without search  
- Immediate threats from the opponent are blocked before deeper exploration  

---

## 3. Performance Optimizations

### Move Pruning (Locality Heuristic)
Only consider moves near existing pieces (within a small radius).  
This reduces the branching factor significantly.

### Move Ordering
Moves are scored heuristically before recursion:
- better moves explored first  
- increases effectiveness of alpha-beta pruning  

### Top-K Candidate Selection
Only the top K promising moves are explored at each depth level.

### Early Termination
Detect:
- immediate wins  
- immediate blocks  

This avoids unnecessary recursive computation.

---

## Summary

The combination of:
- structured heuristic evaluation  
- alpha-beta pruning  
- aggressive move pruning  

allows the agent to scale efficiently to generalized n × n Tic Tac Toe while maintaining strong decision quality.

# Tic Tac Toe Agent (n × n, target m)

## 1. Evaluation (Heuristic) Function

The evaluation function estimates the quality of non-terminal board states and guides the minimax search. The board is decomposed into all contiguous windows of length m across rows, columns, and diagonals. Each window is scored based on its composition: if both players appear, the window is blocked and contributes zero; if only one player appears, the score grows exponentially with the number of symbols (base^k), encouraging the formation of longer sequences. If a window reaches the target length m, it receives a large reward or penalty, approximating terminal behavior. 

In addition, the heuristic incorporates the maximum consecutive sequence length for both players, rewarding longer chains for the agent while penalizing those of the opponent slightly more strongly to emphasize defensive play. A positional component is also included, assigning higher scores to moves closer to the center using a Manhattan-distance-based bonus, reflecting the higher strategic value of central positions. Terminal states override all heuristic components: a win yields a large positive score, a loss a large negative score, and a draw zero, with a depth adjustment that favors faster wins and delayed losses.

## 2. Minimax / Adversarial Search

The agent uses a depth-limited minimax algorithm with alpha-beta pruning to efficiently explore the game tree. The maximizing player seeks to maximize the heuristic score, while the minimizing player seeks to minimize it. Alpha-beta pruning eliminates branches that cannot affect the final decision, significantly reducing computation. Before running the full search, the agent checks for immediate winning moves and immediate threats from the opponent, ensuring tactical correctness without unnecessary recursion.

To further improve performance, the search supports iterative deepening, progressively increasing depth while maintaining a valid best move under time constraints. Move ordering is applied by evaluating candidate moves heuristically before recursion, allowing stronger moves to be explored first and improving pruning efficiency. Additionally, a transposition table caches previously evaluated states using a combination of board configuration, depth, and player type, reducing redundant computations in deeper searches.

## 3. Performance Optimizations

To control the branching factor, the agent applies a locality heuristic, considering only moves within a small neighborhood of existing pieces rather than the entire board. This dramatically reduces the number of candidate moves. From these candidates, only the top K moves—ranked by heuristic score are explored at each depth, balancing efficiency and decision quality. Alpha-beta pruning further reduces the effective search space by cutting off suboptimal branches early.

The search can also be constrained by time using a deadline-based mechanism, ensuring responsiveness even in larger boards. A small random noise is added to move scores to break ties and avoid deterministic play patterns, improving exploration diversity. Together, these optimizations allow the agent to scale effectively to generalized n × n Tic Tac Toe while maintaining strong strategic and tactical performance.

## Summary

The agent combines an exponential window-based heuristic, longest-chain evaluation, positional awareness, and depth-adjusted terminal scoring with an optimized alpha-beta search framework. Through move ordering, locality pruning, top-K selection, caching, and time control, the system achieves a balance between computational efficiency and high-quality decision making in generalized Tic Tac Toe.
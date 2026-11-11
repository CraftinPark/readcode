# Tailoring: posting -> concepts -> problem

This is step 2 of John's pipeline done by hand for one posting ([posting.md](posting.md)): a small concept list for robot learning, the posting's weight on each, and the top concept the problem is built around.

## How the weights were set

For each concept, score the posting on three things, then normalise so the weights sum to 1:

- **Placement** (0-3): in the role summary or "What you'll do" counts most, "looking for" next, "nice to have" least.
- **Emphasis** (0-3): bold lead-in, ownership verbs ("own", "design"), repetition across sections.
- **Interview signal** (0-2): does "How we interview" point at it?

Raw score = placement + emphasis + interview. The concept list is drawn from the failure classes in `research/ml/field-guide.md` and the robotics columns of `research/ml/postings.md` (25% of robotics postings name imitation learning or teleop; 52% name deploying on hardware).

## Concepts and weights

| # | Concept | Raw | Weight | Why (from the posting) |
|---|---|---|---|---|
| 1 | **Teleop demonstration data pipelines** (recording formats, multi-rate streams, synchronisation, quality filtering, dataset tooling) | 8 | **0.195** | First bullet of "What you'll do", bold, "own"; named again in "looking for" (timestamps, multi-rate sensors) and in the interview's system-design round |
| 2 | Behaviour cloning / imitation-learning fundamentals | 6 | 0.146 | Role summary ("policies learn from human demonstrations"), second bullet, "looking for" |
| 3 | Closed-loop evaluation on hardware; offline-vs-robot gap | 6 | 0.146 | Own bullet ("close the gap between offline metrics and closed-loop success"), "debugged a policy on hardware", lab visit |
| 4 | Train/robot parity (preprocessing, normalisation, observation construction match at run time) | 4 | 0.098 | "make sure what the policy sees in training is what it sees on the robot" |
| 5 | Action chunking and temporal ensembling | 3 | 0.073 | "behaviour cloning with action chunking", "ACT-style chunking" |
| 6 | Transformer / diffusion policy architectures | 3 | 0.073 | Second bullet, "looking for" |
| 7 | PyTorch training-loop engineering | 3 | 0.073 | "strong PyTorch"; interview "debugging a piece of our-style training code" |
| 8 | Data-quality checks and silent-failure detection | 3 | 0.073 | "Keep the pipeline honest" bullet |
| 9 | Teleop rigs and data-collection operations | 2 | 0.049 | "Improve data collection" bullet |
| 10 | Simulation and sim-to-real | 1 | 0.024 | Nice to have |
| 11 | Large-scale / distributed training | 1 | 0.024 | Nice to have |
| 12 | RL fine-tuning of pretrained policies | 1 | 0.024 | Nice to have |

Weight = raw / 41 (the sum of the raw scores), so the weights sum to 1 up to rounding.

## Top concept: teleop demonstration data pipelines (0.195)

The posting leads with it, says "own", and repeats it in the requirements and the interview. It is also the concept generic ML prep covers least: it lives between the robot and the training loop, and its failures train fine and only show on the robot (the field guide's "wildest animals give no error").

## How the problem uses it

- **Codebase:** a teleop demonstration pipeline and behaviour-cloning trainer for a pick-and-place cell, about 1,300 lines: recorder format, loader, synchronisation, quality gates, action chunking, normalisation, an MLP chunk policy, temporal ensembling, a robot-side runner and a bench twin for closed-loop evaluation.
- **Code tab (stage: implement / fix):** an incident from the robot lab, "the policy misbehaves on the cell". The concepts the posting weights next (2, 3, 4, 5) are the surrounding code the solver has to rule in or out.
- **Comprehension tab:** seven questions across concepts 1, 2, 4, 5 and 8, each needing two or more files.

What a different posting would change: an RL-heavy posting would put concept 12 (or the field guide's RL specifics) on top and the same harness would carry a different incident; a perception posting would move the weight to coordinate conventions and augmentation.

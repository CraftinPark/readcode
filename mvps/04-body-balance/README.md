# MVP 04: Balance a body (systems thinking, "Terraforming Mars for software")

*Idea 5b: a third kind of problem next to find-the-bug (Tier 1) and the AI-allowed credential (Tier 2). No single right answer, only better and worse trade-offs. AI-written MVP: an experiment, not shipped content.*

## The brief (what the player sees)

> The patient is short of breath. Oxygen (requests) arrives at the lungs; the heart (worker pool) pumps it; what can't be pumped waits in the blood vessels (queue); the liver (cache) serves some on its own; the immune system (retries, timeouts) handles failures. Oxygen that waits is worth less (latency): full value now, 0.8 after 1 tick, 0.4 after 2, nothing after 3.
>
> During the 30-tick run an **infection** hits (ticks 12-17: traffic x2.5, 25% of work fails) and an **injury** (ticks 22-24: half the heart is down). Nutrients (budget) are limited.
>
> Edit the six knobs in `body.json` and run `python body.py` (add `--verbose` for a tick-by-tick trace). Get the score to **80 or more**.

Score = 50% health (oxygen value delivered / needed) + 25% cost (under budget) + 25% stability (steady delivery tick to tick). Python 3.10+, no packages.

| Organ | Backend concept | Knob |
|---|---|---|
| Heart | Worker pool | `heart_capacity` |
| Blood vessels | Queue | `vessel_queue` |
| Immune system | Retries, timeouts | `retry_limit`, `timeout_ticks` |
| Liver | Cache | `liver_cache` |
| Adrenaline | Autoscaling | `autoscale_threshold` |

## What we learned building it

- Shipped config scores **49.8** (a huge queue with a long timeout: nothing is "lost", but the oxygen arrives too late). "Buy more heart" gets **76.3**. The reference balance (small heart + cache + early autoscale + short queue) gets **84.3**. `python _key/check_key.py` checks all three.
- A brute-force grid search over the six knobs found the best score in seconds. **This is the AI risk from the doc made concrete:** as a credential this needs the gate, or hidden conditions (a different shock at test time than in practice).
- `retry_limit` barely moves the score in this version; the retry storm needs to cost more to be a real lesson.

## Not done

Hidden test-time shocks (score on an unseen infection), a write-up question ("why does the bigger queue make the patient sicker?"), any UI.

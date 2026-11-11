# ML case 4: grasp success is down

*A ReadCode case (Tier 1: no AI assistants). Judgement-graded, in the style of the USMLE Step 3 CCS cases. Suggested time: 45 minutes of real time.*

## The ticket

It's Thursday 29 October, 09:00. You're on call for the **grasp model**: the perception model that picks where each robot arm grabs an item, plus its model registry, routing and the grasp-serving service. About 260 pick-and-place arms run it across four warehouse sites (Columbus, Reno, Leipzig, Osaka).

> **From:** Fleet operations. **Priority:** P1
>
> Fleet grasp success was a steady 94% for weeks. Since yesterday it's about 90%. Dropped items are piling up and some get damaged. Columbus is shouting the loudest. Please fix it today; a big customer's new products start arriving this afternoon.

Every action costs simulated time, and the arms keep failing grasps while you work. The shift ends at 17:00. Find the cause, fix production so it stays fixed, declare the incident resolved when it is, then name the cause.

**Scope.** You own the grasp model, the model registry and routing (`route`), training jobs (`retrain`) and the serving settings (`serving.*`). Camera firmware belongs to the hardware team, conveyors and sites to site ops, the feature store and the labeling vendors to their teams. You can ask them (`page`, `ask_site`); changing their things yourself is out of scope.

## How to play

```
python case.py start          # prints this ticket
python case.py actions        # every action and its time cost
python case.py do <action> [args]
python case.py status
python case.py causes         # the possible mechanisms and segments
python case.py submit <change-id> <mechanism-letter> <segment>
```

- You see the system only through actions: daily dashboards, a live view of the last 30 minutes, the change log, model cards, sample camera frames, offline evals, a label audit, and people you can ask. Some actions change production; changes take a few minutes to roll out.
- `do wait <minutes>` lets time pass (useful after a change goes out).
- `do resolve` declares the incident resolved. You can't change production after that. The shift runs on to 17:00, and the replay after you submit shows whether your fix held through the afternoon.
- `submit` names the change that introduced the cause, the mechanism (a letter from `causes`) and the segment it hits (its text or its number). Submitting ends the case.

## How it's scored (out of 100)

| Part | Points | What counts |
|---|---|---|
| Diagnosis | 30 | The exact change, mechanism and segment |
| Fix held | 25 | Every site/camera group stayed at or above the SLO (90%, fleet 93%) from your declaration to 17:00, with no robots left paused |
| Harm to users | 15 | Avoidable failed grasps today, compared with an expert's path |
| Cost | 10 | GPU money spent |
| Judgement | 20 | Penalties for risky, over-broad, unnecessary or out-of-scope actions, and for declaring too early, too late or never |

## Rules

No AI assistants. Don't look outside this folder for answers. Treat every action as real production.

## Starting the server (organiser)

The engine runs as a separate server process from the source folder; the player folder holds only this README and `case.py`.

```
cd C:\Users\chdan\code\literacy\mvps\ml-4-grasp-drop
C:\Python314\python server.py        # leave running; listens on 127.0.0.1:8791
```

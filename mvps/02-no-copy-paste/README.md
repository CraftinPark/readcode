# MVP 02: No copy-paste mode (Tier 1.5, second half)

*Idea 5c: the player may ask an AI, but must type everything; no copy, paste, drag or upload. The AI can't read the whole repo, so the person decides where to look and what to ask. AI-written MVP: an experiment, not shipped content.*

```
python build_bundle.py                    # packs ../01-big-repo-no-hint/out into bundle.js (git-ignored)
python -m http.server 8931                # then open http://127.0.0.1:8931/viewer.html
```

`viewer.html` is one static page: a file tree, the code (not selectable), an "Ask the AI" box, and **the trail**: every file opened, every question typed and every blocked copy/paste attempt, with timestamps, downloadable as JSON. Checked in the browser: 25 files load, opening a file and a blocked paste both land in the trail.

## What we learned building it

- Blocking copy, cut, paste, drag and right-click takes six lines of JavaScript. Getting around it takes a phone photo or a screenshot into a multimodal AI. So this is honour-system, like Tier 1, unless proctored.
- The trail is the more valuable half: "which files did they open, in what order, before the first right answer" measures where-to-look directly, with or without AI.
- MVP: questions are logged, not sent to a model. The real version would call the model with exactly the typed text.

Not done: the real model call, timing per question, comparing trails between strong and weak solvers.

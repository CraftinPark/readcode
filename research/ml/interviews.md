# ML debugging in interviews: what the reports say

Collected 2026-10-24 by web search. Almost all sources are secondhand (interview-report and prep sites); several are paywalled, so details marked *unverified* could not be checked.

## Debugging rounds exist, and look like this

| Where | What candidates report | Source | Confidence |
|---|---|---|---|
| OpenAI, Applied ML onsite | A 60-minute "machine learning code debugging" round | [1point3acres thread 1101638](https://www.1point3acres.com/interview/thread/1101638) | unverified (paywalled) |
| OpenAI, MLE screen (Apr 2026 report) | Get a miniGPT to produce correct text (find and fix bugs in PyTorch), then implement a KV cache; a separate round debugs a buggy Python job scheduler | [PracHub](https://prachub.com/interview-experiences/openai-machine-learning-engineer-interview-experience-a-malloc-phone-screen-and-a-surprise-debugging-round) | secondhand |
| OpenAI, research engineer guide | Find and fix bugs in an existing transformer implementation, then extend it; judged on transformer internals, debugging method, ML systems depth | [Exponent](https://www.tryexponent.com/guides/openai-research-engineer-interview-guide) | secondhand |
| Anthropic, entry-level MLE (late 2025) | A debugging round is mentioned; details cut off | Exponent summary (same guide) | unverified |
| startups.com, MLE (2026) | A PyTorch debugging round | [1point3acres thread 1167208](https://www.1point3acres.com/interview/thread/1167208) | unverified (paywalled) |
| Take-home tasks | "This PyTorch classifier produces NaN losses: find the cause, fix it, write one line on what you changed"; "analyse the script, identify the problems, fix them" | [Harbor task](https://hub.harborframework.com/tasks/termigen/nan_loss_debugging_medium) | task description |
| Waymo, MLE | Google-style loop: coding, ML theory/application, ML system design, behavioural; no debugging round reported | [Interview Query](https://www.interviewquery.com/interview-guides/waymo-machine-learning-engineer), [Exponent](https://www.tryexponent.com/blog/waymo-interview-process) | secondhand |
| Figure AI, AI engineer | RL and imitation-learning fundamentals; a sample prompt trains a PPO policy for navigation | [Dataford](https://dataford.io/interview-guides/figure-ai/ai-engineer) | prep site, mostly paywalled |
| Reddit, MLE (Jul 2026) | Two DSA rounds plus ML knowledge; no debugging round | [PracHub](https://prachub.com/interview-experiences/reddit-machine-learning-engineer-interview-experience-two-dsa-rounds-15455eb2df) | secondhand |

Nothing came up for Physical Intelligence.

## What these rounds reward (from the prep material)

- The **quiet bugs**: a missing `zero_grad()`, softmax applied before a loss that expects logits, labels shuffled apart from inputs, a validation loop that builds a graph, wrong tensor shapes or dtypes for the loss ([DataInterview: fix the training loop](https://www.datainterview.com/courses/deep-learning/fix-training-loop), [debug PyTorch](https://www.datainterview.com/courses/pytorch/debug-pytorch)).
- **Method over memory**: trace a NaN to the op that creates it; overfit a single batch first; check that the initial loss is about ln(C) for C classes; use synthetic data to separate model bugs from data bugs ([PyCon DE 2023, "Honey, I broke the PyTorch model"](https://pycon.de/archive/2023/talks/honey-i-broke-the-pytorch-model-debugging-custom-pytorch-models-in-a-structured-manner/)).
- **Proving the fix**: saying how you would show each fix worked.

## What this means for ReadCode

- The ML debugging round is real at frontier labs and spreading to startups; it is the closest existing format to ReadCode. It is usually **a transformer or a training loop with several planted bugs**, in PyTorch, in about an hour, followed by an extension task.
- Big-company loops (Waymo, Google-style) still weight coding and ML system design; debugging there shows up inside system design and "ML theory/application" discussions.
- Robot-learning companies' processes are barely documented publicly: an opening for interview reports gathered by ReadCode itself.

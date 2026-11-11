# Robot Learning Engineer, Manipulation

*Generic posting written for this problem. Not any real company's text.*

**Team:** Manipulation Learning · **Location:** on-site, with time in the robot lab every week · **Level:** mid to senior

## About the role

We build general-purpose manipulation for warehouse and light-assembly cells. Our policies learn from human demonstrations: operators teleoperate our arms through leader-follower rigs, we turn those sessions into training data, and the policies we train go back onto the same arms. You will own a large part of that loop, from the moment a demonstration is recorded to the moment a policy is graded on hardware.

## What you'll do

- **Own the demonstration data pipeline.** Turn raw teleop recordings (arm state, leader commands, several cameras, each a separate stream at its own rate) into clean, aligned training episodes. Write the loaders, synchronisation, filtering and dataset tooling the whole team trains from, and make sure what the policy sees in training is what it sees on the robot.
- **Train imitation-learning policies.** Behaviour cloning with action chunking, transformer and diffusion policies, in PyTorch. Ablate architectures, action representations and observation sets.
- **Evaluate on real hardware.** Design evaluation protocols on physical cells, run them, and close the gap between offline metrics and closed-loop success. When a policy that looks fine offline misbehaves on the robot, you find out why.
- **Improve data collection.** Work with the teleop operators and the hardware team on rigs, recording software and operator guidelines so that new demonstrations are useful from day one.
- **Keep the pipeline honest.** Tests, data-quality checks and dashboards that catch silent problems before they cost a week of robot time.

## What we're looking for

- 3+ years writing production-quality Python; strong PyTorch.
- Hands-on experience training imitation-learning or offline policies for real robots (behaviour cloning, ACT-style chunking, diffusion policy, VLA fine-tuning or similar).
- Experience with robot data: timestamps, multi-rate sensors, coordinate frames, calibration, and the ways they go wrong.
- You have debugged a policy on hardware and can tell a modelling problem from a data problem.
- Comfortable in a lab: you can run your own evaluations on an arm, safely.

## Nice to have

- ROS 2 or a similar robotics middleware; experience with teleoperation systems or VR teleop.
- Simulation (MuJoCo, Isaac) for evaluation or data augmentation; sim-to-real experience.
- Large-scale training (multi-GPU, data loaders that keep up with them).
- Reinforcement-learning fine-tuning of pretrained policies.

## How we interview

A conversation about a robot-learning project you shipped; a practical session reading and debugging a piece of our-style training code; a system-design discussion about a data pipeline; a lab visit.

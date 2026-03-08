## **OpenEnv Hackathon Participant Guide**

Welcome to the [OpenEnv Hackathon](https://cerebralvalley.ai/e/open-env-hackathon), hacker! 👋 We’re thrilled to have you on board.

This guide is your all-in-one resource for the event, including schedule, rules, technical resources, problem statements, judging information, and more. Please read this carefully; most answers can be found here.

## **1. Join the [PyTorch Discord Server](https://discord.gg/VBcf6VtfY6)**

- You’ll be given a Hackathon Participant role by an admin, which will give you access to the hackathon-specific channels.

- Here, you’ll be able to interact with hackers and sponsors, introduce yourselves, and form teams (for a maximum team size of **3**).

- If you don't receive your role within **24 hours of joining,** please ping @CV.

- Please submit your Discord username below so we can grant you the role

[linkEmbed]

## **2. Location**

**|** Shack15 (1 Ferry Building, Suite 201, San Francisco CA. 94111)

- **Venue Access:** Shack15 is on the 2nd floor of the Ferry Building. Go up the Ferry Building elevator to the second floor, and turn left. Here you will see the main entrance to Shack15. 

- **Parking:** Parking near the Ferry Building is extremely limited. Consider parking farther out and taking Uber, Lyft, or Public Transportation. 

[youtube]

## **3. WiFi Information**

- **Username:** SHACK15_Members

- **Password:** M3mb3r$4L!f3

## **4. Hackathon Schedule**

**Saturday, March 7 (Outline)**

- **9:00 AM:** Doors Open •󠁏 Breakfast Served •󠁏 Team Formation

- **10:00 AM – 11:30AM**: Kick-off presentations with Meta, Hugging Face, UC Berkeley, CoreWeave, OpenPipe, Unsloth AI, Fleet AI, Mercor, Scaler AI Labs, Snorkel AI, Patronus AI, Halluminate and Scale AI

- **11:30 AM:** Hacking Begins

- **1:00 PM:** Lunch Served

- **6:00 PM:** Dinner Served

- **10:00 PM:** Doors Close •󠁏 Re-entry not permitted

**Sunday, March 8 (Outline)**

- **9:00AM:** Doors Open •󠁏 Breakfast Served

- **1:00PM:** Hacking stops •󠁏 Submissions Due

- **1:15PM:** First Round Judging Begins

- **2:00PM:** Lunch Served

- **3:00PM:** Final Round Judging Begins

- **4:00PM:** Winners Announced and Closing

- **5:00PM:** Doors Close

## **5. Hackathon and Submission Rules**

To keep things fair and aligned with our goals, all teams must follow these rules:

- **Open Source:** Please ensure your repository is public.

- **New Work Only:** All projects must be started from scratch during the hackathon with no previous work.

- **Team Size:** Teams may have up to **3** members.

- **Banned Projects:** Projects will be disqualified if they: violate legal, ethical, or platform policies, use code, data, or assets you do not have the rights to.

- Your project **must** use OpenEnv (stable release 0.2.1) deployed on HF spaces

- You must show a minimal training script for your environment using Unsloth or HF TRL in Colab.

- You must upload a **one minute** demo video to YouTube talking about your submission.

## **6. Hackathon Problem Statements**

Your project must address at least **one of the five** required problem statements.

- Some problem statements include **optional partner-sponsored sub-problem statements**, which are additional focus areas related to the main theme.

- Your project may align with **multiple partner sub-problem statements**, but you can only be **judged for a maximum of two**. Please **select up to two** when submitting.

- Projects that match these partner sub-problem statements are eligible for **extra partner prizes**, judged separately from the main track winners.

- Each partner sub-problem statement carries a prize of **$10,000 USD**.

**Statement 1: Multi-Agent Interactions**

Environments for this theme involve cooperation, competition, negotiation, and coalition formation. Learning from these environments will enable agents to model the beliefs and incentives of others in partially observable settings. This drives theory-of-mind reasoning and emergent strategic behavior.

- **Expected Outcome:** an environment that can be used to train multi-agent task handling in a LLM

- **Example Environments:** Market simulations, compute-allocation negotiations, collaborative puzzle worlds, mixed cooperative/competitive strategy games.

- **Partner Sub-Themes:**

  - **Fleet AI:** Scalable Oversight: Environments that train oversight agents to monitor, analyze, and explain the behavior of other AI agents operating in complex, multi-agent settings.
  - **Halluminate:** Multi-Actor Environments: Build a realistic environment where an agent interacts with and manages multiple actors (agents) to discover and achieve the task

**Statement 2: (Super) Long-Horizon Planning & Instruction Following**

You will build environments that require deep, multi-step reasoning with sparse or delayed rewards. After using these environments, the goal is to enable agents to decompose goals, track state over extended trajectories, and recover from early mistakes. The aim is to push beyond shallow next-token reasoning toward structured planning and durable internal representations. 

- **Expected Outcome:** an environment that can capture and improve LLM behaviour on challenging long horizon tasks that need long running sessions beyond context memory limits. 

- **Example Environments:** Research-planning simulators, large-scale codebase refactoring tasks, strategic resource management worlds, long-horizon logistics optimization, extremely complicated long-horizon instruction following (e.g., 300 instructions scattered around).

- **Partner Sub-Themes:**

  - **Mercor:** Make an environment with capped/uncapped rewards where frontier model rewards scale with token output.

  - **Scale AI:** Environments for long horizon workflows for non-code use cases within a business setting: focusing on either Sales, Project management, or HR & IT.

**Statement 3: World Modeling**

- **Statement 3.1: Professional Tasks:** Here you will develop environments that require real interaction with tools, APIs, or dynamic systems where the model is expected to do real hard work instead of exploiting short-cuts to arrive at the desired outcome. Learning from these environments will enable agents to maintain consistent internal state, update beliefs based on outcomes, and orchestrate multi-step workflows. The goal is to strengthen causal reasoning and persistent world models.

  - **Expected Outcome:** an environment capturing nuances of a defined partially observable world and improve LLM interaction with it

  - **Example Environments:** Dynamic browser/API ecosystems, enterprise applications, scientific workflow loops (papers → code → experiments), economic simulations with feedback, tool-discovery benchmarks.

  - **Partner Sub-Theme:**

    - **Scaler AI Labs:** Multi-App RL Environment for Enterprise Workflows: Create RL environments to demonstrate complex workflows, business rule nuances etc in a large enterprise

- **Statement 3.2: Personalized Tasks:** Here we will develop an environment that offers real personalized task handling, imagine replying to personal messages or handling dinner conflicts due to work conflicts, replying to tough emails. Think any personal assistant tasks.

  - **Expected Outcome:** An environment that gives the model a realistic simulation of handling personal tasks, conflicts and managing them as delegations

  - **Example Environments:** Executive Assistant Meeting Planner, Dinner and drive planning, email and message replying, etc

  - **Partner Sub-Theme:**

    - **Patronus AI:** Consumer Workflows with Schema Drift: Multi-step consumer workflow environments where the underlying data schemas, API contracts, and t&cs/policies/rules change.

**Statement 4: Self-Improvement**

The focus here is to create environments where agents can learn to generate new challenges, escalate difficulty, and improve through self-play or adaptive curricula. Rather than optimizing fixed tasks, the goal is for agents to learn to drive their own capability growth. The objective is recursive skill amplification.

- **Expected Outcome:** an environment for improving self-play of a LLM over a defined set of tasks

- **Example Environments:** Self-play negotiation arenas, auto-generated math/proof tasks, evolving coding competitions, adaptive RL curricula.

- **Partner Sub-Theme:**

  - **Snorkel AI:** Simulated Experts-in-the-Loop: Environment that simulates interactions with real subject-matter experts, with changing requirements / preferences.

**Statement 5: Wild Card - Impress Us!**

We do not want to limit your focus if your idea doesn’t fit the boxes above, we want and WILL reward out of box tasks, please be creative but remember to add submissions that meaningfully add value to LLM training on a certain task. 

## **7. CV Hackathon Winners**

[linkEmbed]

## **8. OpenEnv Provided Resources**

**Please read through the entire slideshow here. This includes:**

- OpenEnv Fundamentals, Architecture
- Local Dev, Docker, and HF Spaces Deployment
- OpenEnv in Practice
- Training (TRL & Unsloth)
- How-to-Access-Infrastructure (including GPU Request Form)

[linkEmbed]

## **9. Partner Provided Resources**

- **Unsloth AI Resources**
  - <https://unsloth.ai/docs/get-started/unsloth-notebooks#grpo-reasoning-rl-notebooks>
- **Mercor Resources**
  - Dataset: <https://huggingface.co/datasets/mercor/apex-agents>
  - Archipelago repo to run the eval: <https://github.com/Mercor-Intelligence/archipelago>
  - APEX-Agents paper: <https://arxiv.org/abs/2601.14242>
- **Hugging Face Resources**
  - **$30** in Compute and Inference Credits, **details on provisioning will be added here on the day of.**
- **Cursor Resources**
  - **$50** in Cursor Credits, **details on provisioning will be added here on the day of.**

## **10. Judging & Submissions**

Judges will be taking place on **Sunday, March 8**. These judges are evaluating your **technical demos** in the following categories. *Show us what you have built* to solve our problem statements. Please **do not** show us a presentation. We'll be checking to ensure your project was built **entirely during the event**; no previous work is allowed. 

**|** **Teams should submit [here](https://cerebralvalley.ai/e/openenv-hackathon-sf/hackathon/submit) when they have completed hacking.** In the submission form, you will have to upload a **one minute** demo video on YouTube talking about your submission. You must also show a minimal training script for your environment using Unsloth or HF TRL in Colab.

**Please ensure your project uses** use OpenEnv (stable release 0.2.1) deployed on HF spaces.

[linkEmbed]

**Judging Criteria**

- **Environment Innovation (40%) -** Is the environment novel, creative, or challenging? Does it meaningfully test the agent’s behavior?
- **Storytelling (30%) -** Does the team clearly explain the problem, environment, and agent behavior? Is the demo engaging and easy to follow?
- **Training Script Showing Improvement in Rewards (20%) -** Does the demo provide observable evidence of training progress (reward curves, metrics, or before/after behavior)? 
- **Reward and Training Pipeline Setup (10%) -** Is the reward logic coherent, and does the pipeline produce meaningful improvement in the agent’s inference (how it acts in the environment)?

**Judging Process**

**|** Judging proceeds in two rounds:

- Hackers will be assigned groups of judges; \~3 minutes to pitch followed by 1-2 minutes of Q/A

- The top **six** teams in ranking will get to demo on stage to a panel of judges; \~3 minutes to pitch followed by 2-3 minutes for Q/A.

## **11. Prizes**

- **1st Place:** $15,000 USD Cash

- **2nd Place:** $9,000 USD Cash

- **3rd Place:** $6,000 USD Cash

## **❓If you have any questions, please email [wania@cerebralvalley.ai](mailto:wania@cerebralvalley.ai) or message on Discord.**
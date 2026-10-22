---
type: course
title: "BSc: Reinforcement Learning"
description: "A course covering fundamentals, sample-based learning, and function approximation in reinforcement learning, including MDPs, Q-learning, and Actor-Critic methods."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Reinforcement_Learning"
tags: ["reinforcement-learning", "ai", "machine-learning", "bsc", "course"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Reinforcement_Learning"
    id: "7257"
    title: "BSc: Reinforcement Learning"
    last_modified: "2022-07-13T10:28:52Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:38:04+00:00"
status: draft
stale_after: "2024-07-12T10:28:52+00:00"
duplicate_of: ["/courses/bsc-reinforcementlearning.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSc: Reinforcement Learning

## Reinforcement Learning
- Course name: Reinforcement Learning

### Course Characteristics

#### Key concepts of the class
- Fundamentals of Reinforcement Learning
- Sample-based Learning Methods
- Prediction and Control with Function Approximation

#### What is the purpose of this course?
Harnessing the full potential of artificial intelligence requires adaptive learning systems. Reinforcement learning (RL) is one powerful paradigm for doing so, and it is relevant to an enormous range of tasks, including robotics, game playing, consumer modeling and healthcare.
#### Course objectives based on Bloom’s taxonomy

##### - What should a student remember at the end of the course?
By the end of the course, the students should be able to
- Markov Decision Processes
- Exploration vs. Exploitation
- Value Functions
- Temporal-difference Learning
- Q-learning
- Expected Sarsa
- Actor-Critic

##### - What should a student be able to understand at the end of the course?
By the end of the course, the students should be able to
- How to build an RL system for sequential decision making
- How to formalize a task as an RL problem
- the space of RL algorithms

##### - What should a student be able to apply at the end of the course?
By the end of the course, the students should be able to
- RL for solving real-world problems
- TD-algorithms for estimating value functions
- Expected Sarsa and Q-Learning
- Actor-Critic Method
#### Course evaluation
**Course grade breakdown**

| Type | Points |
| --- | --- |
| Labs/seminar classes | 20 |
| Interim performance assessment | 50 |
| Exams | 30 |

#### Grades range
**Course grading range**

| Grade | Points |
| --- | --- |
| A. Excellent | 85-100 |
| B. Good | 70-84 |
| C. Satisfactory | 55-69 |
| D. Poor | 0-54 |

#### Resources and reference material
- Reinforcement Learning: An Introduction, Sutton and Barto, 2nd Edition.
- Reinforcement Learning: State-of-the-Art, Marco Wiering and Martijn van Otterlo, Eds
### Course Sections
The main sections of the course and approximate hour distribution between them is as follows:
#### Section 1

##### Section title
Fundamentals of Reinforcement Learning

##### Topics covered in this section
- Sequential Decision Making
- Markov Decision Processes
- Value Functions & Bellman Equations
- Dynamic Programming for Value Function

##### What forms of evaluation were used to test students’ performance in this section?
| Form | Yes/No |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 1 |
| Reports | 0 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

##### Typical questions for ongoing performance evaluation within this section
1. What is sequential decision making?
1. What is exploration vs. exploitation trade-off in sequential decision making?
1. What are Markov Decision Processes?
1. What is the difference between episodic and continuous tasks?
1. What are policies, value functions and Bellman equations?
1. How to use dynamic programming to compute value functions and optimal policies?

##### Typical questions for seminar classes (labs) within this section
1. What are the strengths and weaknesses of different exploration algorithms?
1. What is an epsilon greedy agent?
1. How to translate a real-world problem into a Markov Decision Process?
1. Why Bellman equations?
1. What is generalized policy iterations?

##### Tasks for midterm assessment within this section
1. Suppose you are given two action-value functions corresponding to the action-value function of an arbitrary, fixed policy under the two reward functions. Using the Bellman equation, explain if it is possible or not to combine these value functions in a simple manner to obtain a new action-value function corresponding to a single reward function r.

##### Test questions for final assessment in this section
1. How to implement incremental algorithms for estimating action-values? 
1. How to implement and test an epsilon-greedy agent?
1. Create an example of your own that will fit into Markov Decision Processes framework
1. How to use optimal values functions to get optimal policies?
1. How to implement an efficient dynamic programming agent?
#### Section 2

##### Section title
Sample Based Learning

##### Topics covered in this section
- Monte Carlo Methods for Prediction and Control
- Temporal Difference Learning
- Planning Learning and Acting
- Expected Sarsa
- Q-Learning
- On-policy Off-policy Control

##### What forms of evaluation were used to test students’ performance in this section?
| Form | Yes/No |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 1 |
| Reports | 0 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

##### Typical questions for ongoing performance evaluation within this section
1. How to estimate value functions and optimal policies, using only sampled experience from the environment?
1. What is Monte Carlo?
1. What is off-policy?
1. What is Temporal Difference Learning?
1. What is Q-Learning?
1. What is Expected Sarsa?
1. What is model-based RL?
1. What is Random-Tabular Q-planning?

##### Typical questions for seminar classes (labs) within this section
1. How to use Monte Carlo for Prediction and Action values?
1. How to use Monte Carlo for generalized policy iteration?
1. What is Batch RL and how does it work?
1. How to implement Expected Sarsa and Q-Learning?
1. What is Dyna Architecture and Dyna Algorithm?

##### Tasks for midterm assessment within this section
1. Given a Q-Learning algorithm,
1. Draw the one-step backup diagram of the algorithm and write out its update rule 
1. Is this algorithm on-policy or off-policy? Justify your answer. 
1. Write the two-step version of the algorithm.

##### Test questions for final assessment in this section
1. Why does off-policy matter?
1. How to learn from agent’s interaction with the world?
1. What is the difference between methods of on-policy and off-policy control? 
1. How is Q-Learning off-policy?
#### Section 3

##### Section title
Prediction and Control with Function Approximation

##### Topics covered in this section
- On-policy Prediction with Approximation
- Neural Networks and TD Learning
- Policy-Gradient Methods
- Actor-Critic

##### What forms of evaluation were used to test students’ performance in this section?
| Form | Yes/No |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 1 |
| Reports | 0 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

##### Typical questions for ongoing performance evaluation within this section
1. How to estimate a value function for a given policy for a large number of states?
1. How to specify a parametric form of the value function?
1. How to frame value estimation as supervised learning problem?
1. How can we learn features for RL?
1. How can we learn policies directly?
1. What are the advantages of policy parameterization?
1. What is Actor-Critic Method?

##### Typical questions for seminar classes (labs) within this section
1. How to define the Value Error objective?
1. How to implement gradient Monte for policy evaluation?
1. How to solve an infinite state prediction task with NN and TD?
1. How to estimate the policy gradient?
1. How to implement Actor-Critic?

##### Tasks for midterm assessment within this section
1. What are policy learning and actor critic networks?
1. What is TD learning?
1. Given two function approximators, which discretize the state space in two different ways, we want to use the approximators to estimate the value function of a fixed policy, using on-policy data. Suppose you have a small number of samples. Explain the impact that you expect to see on the two algorithm by using TD with different values of lambda.

##### Test questions for final assessment in this section
1. How to frame value estimation as supervised learning problem?
1. What is semi-gradient TD?
1. What is the Policy-Gradient theorem?

<!-- catix:relations -->
## Relations

- Duplicate of (the page edited last): [BSc: ReinforcementLearning](/courses/bsc-reinforcementlearning.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Reinforcement Learning](https://eduwiki.innopolis.university/index.php/BSc%3A_Reinforcement_Learning), revision 7257

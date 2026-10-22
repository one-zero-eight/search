---
type: course
title: "Behavioral and Cognitive Robotics"
description: "A course on autonomous robotics covering embodied cognition, evolutionary and reinforcement learning, and practical implementation using simulation tools."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3ABehavioralAndCognitiveRobotics"
tags: ["robotics", "ai", "machine-learning", "cognitive-science", "course"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3ABehavioralAndCognitiveRobotics"
    id: "179"
    title: "MSc:BehavioralAndCognitiveRobotics"
    last_modified: "2021-08-02T06:30:52Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:43:33+00:00"
status: draft
stale_after: "2023-08-02T06:30:52+00:00"
---

# Behavioral and Cognitive Robotics

[C:FundamentalsRobotControl]

- **Course name:** Behavioral and Cognitive Robotics
- **Course number:**

### Course Characteristics

### What subject area does your course (discipline) belong to?

Robotic control; Artificial Intelligence; Cognitive Science; Machine Learning.

#### Key concepts of the class

- Behavior and cognition as complex dynamical systems
- Embodied cognition
- Machine learning methods for robotics

#### What is the purpose of this course?

The course illustrates the fundamental principles of robotics with particular reference to autonomous robotics: embodiment and situatedness, morphological computation, sensory-motor coordination, robustness, emergence, multi-levels and multi-scale organizations, compositionality, integration between behavioral and cognitive skill, anticipation, and internal models. Students will learn how to program robots and how to design robots that develop their behavioral and cognitive skills autonomously, in interaction with the environment, through evolutionary and reinforcement learning algorithms. This will be realized through the illustration of concrete examples taken from state of the art research and through practical experimentation carried in simulation.

#### Course objectives based on Bloom’s taxonomy

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to remember and recognize

- What makes situated and embodied system different from other AI applications
- The importance of sensory-motor coordination and morphological computation
- The advantage and drawbacks of adaptive methods and of methods based on hand-design
- The open research issues in autonomous robotics

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to describe and explain

- The importance of the interaction between the body of the robot, the controller of the robot and the environment
- The multi-level and multi-scale organzation of behavior and cognition
- The characteristics of evolutionary, reinforcement learning, and learning by demonstration methods
- The relation of the methods above with supervised learning methods
- The methods that can support long-term adaptation and the synthesis of complex solutions

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to

- Design a controller for a mobile robot capable to perform a simple task
- Evolve a robot for the ability to perform a task by using evolutionary algorithm
- Train a robot for the ability to perform a task by using reinforcement learning algorithm
- Understand applicability of these methods for other sequential decision problems (e.g. recomendation systems, chatbots, educational technologies ext)

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/assignments | 25 | 25 |
| Interim project report | 25 | 25 |
| Final project report | 50 | 50 |

The course grades are given according to the following rules: Labs/assignments = 25 pts, Interim project report = 25 pts, Final project report = 50 pts.

#### Grades range

If necessary, please indicate freely your course’s grading features.

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 |  |
| B. Good | 75-89 |  |
| C. Satisfactory | 60-74 |  |
| D. Poor | 0-59 |  |

#### Resources and reference material

Annotated slides, resources available from https://github.com/snolfi/evorobotpy

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Introduction to autonomous robots | 8 |
| 2 | Behavior | 7 |
| 3 | Cognition | 7 |

#### Section 1

##### Section title:

Introdution to autonomous robots

#### Topics covered in this section:

- Autonomous robots
- From Braitenberg’s vehicles to neuroRobots
- Embodiment
- Situatedness
- Adaptation
- Robustness, Plasticity, and Antifragility

#### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 0 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

#### Typical questions for ongoing performance evaluation within this section

1. Identify the role of sensory-motor coordination in the behavior exhibited by a specific robot
1. Describe an example of morfological computation
1. Describe the differences between evolutionary and reinforcement learning methods
1. Describe the criteria that can be used to design reward functions

#### Typical questions for seminar classes (labs) within this section

1. Implement a simple evolutionary algorithm in python
1. Familiarize with the OpenAI Gym environment
1. Evolve a robot by using the evorobotpy tool
1. Train by using a reinforcement learning algorithm included in the baseline tool

#### Test questions for final assessment in this section

1. Use the evolutionary algorithm implemented to evolve a solution for pole-balancing problem
1. Analyze the impact of an hyper-parameter on the course of the learning process
1. Analyze the impact of an atchitecture of the policy on the course of the learning process

#### Section 2

##### Section title:

Behavior

#### Topics covered in this section:

- Behavior as a complex adaptive system
- Swarm robotics
- Coordination, communication and self-organization in collected behavior
- Behavior arbitration and affordances

#### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 0 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

#### Typical questions for ongoing performance evaluation within this section

1. Describe the role of positive and negative feedbacks in self-organized behaviors
1. Describe the different mechanisms supporting behavior arbitration
1. Describe examples of fixed point, limit cycle, and strange attractor behaviors

#### Typical questions for seminar classes (labs) within this section

1. Implement a new Gym environmental problem
1. Analyze the impact of alternative reward functions
1. Design a reward function

#### Test questions for final assessment in this section

1. Train a robot for the ability to perform multiple behaviors
1. Design an experimental setup supporting the evolution of cooperation and specialization
1. Implement a procedure capable to self-select usefull learning experience

#### Section 3

##### Section title:

Cognition

##### Topics covered in this section:

- Symbols and Language
- Prerequisites for the development of cognitive skills
- Integration between behavioral and cognitive skills
- Learning by demonstration
- Internal Models
- Long-term adaptation

#### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 0 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

#### Typical questions for ongoing performance evaluation within this section

1. Describe the advantage and the limits of sensory-motor coordination
1. Describe the processes supporting the evolution of signals and meanings in communication
1. Illustrate the symbol-grounding problem

##### Typical questions for seminar classes (labs) within this section

1. Compare the solutions synthesized through reactive and recurrent neural policy
1. Analyze the role played by sensory fusion
1. Analyze the importance of normalization techniques in reinforcement learning

##### Test questions for final assessment in this section

1. Implement an auto-associative network to extract compressed visual features
1. Implement an anticipatory models that permit to handle the temporal lack of sensory information
1. Compare the efficacy of vanilla and regulatory neural network policy

# Citations

1. [MSc:BehavioralAndCognitiveRobotics](https://eduwiki.innopolis.university/index.php/MSc%3ABehavioralAndCognitiveRobotics), revision 179

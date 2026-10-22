---
type: course
title: "BSc: Game Theory"
description: "Course covering mathematical game theory concepts like Nash Equilibrium and Evolutionary Game Theory, including practical implementation of game-playing agents."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Game_Theory"
tags: ["game-theory", "ai", "mathematics", "programming", "bsc"]
aliases: ["BSc:GameTheory"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Game_Theory"
    id: "7251"
    title: "BSc: Game Theory"
    last_modified: "2022-07-13T08:02:08Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:17:39+00:00"
status: draft
stale_after: "2024-07-12T08:02:08+00:00"
prerequisites: [{"course": "/courses/bsc-analytic-geometry-and-linear-algebra-ii.md", "as_written": "[CSE204 — Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md): real vector and matrix operations, convex hull and span."}, {"course": "/courses/bsc-probability-and-statistics.md", "as_written": "[CSE206 — Probability And Statistics](/courses/bsc-probability-and-statistics.md): probability distribution and mean function."}, {"course": "/courses/bsc-mathematical-analysis-i.md", "as_written": "[CSE201 — Mathematical Analysis II](/courses/bsc-mathematical-analysis-i.md): extreme values of differentiable functions."}, {"course": "/courses/bsc-logic-and-discrete-mathematics.md", "as_written": "[CSE113 — Philosophy I - (Discrete Math and Logic)](/courses/bsc-logic-and-discrete-mathematics.md): paths in directed acyclic weighted graphs."}]
taught_by: ["/people/josephbrown.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSc: Game Theory

## Game Theory
- **Course name**: Game Theory
- **Code discipline**: R-01
- **Subject area**: 

### Short Description
This course covers the following concepts: Game Theory: Basics of the mathematical theory of games, including Nash Equilibrium, Mixed Strategies, and Evolutionary Game Theory; Applications of Computer Programming: Implementation of Game Playing agents.

### Prerequisites

#### Prerequisite subjects
- [CSE204 — Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md): real vector and matrix operations, convex hull and span.
- [CSE206 — Probability And Statistics](/courses/bsc-probability-and-statistics.md): probability distribution and mean function.
- [CSE201 — Mathematical Analysis II](/courses/bsc-mathematical-analysis-i.md): extreme values of differentiable functions.
- [CSE113 — Philosophy I - (Discrete Math and Logic)](/courses/bsc-logic-and-discrete-mathematics.md): paths in directed acyclic weighted graphs.

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Domination and Nash | # 2 by 2 classical games (Chicken, Prisoner’s dilemma, Battle of the Sexes, coin flips) <br> # n by m games and methods of reduction <br> # Domination and Nash Equilibrium <br> # Game Tree Roll Out |
| Advanced strategics | # Multiple player and random player games <br> # Higher level Strategic planning including - Shelling’s theory of credible threats and promises <br> # Introduction to Evolutionary Game theory |
| Tournament and Agents | # Agent players <br> # Computer Tournaments and Evolutionary Tournaments |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
Game Theory is a powerful method to make predictive decisions about common business cases and acts as a foundational course to decision making in AI systems, such as Bayesian techniques and game trees and Monte Carlo Tree Search. As such the purpose of this course is to provide a solid foundation on the basic structures of mathematical games including the canonical 2 by 2 structures of the Prisoner’s Dilemma, Chicken, Hawk and Dove, and Battle of the Sexes. Then looks at more complicated business examples such as price setting, making creditable threats and promises. It also gives practical instruction on the application of computers in game playing, especially tournament play and development of decision making models.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Should be able to define Nash Equilibrium, Domination, Mixed v. Pure Strategies
- Should be able to define Evolutionary Stability
- Should be able to define a number of common agent types (always cooperate/defect, Tit-for-tat, Grudger)

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- A student should understand how game theory affects common daily situations, such as internet trade (as a PD)
- Should understand the role of Evolutionary Stable Strategies
- Should understand the history of tournaments as methods to evaluate agent play

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Program a finite state machine to play iterated games
- Apply both domination and Nash equilibrium to solve pure games
- Apply both domination, Nash equilibrium, and mixed strategies to solve mixed strategic games 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 90-100 | - |
| B. Good | 75-89 | - |
| C. Satisfactory | 60-74 | - |
| D. Poor | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 10 |
| Interim performance assessment | 40 |
| Midterm and Exam | 50 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Andrew McEachern, Game Theory : A Classical Introduction, Mathematical Games, and the Tournament
- Thomas Schelling, Strategy and Conflict
- William Poundstone, Prisoner’s Dilemma

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 |
| --- | --- | --- | --- |
| Homework and group projects | 1 | 1 | 1 |
| Midterm evaluation | 1 | 0 | 0 |
| Testing (written or computer based) | 1 | 1 | 1 |
| Oral polls | 1 | 0 | 1 |
| Discussions | 1 | 1 | 1 |
| Development of individual parts of software product code | 0 | 1 | 1 |
| Reports | 0 | 0 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is an externality in PD? | 1 |
| Question | Give the Nash Equilibrium of an example 2 by 2 game | 1 |
| Question | Give the Domination in an example n by m game | 1 |
| Question | What is the payoff matrix for a given game | 1 |
| Question | List and example the set of externalities of PD | 0 |
| Question | Worked examples of Nash Equlibrium | 0 |
| Question | Worked examples of Domination | 0 |
| Question | Given the payoff matrix for a given game, what is the outcome of play. | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Using Domination and Nash Equilibrium find a mixed strategy solution for a given game. | 1 |
| Question | How does this game differ if we only allow for pure strategies rather than mixed? | 1 |
| Question | What is the difference between Evolutionary Stable Strategies and Dominator Theory | 1 |
| Question | What is the ESS for an Iterated Prisoner’s Dilemma? | 1 |
| Question | Why does IPD not have a clear Nash Equilibrium and why should we use a Evolutionary Stable Strategies | 0 |
| Question | Show the finite state representation for TFT | 0 |
| Question | Demonstrate the Outcome of a population of half ALLC and half ALLD | 0 |
| Question | Demonstrate the Best Response method on an example matrix | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Define the meaning of a lock box. | 1 |
| Question | Define the meaning of a nice strategy. | 1 |
| Question | How can we make a strategy more cooperative by changing its structure? | 1 |
| Question | Give a listing of IPD agents and a short description of their ruleset | 1 |
| Question | Program a finite state machine for IPD which implements a Lock Box | 0 |
| Question | What properties does a finite state machine have (i.e. is it nice) | 0 |
| Question | If a state machine is nice - what does it’s transitions matrix look like? | 0 |
| Question | How can a 3 and 4 state lockbox reach cooperation? | 0 |
#### Final assessment
**Section 1**
1. List and example the set of externalities of PD
1. Worked examples of Nash Equilibrium and Domination
1. Given the payoff matrix for a given game, what is the outcome of play.
1. A button is put before you. If you don’t press the button you get a low passing grade on this question. If you press the button and less than half the class presses the button you get a high passing grade for this question. If more than half the class presses the button then those who press the button get a failing grade for this question. Do you press the button?
**Section 2**
1. Simulate the IPD, does the ESS occur?
1. When the time-line of an ESS is extended but we include the restriction of a finite space, what happens to the equilibriumum
1. Demonstrate the Best Response method on an example matrix
**Section 3**
1. Show a working finite state machine IPD model of Trifecta.
1. Create a Tournament agent to compete against your classmates for a given game.
1. Given a set of players for an IPD model, what is the most likely equilibrium outcome, explain.

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

<!-- catix:relations -->
## Relations

- Prerequisites: [BSc: Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md) ([CSE204 — Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md): real vector and matrix operations, convex hull and span.); [BSc: Probability And Statistics](/courses/bsc-probability-and-statistics.md) ([CSE206 — Probability And Statistics](/courses/bsc-probability-and-statistics.md): probability distribution and mean function.); [BSc: Mathematical Analysis I](/courses/bsc-mathematical-analysis-i.md) ([CSE201 — Mathematical Analysis II](/courses/bsc-mathematical-analysis-i.md): extreme values of differentiable functions.); [Logic and Discrete Mathematics (CSE113)](/courses/bsc-logic-and-discrete-mathematics.md) ([CSE113 — Philosophy I - (Discrete Math and Logic)](/courses/bsc-logic-and-discrete-mathematics.md): paths in directed acyclic weighted graphs.)
- Taught by: [Joseph Brown](/people/josephbrown.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Game Theory](https://eduwiki.innopolis.university/index.php/BSc%3A_Game_Theory), revision 7251

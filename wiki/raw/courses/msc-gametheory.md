---
type: course
title: "Game Theory"
description: "Course R-01 covering mathematical game theory, Nash Equilibrium, and AI agent implementation, including course objectives, evaluation methods, and section breakdowns."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3AGameTheory"
tags: ["game-theory", "ai", "course", "msccs", "innopolis"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3AGameTheory"
    id: "140"
    title: "MSc:GameTheory"
    last_modified: "2021-07-30T11:56:52Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:33:57+00:00"
status: draft
stale_after: "2023-07-30T11:56:52+00:00"
---

# Game Theory

## Game Theory

- **Course name:** Game Theory
- **Course number:** R-01

### Course Characteristics

#### Key concepts of the class

- Game Theory: Basics of the mathematical theory of games, including Nash Equilibrium, Mixed Strategies, and Evolutionary Game Theory
- Applications of Computer Programming: Implementation of Game Playing agents

#### What is the purpose of this course?

Game Theory is a powerful method to make predictive decisions about common business cases and acts as a foundational course to decision making in AI systems, such as Bayesian techniques and game trees and Monte Carlo Tree Search. As such the purpose of this course is to provide a solid foundation on the basic structures of mathematical games including the canonical 2 by 2 structures of the Prisoner’s Dilemma, Chicken, Hawk and Dove, and Battle of the Sexes. Then looks at more complicated business examples such as price setting, making credible threats and promises. It also gives practical instruction on the application of computers in game playing, especially tournament play and the development of decision-making models.

#### Course objectives based on Bloom’s taxonomy

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to give basic definitions of games

- Should be able to define Nash Equilibrium, Domination, Mixed v. Pure Strategies
- Should be able to define Evolutionary Stability
- Should be able to define a number of common agent types (always cooperate/defect, Tit-for-tat, Grudger)

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to understand the basic

- A student should understand how game theory affects common daily situations, such as internet trade (as a PD)
- Should understand the role of Evolutionary Stable Strategies
- Should understand the history of tournaments as methods to evaluate agent play

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to apply game theory to solve problems in limited real world cases.

- Program a finite state machine to play iterated games
- Apply both domination and Nash equilibrium to solve pure games
- Apply both domination, Nash equilibrium, and mixed strategies to solve mixed strategic games

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 10 |  |
| Interim performance assessment | 40 |  |
| Midterm and Exam | 50 |  |

If necessary, please indicate freely your course’s features in terms of students’ performance assessment.

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 |  |
| B. Good | 75-89 |  |
| C. Satisfactory | 60-74 |  |
| D. Poor | 0-59 |  |

If necessary, please indicate freely your course’s grading features.

#### Resources and reference material

- Andrew McEachern, Game Theory : A Classical Introduction, Mathematical Games, and the Tournament
- Thomas Schelling, Strategy and Conflict
- William Poundstone, Prisoner’s Dilemma

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Domination and Nash | 16 |
| 2 | Advanced strategics | 16 |
| 3 | Tournament and Agents | 16 |

#### Section 1

##### Section title:

Domination and Nash

#### Topics covered in this section:

- 2 by 2 classical games (Chicken, Prisoner’s dilemma, Battle of the Sexes, coin flips)
- n by m games and methods of reduction
- Domination and Nash Equilibrium
- Game Tree Roll Out

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| :--- | :--- | :--- |
| Development of individual parts of software product code | 0 | |
| Homework and group projects | 1 | |
| Midterm evaluation | 1 | |
| Testing (written or computer based) | 1 | |
| Reports | 0 | |
| Essays | 0 | |
| Oral polls | 1 | |
| Discussions | 1 | |

#### Typical questions for ongoing performance evaluation within this section

1. What is an externality in PD?
2. Give the Nash Equilibrium of an example 2 by 2 game
3. Give the Domination in an example n by m game
4. What is the payoff matrix for a given game

#### Typical questions for seminar classes (labs) within this section

1. List and example the set of externalities of PD
2. Worked examples of Nash Equlibrium
3. Worked examples of Domination
4. Given the payoff matrix for a given game, what is the outcome of play.

#### Test questions for final assessment in this section

1. List and example the set of externalities of PD
2. Worked examples of Nash Equilibrium and Domination
3. Given the payoff matrix for a given game, what is the outcome of play.
4. A button is put before you. If you don’t press the button you get a low passing grade on this question. If you press the button and less than half the class presses the button you get a high passing grade for this question. If more than half the class presses the button then those who press the button get a failing grade for this question. Do you press the button?

#### Section 2

##### Section title:

Advanced strategics

#### Topics covered in this section:

- Multiple player and random player games
- Higher level Strategic planning including - Shelling’s theory of credible threats and promises
- Introduction to Evolutionary Game theory

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| :--- | :--- | :--- |
| Development of individual parts of software product code | 1 | |
| Homework and group projects | 1 | |
| Midterm evaluation | 0 | |
| Testing (written or computer based) | 1 | |
| Reports | 0 | |
| Essays | 0 | |
| Oral polls | 0 | |
| Discussions | 1 | |

#### Typical questions for ongoing performance evaluation within this section

1. Using Domination and Nash Equilibrium find a mixed strategy solution for a given game.
2. How does this game differ if we only allow for pure strategies rather than mixed?
3. What is the difference between Evolutionary Stable Strategies and Dominator Theory
4. What is the ESS for an Iterated Prisoner’s Dilemma?

#### Typical questions for seminar classes (labs) within this section

1. Why does IPD not have a clear Nash Equilibrium and why should we use a Evolutionary Stable Strategies
2. Show the finite state representation for TFT
3. Demonstrate the Outcome of a population of half ALLC and half ALLD
4. Demonstrate the Best Response method on an example matrix

#### Test questions for final assessment in this section

1. Simulate the IPD, does the ESS occur?
2. When the time-line of an ESS is extended but we include the restriction of a finite space, what happens to the equilibriumum
3. Demonstrate the Best Response method on an example matrix

#### Section 3

##### Section title:

Tournament and Agents

##### Topics covered in this section:

- Agent players
- Computer Tournaments and Evolutionary Tournaments

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| :--- | :--- | :--- |
| Development of individual parts of software product code | 1 | |
| Homework and group projects | 1 | |
| Midterm evaluation | 0 | |
| Testing (written or computer based) | 1 | |
| Reports | 1 | |
| Essays | 0 | |
| Oral polls | 1 | |
| Discussions | 1 | |

#### Typical questions for ongoing performance evaluation within this section

1. Define the meaning of a lock box.
2. Define the meaning of a nice strategy.
3. How can we make a strategy more cooperative by changing its structure?
4. Give a listing of IPD agents and a short description of their ruleset

##### Typical questions for seminar classes (labs) within this section

1. Program a finite state machine for IPD which implements a Lock Box
2. What properties does a finite state machine have (i.e. is it nice)
3. If a state machine is nice - what does it’s transitions matrix look like?
4. How can a 3 and 4 state lockbox reach cooperation?

##### Test questions for final assessment in this section

1. Show a working finite state machine IPD model of Trifecta.
2. Create a Tournament agent to compete against your classmates for a given game.
3. Given a set of players for a IPD model, what is the most likely equilibrium outcome, explain.

# Citations

1. [MSc:GameTheory](https://eduwiki.innopolis.university/index.php/MSc%3AGameTheory), revision 140

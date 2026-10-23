---
type: course
title: "Theoretical Computer Science"
description: "A BSc course covering Automata Theory, Formal Grammars, and Computability, focusing on the theoretical foundations of compilers and computation limits."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Theoretical_Computer_Science"
tags: ["theoretical-computer-science", "automata", "computability", "formal-grammars", "compiler-theory"]
aliases: ["BSc:TheoreticalComputerScience"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Theoretical_Computer_Science"
    id: "7194"
    title: "BSc: Theoretical Computer Science"
    last_modified: "2022-07-12T09:43:55Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T02:23:07+00:00"
status: draft
stale_after: "2024-07-11T09:43:55+00:00"
prerequisite_of: ["/courses/bsc-capstone-project.md", "/courses/bsc-practical-machine-learning-deep-learning.md"]
prerequisites: [{"as_written": "CSE113 Logic and Discrete Mathematics: set theory, inductive definitions and proofs, predicate logic, proof techniques (for example by contradiction, diagonalization...), algebraic structures (preferably)."}]
taught_by: ["/people/andreyfrolov.md", "/people/mansurkhazeev.md", "/people/manuelmazzara.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Theoretical Computer Science

## Theoretical Computer Science
- **Course name**: Theoretical Computer Science
- **Code discipline**: BS-
- **Subject area**: 

### Short Description
This course covers the following concepts: Automata Theory; Formal Grammars; Computability.

### Prerequisites

#### Prerequisite subjects
- CSE113 Logic and Discrete Mathematics: set theory, inductive definitions and proofs, predicate logic, proof techniques (for example by contradiction, diagonalization...), algebraic structures (preferably).

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Automata Theory | # Languages <br> # Finite State Automata <br> # Pushdown Automata <br> # Nondeterminism <br> # Turing Machines |
| Formal Grammars | # Chomsky Hierarchy <br> # Regular Expressions <br> # Relationships with Automata |
| Computability | # Undecidability <br> # Halting Problem <br> # Rice Theorem |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
A good software developer ignorant of how the mechanics of a compiler works is not better than a good pilot when it comes to fix the engine and he will definitively not be able to provide more than average solutions to the problems he is employed to solve. Like automotive engineering teach us, races can only be won by the right synergy of a good driving style and mechanics. Most importantly, limits of computation cannot be ignored in the same way we precisely know how accelerations, forces and frictions prevent us from racing at an unlimited speed. This course will investigate the prerequisites to understand compilers functioning. Although the act of compilation appears deceptively simple to most of the modern developers, great minds and results are behind the major achievements that made this possible. All starts with the Epimenides paradox (about 600 BC), which emphasizes a problem of self-reference in logic and brings us to the short time window between WWI and WW2 when, in 1936, Alan Turing proved that a general procedure to identify algorithm termination simply does not exist. Another major milestone has been reached by Noam Chomsky in 1956 with his description of a hierarchy of grammars. In this long historical timeframe we can put most of the bricks with which we build modern compilers. The course will be an historical tour through the lives of some of the greatest minds who ever lived on this planet.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Define a formal language
- List different computational models
- Define computational models such as Finite State Automata and Pushdown Automata
- List different types of Formal Grammars
- Define computability and related concepts
- List applications for automata theory and formal grammar

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Describe the basic mathematical machinery behind automata theory and how can be applied to programming languages compilers
- Explain Strengths and weaknesses of specific computational model
- Explain Finite State Automata and Pushdown Automata
- Abstract systems using the given models

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Formally modelling a system
- Reasoning about verification of program properties
- Specifying a system as Finite State Automata, Pushdown Automata or Turing Machine
- Coding in programming languages an emulator of Finite State Automata
- Using proof techniques by diagonalization 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 80-100 | - |
| B. Good | 65-79 | - |
| C. Satisfactory | 50-64 | - |
| D. Poor | 0-49 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 40 |
| Interim performance assessment | 30 |
| Exams | 30 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Handouts supplied by the instructor

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 |
| --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 0 | 0 |
| Homework and group projects | 1 | 0 | 0 |
| Midterm evaluation | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 0 | 0 |
| Reports | 1 | 1 | 0 |
| Discussions | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is a Finite State Automaton? | 1 |
| Question | What is a Pushdown Automaton? | 1 |
| Question | What is a Turing Machine? | 1 |
| Question | What is a nondeterministic automaton? | 1 |
| Question | Given a specific language define a corresponding Finite State Automaton | 1 |
| Question | Given a specific language define a corresponding Pushdown Automaton | 1 |
| Question | State the difference between Finite State Automata and Pushdown Automata | 1 |
| Question | Computing the intersection, union, complement of two automata | 1 |
| Question | What is Pumping Lemma? Example of applications. | 1 |
| Question | Operations on Automata | 1 |
| Question | Check if a given language is recognized by a specific Finite State Automaton | 0 |
| Question | Prove with Pumping Lemma that a language is regular | 0 |
| Question | Check if a given language is recognized by a specific Pushdown Automaton | 0 |
| Question | Check if a given language is recognized by a specific Turing Machine | 0 |
| Question | Define a correct automaton given a specific language | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is Chomsky Hierarchy? | 1 |
| Question | What is a Regular language? | 1 |
| Question | What is a Context-free language? | 1 |
| Question | What is a Context-sensitive language? | 1 |
| Question | What is a regular expression? | 1 |
| Question | Given a specific Finite State Automaton define a grammar for the corresponding language | 0 |
| Question | Given a specific Pushdown Automaton define a grammar for the corresponding language | 0 |
| Question | Given a regular expression design the corresponding Finite state Automaton | 0 |
| Question | Given a Finite state Automaton define the regular expression for the corresponding language | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is Halting Problem? | 1 |
| Question | What is Rice theorem? | 1 |
| Question | What is an undecidable problem | 1 |
| Question | What is a Turing Machine? | 1 |
| Question | What is Goedelization? | 1 |
| Question | Given a specific computational problem showing that it is undecidable (via reduction to a known problem, for example) | 0 |
| Question | Show a proof via diagonalization of Halting Problem | 0 |
| Question | Show a proof via diagonalization of Rice Theorem | 0 |
| Question | Give an example of an undecidable problem | 0 |
| Question | Show that a Turing Machine with multiple tapes is equivalent to a Turing Machine with a single tape | 0 |
#### Final assessment
**Section 1**
1. Check if a given language is recognized by a specific Finite State Automaton
1. Prove with Pumping Lemma that a language is regular.
1. Check if a given language is recognized by a specific Pushdown Automaton
1. Check if a given language is recognized by a specific Turing Machine
1. Define a correct automaton given a specific language
**Section 2**
1. What is Chomsky Hierarchy?
1. What is a Regular language?
1. Given a regular expression design the corresponding Finite state Automaton
1. Given a specific Pushdown Automaton define a grammar for the corresponding language
**Section 3**
1. What is a Turing Machine?
1. What is Halting Problem?
1. What is Rice theorem?
1. Show a proof via diagonalization of Halting Problem
1. Show a proof via diagonalization of Rice Theorem
1. Show that a Turing Machine with multiple tapes is equivalent to a Turing Machine with a single tape

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

<!-- catix:relations -->
## Relations

- Prerequisites: CSE113 Logic and Discrete Mathematics: set theory, inductive definitions and proofs, predicate logic, proof techniques (for example by contradiction, diagonalization...), algebraic structures (preferably).
- Required for: [BSc: Capstone Project](/courses/bsc-capstone-project.md), [Practical Machine Learning and Deep Learning](/courses/bsc-practical-machine-learning-deep-learning.md)
- Taught by: [Andrey Frolov](/people/andreyfrolov.md), [Mansur Khazeev](/people/mansurkhazeev.md), [Manuel Mazzara](/people/manuelmazzara.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Theoretical Computer Science](https://eduwiki.innopolis.university/index.php/BSc%3A_Theoretical_Computer_Science), revision 7194

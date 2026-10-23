---
type: course
title: "Models of Software Systems"
description: "Course SE-07 covering formal models, software specification, and verification, including mathematical foundations, state machines, and tools like SPIN and Z."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Models_Software_Systems"
tags: ["course", "formal-methods", "verification", "specification", "models"]
aliases: ["MSc:Models Software Systems"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Models_Software_Systems"
    id: "7479"
    title: "MSc: Models Software Systems"
    last_modified: "2022-08-29T09:02:00Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:37:28+00:00"
status: draft
stale_after: "2024-08-28T09:02:00+00:00"
prerequisites: [{"as_written": "Set theory"}, {"course": "/courses/bsc-phil1-introductiontologic.md", "as_written": "Propositional Logic", "via": "model"}, {"as_written": "First Order Logic"}, {"as_written": "Formal Systems"}, {"course": "/courses/bsc-discretemathematics-new.md", "as_written": "INTRODUCTION to SET THEORY - DISCRETE MATHEMATICS", "via": "model"}, {"course": "/courses/bsc-discretemath.md", "as_written": "INTRODUCTION to SET THEORY - DISCRETE MATHEMATICS", "via": "model"}, {"course": "/courses/bsc-logic-and-discrete-mathematics-776.md", "as_written": "INTRODUCTION to SET THEORY - DISCRETE MATHEMATICS", "via": "model"}, {"course": "/courses/bsc-logic-and-discrete-mathematics-776.md", "as_written": "INTRODUCTION to PROPOSITIONAL LOGIC - DISCRETE MATHEMATICS", "via": "model"}, {"course": "/courses/bsc-discretemathandlogic.md", "as_written": "INTRODUCTION to PROPOSITIONAL LOGIC - DISCRETE MATHEMATICS", "via": "model"}, {"course": "/courses/bsc-logicincomputerscience.md", "as_written": "(Logic) Predicate Logic", "via": "model"}, {"course": "/courses/bsc-softwareverificationtesting.md", "as_written": "What is Formal Verification?", "via": "model"}]
taught_by: ["/people/manuelmazzara.md", "/people/nursultan-askarbekuly.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Models of Software Systems

## Models of Software Systems
- **Course name**: Models of Software Systems
- **Code discipline**: SE-07
- **Subject area**: 

### Short Description
This course covers the following concepts: Formal Models; Software Specification; Software Verification.

### Prerequisites

#### Prerequisite subjects
- Set theory
- Propositional Logic
- First Order Logic
- Formal Systems
- INTRODUCTION to SET THEORY - DISCRETE MATHEMATICS
- INTRODUCTION to PROPOSITIONAL LOGIC - DISCRETE MATHEMATICS
- (Logic) Predicate Logic
- What is Formal Verification?

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Mathematical Foundations | # Propositional & Predicate Logic <br> # Sets, Relations, Functions |
| Concepts of computation and software | # Proof Techniques, Induction <br> # State Machines |
| Formal Modelling | # UML <br> # Z/B/Event-B <br> # Model Checking <br> # Linear Temporal Logic <br> # Concurrency <br> # Petri Nets <br> # Alloy <br> # Process Algebra <br> # CSP <br> # Autoproof |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
Formal models and formal methods are gaining an increasing importance today - in academia and in industry - in particular due to the emerging of tool support used for modeling and analysis of systems. An important question is asked world-wide when developing academic curricula: what a software engineer should know about formal modeling? On what specific aspect a course should focus and help the perspective engineer to navigate such a complex and fast changing field? The course attempt to give a partial although consistent answer to this question by providing an introduction to the foundations and uses of formal modeling. The course can be seen as organized in three parts: the first part sets out the mathematical foundations on which the rest of the course is based. It presents the mathematical concepts, such as logics, proofs, theories, sets, functions, relations, etc., on which all modern modeling approaches build. The second part presents the concepts that allow to relate mathematics to computation and to software: state machines, invariants, pre- and post-conditions, proving properties about programs. The third part consists of particular notations and method of formal modeling showing how the general concepts of the second part can be turned into effective engineering tools.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Define mathematical notions behind software specification and verification
- List different specification methods
- List different specification notations
- Define concurrency and related concepts
- List Popular verification tools

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Describe the basic mathematical machinery and how can be applied to improve software development and software quality
- Explain Strengths and weaknesses of specific models and logics
- Explain State machines and temporal logics
- Abstract formal models for certain classes of systems

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Formally modelling a system
- Reasoning about system properties
- Specifying a system in Z
- Coding in languages like PROMELA for model checking
- Using SPIN model checker 
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
| Homework and group projects | 1 | 1 | 1 |
| Midterm evaluation | 1 | 1 | 0 |
| Testing (written or computer based) | 1 | 1 | 1 |
| Reports | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 |
| Development of individual parts of software product code | 0 | 0 | 1 |
| Essays | 0 | 0 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is a formal system? What is a rewriting system? | 1 |
| Question | What is the difference between propositional and predicate logic? | 1 |
| Question | What is a predicate? What is a connective? | 1 |
| Question | What is a quantifier? Existential? Universal? | 1 |
| Question | Given a specific formula define the truth table? | 1 |
| Question | Check if a specific formula is a tautology or a contradiction. | 1 |
| Question | State the difference between relation and function | 1 |
| Question | Computing the intersection or union of two sets | 1 |
| Question | What are De Morgan Laws? Example of applications. | 1 |
| Question | Operators of set theory. | 1 |
| Question | Check if given formulas are well-formed. For those that are not briefly explain why. | 0 |
| Question | Prove that a given statement is a theorem in a given formal system. | 0 |
| Question | Augment a given formal system so that given statements become theorems in that formal system. | 0 |
| Question | Construct a truth table for given propositions. | 0 |
| Question | For given satisfiable propositions, provide z3 code that proves their satisfiability. | 0 |
| Question | Translate given predicates into English sentences using the provided translation key. | 0 |
| Question | Translate given sentences into predicate logic, using the translation key provided. | 0 |
| Question | Identify theorems among given propositional statements using z3. | 0 |
| Question | Provide a linear/tree proof of a statement identified as a theorem. | 0 |
| Question | Prove in Isabelle proof assistant a statement identified as a theorem. | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is a state machine and how it is formally defined? | 1 |
| Question | What is s state, initial state, final state? | 1 |
| Question | What is the language accepted by a machine? | 1 |
| Question | Design a state machine for some specific purpose | 1 |
| Question | Verify that a state machine performs a given goal | 1 |
| Question | How does a proof system work? | 1 |
| Question | What is natural deduction and for what it is used? | 1 |
| Question | What is an inference rule? | 1 |
| Question | Prove specific theorems in natural deduction | 1 |
| Question | What are preconditions and postconditons? | 1 |
| Question | Give a 4-tuple description of a state machine. | 0 |
| Question | What are the reachable states of a state machine? | 0 |
| Question | Implement a state machine in the LTSA tool; provide your code. | 0 |
| Question | Does a state machine have any progress or safety violations? Provide the corresponding output from LTSA. . | 0 |
| Question | Given a UML class diagram, annotate its classes with class invariants in OCL. | 0 |
| Question | Given a UML class diagram, annotate its methods with preconditions in OCL. | 0 |
| Question | Given a UML class diagram, annotate its methods with postconditions in OCL. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are the UML diagrams and what is their purpose? | 1 |
| Question | What is OCL and what is its purpose? | 1 |
| Question | What is Z and what is its purpose? | 1 |
| Question | What is Design-by-contract and what is its purpose? | 1 |
| Question | Design UML Use Cases diagrams for some given system | 1 |
| Question | Design UML Class Diagrams for some given system | 1 |
| Question | Define OCL constraints for some parts of some given system | 1 |
| Question | Specify system requirements for a given system in Z | 1 |
| Question | Use temporal logic and model checkers to specify and verify system properties | 1 |
| Question | Use Design-by-contract and Autoproof to specify and verify system properties | 1 |
| Question | Specify a state space in Z. | 0 |
| Question | Specify initial states of a state space in Z. | 0 |
| Question | Specify CRUD operations of a state space in Z. | 0 |
| Question | Define a robust version of a Z specification. | 0 |
| Question | Provide an Alloy specification of a state space. | 0 |
| Question | Enrich an Alloy specification with axioms. | 0 |
| Question | Implement CRUD operations on an Alloy specification of a state space. | 0 |
| Question | Specify an assertion that you want to hold on an Alloy specification. | 0 |
| Question | Check an assertion in an Alloy specification using Alloy analyzer; correct the specification if the assertion does not hold. | 0 |
#### Final assessment
**Section 1**
1. Given a set of different formulas define truth tables
1. Given a set of different formulas define those that are tautology and/or contradiction
1. Compute operations over some specific instances of sets
1. Determining satisfiability of a formula
1. Model natural language as propositional or predicate logic formulas
**Section 2**
1. Prove theorems in natural deduction
1. Design a state machine for some specific purpose
1. Verify that a state machine performs a given goal
1. Determine the language recognized by a state machine
**Section 3**
1. Design UML Use Cases diagrams for some given system
1. Design UML Class Diagrams for some given system
1. Define OCL constraints for some parts of some given system
1. Specify system requirements for a given system in Z
1. Use temporal logic and model checkers to specify and verify system properties
1. Use Design-by-contract and Autoproof to specify and verify system properties

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

<!-- catix:relations -->
## Relations

- Prerequisites: Set theory; [PHIL-Introduction to Logic](/courses/bsc-phil1-introductiontologic.md) (Propositional Logic, matched by the model); First Order Logic; Formal Systems; [Discrete Mathematics](/courses/bsc-discretemathematics-new.md) (INTRODUCTION to SET THEORY - DISCRETE MATHEMATICS, matched by the model); [Discrete Mathematics](/courses/bsc-discretemath.md) (INTRODUCTION to SET THEORY - DISCRETE MATHEMATICS, matched by the model); [Logic and Discrete Mathematics (CSE113)](/courses/bsc-logic-and-discrete-mathematics-776.md) (INTRODUCTION to SET THEORY - DISCRETE MATHEMATICS, matched by the model); [Logic and Discrete Mathematics (CSE113)](/courses/bsc-logic-and-discrete-mathematics-776.md) (INTRODUCTION to PROPOSITIONAL LOGIC - DISCRETE MATHEMATICS, matched by the model); [Discrete Math and Logic](/courses/bsc-discretemathandlogic.md) (INTRODUCTION to PROPOSITIONAL LOGIC - DISCRETE MATHEMATICS, matched by the model); [Logic in Computer Science](/courses/bsc-logicincomputerscience.md) ((Logic) Predicate Logic, matched by the model); [Software Verification and Testing](/courses/bsc-softwareverificationtesting.md) (What is Formal Verification?, matched by the model)
- Taught by: [Manuel Mazzara](/people/manuelmazzara.md), [Nursultan Askarbekuly](/people/nursultan-askarbekuly.md)
<!-- /catix:relations -->

# Citations

1. [MSc: Models Software Systems](https://eduwiki.innopolis.university/index.php/MSc%3A_Models_Software_Systems), revision 7479

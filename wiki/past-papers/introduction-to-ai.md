---
type: page
title: "Past exam papers: Introduction to AI"
description: "Past exams and tests of Introduction to AI at Innopolis University (5 papers, 2021–2024), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "introduction-to-ai"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "Introduction to AI"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: Introduction to AI

Exams and tests of **Introduction to AI** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2024: Final

Files: [Introduction to AI Final 2024.pdf](https://glebpopov.notion.site/152e746cceef80578082e9801647b188)


Name Surname: _______________________________

Pieced together by B23 for generations to come.

Task 1 (6 points)
Write the Isaac Asimov’s laws of robotics.

Group: __________

Name Surname: _______________________________

Group: __________

Task 2 (10 points)
Apply Hill Climber to the given 8-puzzle problem by sliding numbers vertically or
horizontally to an empty cell. Define heuristics. Provide step-by-step solution.

3

1

2

4

5

8

6
Heuristics:

Solution:

7

→

1

2

3

4

5

6

7

8

Name Surname: _______________________________

Group: __________

Task 3 (12 points)
The provided PDDL domain definition names school_domain outlines a simple
model for managing teachers, students, lessons, and rooms in a school-like
setting. Fill in the gaps in the following code.







(room_empty ?r): indicates whether a room ?r is empty
(student_at ?s ?r): indicates whether a student ?s in a room ?r
(teacher_at ?t ?r): indicates whether a teacher ?t in a room ?r
(lesson_scheduled ?l ?r): indicates whether a lesson ?l in scheduled in a room ?r
(student_enrolled ?s ?l): indicates whether a student ?s in enrolled in a lesson ?l
(lesson_started ?l): indicates whether a lesson ?l is started

domain.pddl (8 points)

problem.pddl (4 points)

Define the following actions:
 schedule_lesson: schedules a lesson in a room
 enroll student: enrolls a student in a lesson
 start_lesson: starts a lesson

Define the goal for the system: one of the
students is enrolled in math, another
student is enrolled in intro_ai, and each
course is scheduled in a different room
(101 and 102).

(define (domain school_domain)
(:requirements :strips)
(:predicates
(room_empty ?r)
(student_at ?s ?r)
(teacher_at ?t ?r)
(lesson_sheduled ?l ?r)
(student_enrolled ?s ?l)
(lesson_started ?l)
)

(define (problem school_problem)
(:domain school_domain)
(:objects
student1 student2 – student
room101 room 102 – room
math intro_ai – lesson
)
(:init
(room_empty room101)
(room_empty room102)
(student_at student1 room101)
(student_at student2 room102)
)

(:action schedule_lesson
:parameters (?l ?r)
:precondition (and (______________________)
(______________________))
:effect (and (______________________)
(______________________))

(:goal
(and
(______________________)
(______________________)
(______________________)
(______________________)
)
)

)
(:action enroll_student
:parameters (?s ?l ?r)
:precondition (and (______________________)
(______________________)
(lesson_scheduled ?l ?r))
:effect (student_enrolled ?s ?l)
)
; ignore the necessity of the students
(:action start_lesson
:parameters (?t ?l ?r)
:precondition (and (teacher_at ?t ?r)
(______________________))
:effect (______________________)
)
)

)

Name Surname: _______________________________

Group: __________

Task 4 (12 points)
Provide a pseudo-code for a general Evolutionary Algorithm (EA). Describe which
special operations can be applied in GP, provide examples of these operations.
a. EA pseudo-code (6 points).

b. Provide a description of the following for Genetic Programming (4 points).
1. Representation:

2. Selection:

3. Crossover:

4. Mutation:

c. Special operations in Genetic Programming with examples (2 points).

Name Surname: _______________________________

Group: __________

Task 5 (10 points)
Consider the following fully connected neural network:

All the Neurons (𝑁1 , 𝑁2 , 𝑁3 , 𝑁4 , 𝑁5 ) use Leaky ReLU (𝝈) as an activation function.
Consider a hyperparameter equal to 0.1.
Write the answers to the following questions:
1. Output after activation of 𝑁1 | 𝜎(𝑁1 ) = ______________
2. Output after activation of 𝑁2 | 𝜎(𝑁2 ) = ______________
3. Output after activation of 𝑁3 | 𝜎(𝑁3 ) = ______________
4. Output after activation of 𝑁4 | 𝜎(𝑁4 ) = ______________
5. Output after activation of 𝑁5 | 𝜎(𝑁5 ) = ______________

## 2022: Final

Files: [Introduction to AI Final 2022.pdf](https://glebpopov.notion.site/ac5d85cf655d40aea85afda3e59f28f2)


Name Surname:

Group №:
Introduction to AI
Final Exam Spring 2022

Rules:
Print your name and group number carefully at the top of all pages. This is a closed book exam
and requires no external materials Any cheating/misconduct will result in a mark of 0 and report
to the Educational Dept. Make all answers in pen – no remarks will be given to those using pencil.
Exam will last 110 min from call of time. There are 6 questions and 50 marks available – this test
making up 25% of your final grade:
1. Provide the Isaac Asimov’s laws of robotics. [5pt]

2. The piece of Romanov’s family tree is given, most of the members are intentionally omitted,
please ignore them. You should use PROLOG to answer the questions given below.

Alexander II
Maria Fedorovna

Olga

Maria Alexandrovna

Alexander III …

Vladimir

Nicholas II

George

…

1

Name Surname:

Group №:

a. Write the knowledge base for the tree using female(X), male(X), parent(X,Y). [5pt]
Write facts:

Specify rules (ignore creation of duplicates in answers):
• father(X,Y) :=
• mother(X,Y) :=
• grandfather(X,Y) :• grandmother(X,Y) :• brother(X,Y) :• sister(X,Y) :• aunt(X,Y) :• uncle(X,Y) :b. Resolve the following queries using given facts and rules [5pt]:
• Was Alexander II the parent of Alexander III?
Query:
Answer:
•

Who were the parents of Nicholas II?
Query:
Answer:

•

Show all male nephews, make the rule ultimate for even a bigger tree.
Query:
Answer:

•

Show all pairs of males with daughters.
Query:
Answer:

2

Name Surname:

Group №:

3. What is the difference between GBEST and LBEST PSO versions? Draw examples of topologies
for both versions [6pt]

4. What formula is used for the selection of a leaf in Monte Carlo Tree Search and how? Explain
the variable meanings and which part of the formula is responsible for exploitation and which
for exploration. [7pt]

3

Name Surname:

Group №:

5. Provide pseudo-code for a general evolutionary algorithm’s main loop. Then give a description
of evolutionary strategy (representation, selection, crossover and mutation).
a. EA pseudo-code: [5pt]

b. ES description:
i. Representation [1pt]:

ii. Selection [1pt]:

iii. Crossover [1pt]:

iv. Mutation and its versions [2pt]:

4

Name Surname:

Group №:

6. Show 3 perceptrons with activation functions and weights:
a. Show a perceptron which implements AND. [4pt]

b. Show a perceptron which implements OR. [4pt]

c. Show a perceptron which implements NOT. [4pt]

5

Name Surname:

Group №:

6

## 2022: Midterm

Files: [Introduction to AI Midterm 2022.pdf](https://glebpopov.notion.site/120e746cceef80e7b10dedec54cd7720)


Name Surname:

Group №:

Introduction to AI
Midterm Spring 2022 (2nd of March)
Rules:
Print your name and group number carefully at the top of all pages. This is a closed book exam
and requires no external materials. Any cheating/misconduct will result in a mark of 0 and report
to the Educational Dept. Make all answers in pen – no marks will be given to those using pencil.
Exam will last 90 min from call of time. There are 6 questions and 50 marks available – this test
making up 25% of your final grade:
1. What is Socrates definition of Knowledge and how does it relate to the philosophy of AI? [5pt]

2. Provide and justify a PEAS for a delivery robot. Describe and justify the properties of the
environment. [10pt]

1

Name Surname:

Group №:

3. Describe the Chinese Room Problem and what it says about the philosophy of AI. [5pt]

4. What is Exploitation and Exploration in a Search Algorithm? If I begin to use my car keys to
cause my car alarm to sound – is this Explorative or Exploitative? [5pt]

2

Name Surname:

Group №:

5. Apply minimax with alpha beta pruning for a given tree and given sequence of numbers
appearing in leaves from left to right: -1, 3, 5, 1, -6, -4, 0, 9. [10pt]

max
min
max

3

Name Surname:

Group №:

6. Tank should cross the field and achieve final point. Different obstacles cost different points:
• empty cell – 1 point
• WALL can be destroyed - 2 points
• LAKE can be crossed – 3 points
• PIT can be crossed – 4 points
• HILL can be climbed – 5 points

Tank can move in any direction including diagonal cells. Using the A* algorithm find the
shortest path (or paths) and draw other paths from initial point till final point [15pt]
TANK

LAKE

HILL

HILL

LAKE

HILL

HILL

WALL WALL LAKE

LAKE

PIT

PIT

WALL GOAL

4

## 2021: Final

Files: [Introduction to AI Final 2020.pdf](https://glebpopov.notion.site/a5ccbea1ce9a4d3aa876b91b8314af4f)


This is an essay style question, using the concepts in class. Do not rely on “personal opinions”
in this writing, but relate it clearly to concepts of the course.
You are expected to write your answer using the proper English spelling, grammar, and form and
convince examiners you know the course materials via your persuasive writing. You may use any
resources required but please cite any sources used. It is expected that an intelligent answer to
this question will take at least two double spaced typed pages in 12pt Times New Roman font
with normal margins (i.e. the settings already in this word document) without diagrams or
figures. Though you may use more space to further your arguments. Please name your
submission as Firstname_Lastname.docx and place your name and student ID on all pages of the
document.
Do this work on your own, evidence of copying or plagiarism, etc. will result in a grade of zero
and a report to the DOE. Please, challenge yourselves and display your honest knowledge and
understanding in a new issue.
A number of AI systems are engaged in the selection of those who receive credit, jobs, access to
resources, etc. Necessarily, this has led to the questions of discrimination in the choice of such
systems.
Your task in this essay is to argue a case as to if or if not, an AI system itself can be
“discriminatory”. Clearly state your choice of argument, either for or against, and make a
full-throated argument for your chosen side. You may compare and contrast to the opposing
side, but you must have a clear thesis statement either for or against and work to this end. Do
not make a middle ground or fence sitting essay. Use real world examples and course materials
to support your argument.

## 2021: Midterm

Files: [Introduction to AI Midterm 2020.pdf](https://glebpopov.notion.site/9d4a1c24fc7d4b44819b862250fcc941)


This is an essay style question, using the concepts in class. Do not rely on “personal opinions”
in this writing, but relate it clearly to concepts of the course.
You are expected to write your answer using the proper English spelling, grammar, and form and
convince examiners you know the course materials via your persuasive writing. You may use any
resources required but please cite any sources used. It is expected that an intelligent answer to
this question will take at least two double spaced typed pages in 12pt Times New Roman font
with normal margins (i.e. the settings already in this word document) without diagrams or
figures. Though you may use more space to further your arguments. Please name your
submission as Firstname_Lastname.docx and place your name and student ID on all pages of the
document.
Do this work on your own, evidence of copying or plagiarism, etc. will result in a grade of zero
and a report to the DOE. Please, challenge yourselves and display your honest knowledge and
understanding in a new issue.
You have been asked to create a chess playing system for tournament play. The system is built
into a normal chess board and uses a camera to view the positions on the board, it then makes its
moves by declaration on a screen (an official of the tournament will move the pieces for it), it
will also be able to operate the clock, and must be able to hand in its scorecard.
Provide a PEAS model for the system. Define the task environment. Provide a clear justification
for these choices. Compare and contrast two methods for the system to find the next move.
Comment on these two methods in regards to how they use Exploration and Exploitation.
Finally, can this system ever be said to know how to play chess? Why or why not?

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)

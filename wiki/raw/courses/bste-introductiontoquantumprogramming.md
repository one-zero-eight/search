---
type: course
title: "Introduction to Quantum Programming"
description: "Course covering quantum computing basics, Qiskit programming, quantum algorithms, and applications in optimization and machine learning."
resource: "https://eduwiki.innopolis.university/index.php/BSTE%3AIntroductionToQuantumProgramming"
tags: ["quantum", "qiskit", "course", "algorithms", "machine-learning"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSTE%3AIntroductionToQuantumProgramming"
    id: "969"
    title: "BSTE:IntroductionToQuantumProgramming"
    last_modified: "2021-10-12T08:03:23Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:12:53+00:00"
status: draft
stale_after: "2023-10-12T08:03:23+00:00"
---

# Introduction to Quantum Programming

## Introduction to Quantum Programming

- **Course name:** Introduction to Quantum Programming
- **Course number:** N/A

### Course Characteristics

### What subject area does your course (discipline) belong to?

Quantum computing

#### Key concepts of the class

- Quantum computer
- Quantum circuit
- Quantum optimization

#### What is the purpose of this course?

The goal of the course is to equip students with the skills to develop quantum algorithms using modern development tools for simulators and real computing systems. These skills include, but are not limited to, the qiskit programming language and its libraries, and universal quantum notation.

After mastering the course the student should be aware of ways to develop quantum algorithms, should be able to develop simple quantum circuits from scratch and integrate them into classical software, should be able to compose sequences of quantum circuits that solve computational and machine learning problems.

#### Course objectives based on Bloom’s taxonomy

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to remember and recognize

- basics of quantum computing
- definition of quantum state and quantum gate
- basic quantum gates
- basic quantum subprograms

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to describe and explain

- terms of quantum computing
- solving applied problems in quantum computer

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to

- write an algormithm in qiskit progamming language
- run an algorithm in simulator
- run an algorithm in real quantum computer

#### Course evaluation

**Course grade breakdown**

|  | **Proposed points** |
| --- | --- |
| Labs/seminar classes | 0 |
| Interim performance assessment | 20 |
| Assessments | 60 |
| Exams | 20 |

If necessary, please indicate freely your course’s features in terms of students’ performance assessment:

Students pass 3 homeworks 20 points each. 20 points are given for in-class performance (solving the labs and whiteboard examples). 20 points go to the exam.

#### Grades range

**Course grading range**

|  | **Proposed range** |
| --- | --- |
| A. Excellent | 80-100 |
| B. Good | 65-79 |
| C. Satisfactory | 50-64 |
| D. Poor | 0-49 |

#### Resources and reference material

Main textbook:

- [Programming Quantum Computers: Essential Algorithms and Code Samples](https://www.amazon.com/Programming-Quantum-Computers-Essential-Algorithms/dp/1492039683)
- [Qiskit textbook](https://qiskit.org/textbook/preface.html)
- [QBronze workshop materials](https://gitlab.com/qworld/bronze-qiskit)

Other reference material:

- [QSilver workshop](https://gitlab.com/qworld/silver)

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Single qubit | 12 |
| 2 | 2 qubit operations | 8 |
| 3 | quantum data representation | 10 |
| 4 | quantum building blocks | 4 |
| 5 | quantum optimization and machine learning | 6 |

#### Section 1

##### Section title:

Single Qubit

##### Topics covered in this section:

- Qubit
- Superposition
- Quantum states, vector representation, and bra-ket notation
- Single qubit gates NOT, READ/WRITE, HADAMARD, ROT, PHASE

##### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 0 |
| Reports | 0 |
| Essays | 1 |
| Oral polls | 0 |
| Discussions | 0 |

##### Typical questions for ongoing performance evaluation within this section

1. Express a superposed state with given probabilities of realization in bra-ket notation
1. Compute the state given a sequence of gates
1. Prepare a desired quantum state given single-qubit operations
1. What is the difference between Unitary and Stochastic matrices?

##### Typical questions for seminar classes (labs) within this section

1. Prepare a desired state given single-qubit operations 
1. Apply Hadamard gate to |+>
1. What is Matrix exponentiation?

##### Test questions for final assessment in this section

1. Find eigenstates of Hadamard operator
1. Prepare a desired quantum state

#### Section 2

##### Section title:

2 qubit operations

##### Topics covered in this section:

- 2-qubit operations
- CNOT
- CU: CPHASE, CZ, SWAP
- CC-U: Toffoli
- Implementation of arbitrary C-U and CC-U gates


##### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 0 |
| Reports | 0 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

##### Typical questions for ongoing performance evaluation within this section

1. Compute tensor product of 2 matrices
1. Implement C-RotX(phi) gate
1. Compute CNOT^(-1)

##### Typical questions for seminar classes (labs) within this section

1. Apply CNOT to |+0> in matrix form
1. Implement CC-H gate using 2-qubit gates only
1. Compute CCNOT^(-1)

##### Test questions for final assessment in this section

1. Implement CZ gate
1. Implement sqrt(CZ) gate
1. Implement CCCNOT

#### Section 3

##### Section title:

Quantum data representation

##### Topics covered in this section:

- Quantum arithmetics
- Quantum RAM
- Quantum vector encoding
- Quantum matrix encoding

##### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 0 |
| Reports | 0 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

#### Typical questions for ongoing performance evaluation within this section

1. Implement +3 for 2-s complement notation
1. Encode a random vector of 8 components
1. Encode a random unitary matrix

##### Typical questions for seminar classes (labs) within this section

1. Implement x2 for 2-s complement notation
1. Encode a random vector of 4 components
1. Encode a random Hermitian matrix with density matrix

##### Test questions for final assessment in this section

1. Implement x3 for 2-s complement notation
1. Encode a random vector of 16 components
1. Encode a random Hermitian matrix

#### Section 4

##### Section title:

Quantum programming building blocks

##### Topics covered in this section:

- Quantum teleportation
- Amplitude amplification
- QFT
- Quantum Phase estimation
- Grover's search algorithm
- Shor's factorization algoritm

##### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 0 |
| Reports | 0 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

##### Typical questions for ongoing performance evaluation within this section

1. Teleport a qubit and prove your teleportation result is correct
1. Apply QFT to a given vector and report major frequency in discrete sinal
1. For a given matrix, implement a matrix as a circuit and find an eigenvalue for the first eigenvector

##### Typical questions for seminar classes (labs) within this section

1. Implement Amplitude Amplification and show in works
1. Factorize 21 using Shor's algorithm
1. Apply QFT for a `sin(kt)` function

##### Test questions for final assessment in this section

1. Factorize 15 using Shor's algorithm
1. Apply Grover search for an arbitrary oracle function
1. Apply QFT for a `cos(kt)` function

#### Section 5

##### Section title:

Quantum optimization and machine learning

##### Topics covered in this section:

- Quantum PCA
- Quantum SVM
- Quadractic Unconstrained Binary Optimization (QUBO) and derivations
- QAOA
- Quantum CNN

##### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 0 |
| Reports | 0 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

##### Typical questions for ongoing performance evaluation within this section

1. Using qiskit find the first principal conponent of the matrix
1. Classify the data using quantum SVM
1. Implement Quantum CNN

##### Typical questions for seminar classes (labs) within this section

1. Build a QSVM classifier
1. State a problem in a QUBO form and solve it

##### Test questions for final assessment in this section

1. Using qiskit find the second principal conponent of the matrix
1. Find graph max cut using QAOA

# Citations

1. [BSTE:IntroductionToQuantumProgramming](https://eduwiki.innopolis.university/index.php/BSTE%3AIntroductionToQuantumProgramming), revision 969

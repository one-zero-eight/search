---
type: course
title: "Optimization"
description: "Course covering optimization of cost functions, linear and nonlinear algorithms, simplex method, and convergence analysis for engineering applications."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Optimization"
tags: ["optimization", "linear-programming", "nonlinear-programming", "algorithms", "engineering"]
aliases: ["MSc:Optimization"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Optimization"
    id: "7755"
    title: "MSc: Optimization"
    last_modified: "2022-11-10T11:09:42Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:39:05+00:00"
status: draft
stale_after: "2024-11-09T11:09:42+00:00"
---

# Optimization

## Optimization
- **Course name**: Optimization
- **Code discipline**: R-01
- **Subject area**: 

### Short Description
This course covers the following concepts: Optimization of a cost function; Algorithms to find solution of linear and nonlinear optimization problems.

### Prerequisites

#### Prerequisite subjects


#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Linear programming | # simplex method to solve real linear programs <br> # cutting-plane and branch-and-bound methods to solve integer linear programs. |
| Nonlinear programming | # methods for unconstrained optimization <br> # linear and nonlinear least-squares problems <br> # methods for constrained optimization |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The main purpose of this course to make the student aware of  basic notions of mathematical programming and of its importance in the area of engineering.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- explain the goal of an optimization problem
- remind the importance of converge analysis for optimization algorithms
- draft solution codes in Python/Matlab.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- formulate a simple optimization problem
- select the appropriate solution algorithm
- find the solution.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- the simplex method
- algorithms to solve nonlinear optimization problems. 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 86-100 | - |
| B. Good | 71-85 | - |
| C. Satisfactory | 56-70 | - |
| D. Poor | 0-55 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes (weekly evaluations) | 0 |
| Interim performance assessment (class participation) | 100/0 |
| Exams | 0/100 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Textbook: C.H. Papadimitriou, K. Steiglitz, Combinatorial Optimization, Dover, New York, 1982.
- Textbook: D. Bertsekas, Nonlinear Programming, Athena Scientific, 1999.

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 |
| --- | --- | --- |
| Midterm evaluation | 1 | 1 |
| Testing (written or computer based) | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How a convex set and a convex function are defined? | 1 |
| Question | What is the difference between polyhedron and polytope? | 1 |
| Question | Why does always a linear program include constraints? | 1 |
| Question | Consider the problem: <br> <math>{\displaystyle {\text{minimize }}c_{1}x_{1}+c_{2}x_{2}+c_{3}x_{3}+c_{4}x_{4}}</math> <br> <math>{\displaystyle {\text{subject to }}x_{1}+x_{2}+x_{3}+x_{4}=2}</math> <br> <math>{\displaystyle 2x_{1}+3x_{3}+4x_{4}=2}</math> <br> <math>{\displaystyle x_{1},x_{2},x_{3},x_{4}\geqslant 0}</math> <br> Solve it using simplex method. | 0 |
| Question | Consider the problem: <br> <math>{\displaystyle {\text{minimize }}x_{1}+x_{2}}</math> <br> <math>{\displaystyle {\text{subject to }}-5x_{1}+4x_{2}\leq 0}</math> <br> <math>{\displaystyle 6x_{1}+2x_{2}\ \leq 17}</math> <br> <math>{\displaystyle x_{1},\ x_{2}\geq 0}</math> <br> Solve it using cutting-plane and branch-and-bound methods. | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Which are the necessary and sufficient conditions of optimality of a generic minimization/maximization problem? | 1 |
| Question | What is the goal of a descent algorithm? | 1 |
| Question | What does it mean to fit some experimental data points | 1 |
| Question | Consider the problem: <br> <math>{\displaystyle {\text{minimize }}{\frac {1}{2}}\left(x_{1}^{1}+x_{2}^{2}\right)}</math> <br> Solve it using the suitable method. | 0 |
| Question | Consider the problem: <br> <math>{\displaystyle {\text{minimize }}-\left(x_{1}-2\right)^{2}}</math> <br> <math>{\displaystyle {\text{subject to }}\ x_{1}+x_{2}^{2}=1}</math> <br> <math>{\displaystyle -1\leq x_{2}\leq 1}</math> <br> Solve it using the suitable method. | 0 |
#### Final assessment
**Section 1**
1. Why does the simplex method require to be initialized with a correct basic feasible solution?
1. How one can test absence of solutions to a linear program?
1. How one can test unbounded solutions to a linear program?
1. How can the computational complexity of an optimization algorithm can be defined?
**Section 2**
1. How is it possible to compute the Lagrange multiplier of a constrained optimization problem?
1. Which are the convergence conditions of the steepest descent method?
1. Which are the convergence conditions of the Newton’s method?
1. How can one “penalize” a constraint?

#### The retake exam
**Section 1**
1. Consider the problem:
<math>{\displaystyle {\text{minimize }}x_{1}+x_{2}}</math> 
<math>{\displaystyle {\text{subject to }}x_{1}+{2x}_{2}+2x_{3}\leq 20}</math> 
<math>{\displaystyle 2x_{1}+x_{2}+2x_{3}\leq 20}</math> 
<math>{\displaystyle 2x_{1}+2x_{2}+x_{3}\leq 20}</math> 
<math>{\displaystyle x_{1},\ x_{2},\ x_{3}\geq 0}</math> 
Solve it using simplex method.
1. Consider the problem:
<math>{\displaystyle {\text{maximize }}15x_{1}+{12x}_{2}+4x_{3}+2x_{4}}</math> 
<math>{\displaystyle {\text{subject to }}8x_{1}+5x_{2}+3x_{3}+2x_{4}\leq 10}</math> 
<math>{\displaystyle x_{i}\in \{0,1\}}</math> 
Solve it using cutting-plane and branch-and-bound methods.

**Section 2**
1. Consider the problem:
<math>{\displaystyle {\text{minimize }}100\left(x_{2}-x_{1}^{2}\right)^{2}+\left(1-x_{1}\right)^{2}}</math> 
<math>{\displaystyle {\text{subject to }}x_{1},\ x_{2}\geq 0}</math> 
Solve it using the suitable method.


# Citations

1. [MSc: Optimization](https://eduwiki.innopolis.university/index.php/MSc%3A_Optimization), revision 7755

---
type: course
title: "Computational Intelligence"
description: "Course covering convex and global optimization, machine learning, and function approximation, including prerequisites, learning outcomes, and grading structure."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Computational_Intelligence"
tags: ["computational-intelligence", "optimization", "machine-learning", "convex-optimization", "course"]
aliases: ["MSc:Computational Intelligence"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Computational_Intelligence"
    id: "7469"
    title: "MSc: Computational Intelligence"
    last_modified: "2022-08-29T08:47:50Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:28:51+00:00"
status: draft
stale_after: "2024-08-28T08:47:50+00:00"
prerequisites: [{"course": "/courses/msc-analyticalgeometryandlinearalgebrai.md", "as_written": "CSE202 — Analytical Geometry and Linear Algebra I"}, {"course": "/courses/bsc-analytic-geometry-and-linear-algebra-ii.md", "as_written": "CSE204 — Analytic Geometry And Linear Algebra II: SVD, least squares, pseudoinverse, semidefinite matrices, solving systems of linear eq., dot product, norms. Basic Geometry (ellipsoids, planes, normal, tangent)."}, {"as_written": "Basic multivariable Calculus (extremum and minimum of a function, derivatives, Jacobians)"}, {"course": "/courses/bsc-ftd-03-mfai-2024-python-programming-2s.md", "as_written": "Programming (Python/Matlab)", "via": "model"}, {"course": "/courses/bsc-ftd-03-mfai-2024-python-programming-1s.md", "as_written": "Programming (Python/Matlab)", "via": "model"}]
taught_by: ["/people/sergeysavin.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Computational Intelligence

## Computational intelligence
- **Course name**: Computational intelligence
- **Code discipline**: R-02
- **Subject area**: Computer Science and Engineering

### Short Description
This course covers the following concepts: Convex Optimization; Global Optimization; Machine Learning and function approximation.

### Prerequisites

#### Prerequisite subjects
- CSE202 — Analytical Geometry and Linear Algebra I
- CSE204 — Analytic Geometry And Linear Algebra II: SVD, least squares, pseudoinverse, semidefinite matrices, solving systems of linear eq., dot product, norms. Basic Geometry (ellipsoids, planes, normal, tangent).
- Basic multivariable Calculus (extremum and minimum of a function, derivatives, Jacobians)
- Programming (Python/Matlab)

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Introduction to optimization methods | # Optimization problem types. <br> # Constraint types. <br> # Cost function (Reward function) types. <br> # Practical examples of optimization problems. <br> # Basic optimization algorithms and their limitations. <br> # Lagrange multipliers. <br> # Gradient descent. |
| Convex Optimization. | # Convex sets. <br> # Convex functions. <br> # Convex optimization problems. <br> # Properties of the convex optimizations. <br> # Linear Programming <br> # Quadratic Programming. <br> # Second Order Cone Programming. <br> # Semidefinite Programming. <br> # Vertical Stability of a bipedal robot as an optimization. <br> # Quadrotor path planning as an optimization. <br> # Controller design as an optimization. <br> # CVX. |
| Global Optimization | # Properties of non-convex problems. <br> # Problems with multiple solutions. <br> # Problems with weak local minima. <br> # Problems with computationally expensive gradients. <br> # Path planning on non-convex maps. <br> # Controller design as a non-convex problem. <br> # Relaxations. <br> # Mixed integer programming. <br> # PSO. <br> # RRT. <br> # Genetic Algorithm. <br> # Machine Learning. |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
Computational Intelligence serves as a combined multidisciplinary subject, encompassing a wide range of topics. These include numeric optimization, especially convex optimization, which is the necessary and required topic for most of the modern engineering and scientific work. The course also covers global non-convex optimization methods, which are important instruments in a number of areas: product design and manufacturing, control, and others. Basic information from a number of other areas, such as machine learning, are added to complete the picture of modern intelligent computational tools that serve the same set of goals.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Convexity, Convex Sets, Convex optimization
- Quadratic programming, Second Order Cone Programming, Semidefinite Programming
- Optimization in Controller design, Optimization in path planning, Optimization in Mechanical Engineering
- Nonlinear non-convex optimization, RRT algorithm, Genetic Algorithm, Particle Swarm Optimization, Function approximation.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Structure of optimization problems
- Convexity criteria
- Properties of convex optimization
- Types of problems that cab be transformed into Linear Programs
- Types of problems that cab be transformed into Quadratic Programs
- Types of problems that cab be transformed into Second Order Cone Programs
- Types of problems that cab be transformed into Semidefinite Programs
- Types of non-convex problems that can be approximated by a convex relaxation
- Mixed-integer Optimization
- Path planning as an optimization
- Controller design as an optimization
- Optimal parameter choice
- RRT implementation
- PSO implementation

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Design Control using Convex Optimization.
- Implement iterative non-linear controllers with inequality constraints.
- Find optimal parameter choice for processes
- proof convexity of a problem
- program optimization in CVX
- make RRT-based algorithms, understand their limitations
- make PSO-based algorithms, understand their limitations
- make GA-based algorithms, understand their limitations 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 85-100 | - |
| B. Good | 70-84 | - |
| C. Satisfactory | 50-69 | - |
| D. Poor | 0-49 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 30 |
| Interim performance assessment | 20 |
| Exams | 50 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Engelbrecht, A.P., 2007. Computational intelligence: an introduction. John Wiley & Sons.
- Pedrycz, W., 1997. Computational intelligence: an introduction. CRC press.
- Konar, A., 2006. Computational intelligence: principles, techniques and applications. Springer Science & Business Media.

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 |
| --- | --- | --- | --- |
| Homework and group projects | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 0 | 0 |
| Reports | 1 | 1 | 1 |
| Midterm evaluation | 0 | 1 | 0 |
| Discussions | 0 | 1 | 0 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Describe an engineering problem as an optimization problem. | 1 |
| Question | What is the domain of an optimization problem? | 1 |
| Question | What is the difference between Convex and Non-convex optimization? | 1 |
| Question | Formulate a linear system with multi-dimensional solution space and inequality constraints. | 0 |
| Question | Solve a linear system with inequality constraints via gradient descent. | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Provide examples of convex problems. | 1 |
| Question | What is a convex domain? | 1 |
| Question | Examples of problems with a convex cost but non-convex domain? | 1 |
| Question | What is the difference between quadratic and conic programming? | 1 |
| Question | What is the hierarchy of convex optimization problems? | 1 |
| Question | What solvers can solve quadratic programs? | 1 |
| Question | What solvers can solve SOCP? | 1 |
| Question | What solvers can solve LP? | 1 |
| Question | What solvers can solve SDP? | 1 |
| Question | What kinds of inequality constraints make the problem non-convex? | 0 |
| Question | What kinds of inequality constraints make the problem non-feasible? | 0 |
| Question | Show an example of a problem where the cost is a 2-norm. Show that it is a SOCP. | 0 |
| Question | Show an example of a problem where the cost is a 2-norm. Prove that it can be equivalently solved as a QP. | 0 |
| Question | Solve trajectory planning for a quadrotor as a SOCP. | 0 |
| Question | Solve vertical stability check for a biped as a QP. | 0 |
| Question | implement ZMP trajectory planning as a QP. | 0 |
| Question | implement LTI controller design as a SDP. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Provide examples of non-convex problems? | 1 |
| Question | Why non-convex problems can have multiple solutions? | 1 |
| Question | What are local minima? | 1 |
| Question | What is global optimization? | 1 |
| Question | Provide an example of a non-convex path planning problems? | 1 |
| Question | What are the limitations of PSO? | 1 |
| Question | Implement PSO for a parameter optimization problem. | 0 |
| Question | Make a comparative study of PSO, GA and Random Search. | 0 |
| Question | What is the difference between random search, Sobol sequences-based methods and PSO? Show it in the numerical examples. | 0 |
| Question | Implement RRT | 0 |
| Question | Implement GA | 0 |
#### Final assessment
**Section 1**

**Section 2**

**Section 3**
1. Solve minimum distance to a plane problem, when the domain is non-convex.
1. Find optimal controller parameters for a given trajectory of a non-linear system.
1. Which non-linear algorithms can solve problems with non-convex domains?

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

<!-- catix:relations -->
## Relations

- Prerequisites: [Analytical Geometry and Linear Algebra I](/courses/msc-analyticalgeometryandlinearalgebrai.md) (CSE202 — Analytical Geometry and Linear Algebra I); [BSc: Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md) (CSE204 — Analytic Geometry And Linear Algebra II: SVD, least squares, pseudoinverse, semidefinite matrices, solving systems of linear eq., dot product, norms. Basic Geometry (ellipsoids, planes, normal, tangent).); Basic multivariable Calculus (extremum and minimum of a function, derivatives, Jacobians); [BSc: FTD.03 MFAI 2024 Python programming 2s](/courses/bsc-ftd-03-mfai-2024-python-programming-2s.md) (Programming (Python/Matlab), matched by the model); [BSc: FTD.03 MFAI 2024 Python programming 1s](/courses/bsc-ftd-03-mfai-2024-python-programming-1s.md) (Programming (Python/Matlab), matched by the model)
- Taught by: [Sergey Savin](/people/sergeysavin.md)
<!-- /catix:relations -->

# Citations

1. [MSc: Computational Intelligence](https://eduwiki.innopolis.university/index.php/MSc%3A_Computational_Intelligence), revision 7469

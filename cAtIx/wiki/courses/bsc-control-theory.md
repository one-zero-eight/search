---
type: course
title: "BSc: Control Theory"
description: "A course covering linear control theory, stability, controller design, sensing, observers, and adaptive control for robotics and engineering."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Control_Theory"
tags: ["control-theory", "robotics", "linear-systems", "state-space", "observer-design"]
aliases: ["BSc:ControlTheory"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Control_Theory"
    id: "7253"
    title: "BSc: Control Theory"
    last_modified: "2022-07-13T10:05:08Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:45:47+00:00"
status: draft
stale_after: "2024-07-12T10:05:08+00:00"
prerequisite_of: ["/courses/bsc-capstone-project.md", "/courses/bsc-robotic-systems.md"]
prerequisites: [{"course": "/courses/bsc-analytic-geometry-and-linear-algebra-i.md", "as_written": "[CSE204 - Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-i.md): Semidefinite matrices, Eigenvalues, Eigendecomposition (weak prerequisite), matrix exponentials (weak prerequisite), SVD (weak prerequisite)"}, {"course": "/courses/bsc-differential-equations.md", "as_written": "[CSE205 - Differential Equations](/courses/bsc-differential-equations.md)"}]
taught_by: ["/people/aleksandrmaloletov.md", "/people/sergeysavin.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSc: Control Theory

## Control Theory
- **Course name**: Control Theory
- **Code discipline**: [S20]
- **Subject area**: Sensors and actuators; Robotic control.

### Short Description
This course covers the following concepts: Introduction to Linear Control, Stability of linear dynamical systems; Controller design; Sensing, observers, Adaptive control.

### Prerequisites

#### Prerequisite subjects
- [CSE204 - Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-i.md): Semidefinite matrices, Eigenvalues, Eigendecomposition (weak prerequisite), matrix exponentials (weak prerequisite), SVD (weak prerequisite)
- [CSE205 - Differential Equations](/courses/bsc-differential-equations.md)

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Introduction to Linear Control, Stability of linear dynamical systems | # Control, introduction. Examples. <br> # Single input single output (SISO) systems. Block diagrams. <br> # From linear differential equations to state space models. <br> # DC motor as a linear system. <br> # Spring-damper as a linear system. <br> # The concept of stability of the control system. Proof of stability for a linear system with negative real parts of eigenvalues. <br> # Multi input multi output (MIMO) systems. <br> # Linear Time Invariant (LTI) systems and their properties. <br> # Linear Time Varying (LTV) systems and their properties. <br> # Transfer function representation. |
| Controller design. | # Stabilizing control. Control error. <br> # Proportional control. <br> # PD control. Order of a system and order of the controller. <br> # PID control. <br> # P, PD and PID control for DC motor. <br> # Trajectory tracking. Control input types. Standard inputs (Heaviside step function, Dirac delta function, sine wave). <br> # Tuning PD and PID. Pole placement. <br> # Formal statements about stability. Lyapunov theory. <br> # Types of stability; Lyapunov stability, asymptotic stability, exponential stability. <br> # Eigenvalues in stability theory. Reasoning about solution of the autonomous linear system. <br> # Stability proof for PD control. <br> # Stability in stabilizing control and trajectory tracking. <br> # Frequency response. Phase response. <br> # Optimal control of linear systems. From Hamilton-Jacobi-Bellman to algebraic Riccati equation. LQR. <br> # Stability of LQR. <br> # Controllability. |
| Sensing, observers, Adaptive control | # Modelling digital sensors: quantization, discretization, lag. <br> # Modelling sensor noise. Gaussian noise. Additive models. Multiplicative models. Dynamic sensor models. <br> # Observability. <br> # Filters. <br> # State observers. <br> # Optimal state observer for linear systems. <br> # Linearization of nonlinear systems. <br> # Linearization along trajectory. <br> # Linearization of Inverted pendulum dynamics. <br> # Model errors. Differences between random disturbances and unmodeled dynamics/processes. <br> # Adaptive control. <br> # Control for sets of linear systems. <br> # Discretization, discretization error. <br> # Control for discrete linear systems. <br> # Stability of discrete linear systems. |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
Linear Control Theory is both an active tool for modern industrial engineering and a prerequisite for most of the state-of-the-art level control techniques and the corresponding courses. With this in mind, the Linear Control course is both building a foundation for the following development of the student as a learner in the fields of Robotics, Control, Nonlinear Dynamics and others, as well as it is one of the essential practical courses in the engineering curricula.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- methods for control synthesis (linear controller gain tuning)
- methods for controller analysis
- methods for sensory data processing for linear systems

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- State-space models
- Eigenvalue analysis for linear systems
- Proportional and PD controllers
- How to stabilize a linear system
- Lyapunov Stability
- How to check if the system is controllable
- Observer design
- Sources of sensor noise
- Filters
- Adaptive Control
- Optimal Control
- Linear Quadratic Regulator

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Turn a system of linear differential equations into a state-space model.
- Design a controller by solving Algebraic Riccati eq.
- Find if a system is stable or not, using eigenvalue analysis. 
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
- Ogata, K., 1994. Solving control engineering problems with MATLAB. Englewood Cliffs, NJ: Prentice-Hall.
- Williams, R.L. and Lawrence, D.A., 2007. Linear state-space control systems. John Wiley & Sons.
- Ogata, K., 1995. Discrete-time control systems (Vol. 2, pp. 446-480). Englewood Cliffs, NJ: Prentice Hall.

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
| Question | What is a linear dynamical system? | 1 |
| Question | What is an LTI system? | 1 |
| Question | What is an LTV system? | 1 |
| Question | Provide examples of LTI systems. | 1 |
| Question | What is a MIMO system? | 1 |
| Question | Simulate a linear dynamic system as a higher order differential equation or in state-space form (Language is a free choice, Python and Google Colab are recommended. Use built-in solvers or implement Runge-Kutta or Euler method. | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is stability in the sense of Lyapunov? | 1 |
| Question | What is stabilizing control? | 1 |
| Question | What is trajectory tracking? | 1 |
| Question | Why the control for a state-space system does not include the derivative of the state variable in the feedback law? | 1 |
| Question | How can a PD controller for a second-order linear mechanical system can be re-written in the state-space form? | 1 |
| Question | Write a closed-loop dynamics for an LTI system with a proportional controller. | 1 |
| Question | Give stability conditions for an LTI system with a proportional controller. | 1 |
| Question | Provide an example of a LTV system with negative eigenvalues that is not stable. | 1 |
| Question | Write algebraic Riccati equation for a standard additive quadratic cost. | 1 |
| Question | Derive algebraic Riccati equation for a given additive quadratic cost. | 1 |
| Question | Derive differential Riccati equation for a standard additive quadratic cost. | 1 |
| Question | What is the meaning of the unknown variable in the Riccati equation? What are its property in case of LTI dynamics. | 1 |
| Question | What is a frequency response? | 1 |
| Question | What is a phase response? | 1 |
| Question | Design control for an LTI system using pole placement. | 0 |
| Question | Design control for an LTI system using Riccati (LQR). | 0 |
| Question | Simulate an LTI system with LQR controller. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are the sources of sensor noise? | 1 |
| Question | How can we combat the lack of sensory information? | 1 |
| Question | When it is possible to combat the lack of sensory information? | 1 |
| Question | How can we combat the sensory noise? | 1 |
| Question | What is an Observer? | 1 |
| Question | What is a filter? | 1 |
| Question | How is additive noise different from multiplicative noise? | 1 |
| Question | Simulate an LTI system with proportional control and sensor noise. | 0 |
| Question | Design an observer for an LTI system with proportional control and lack of sensory information. | 0 |
#### Final assessment
**Section 1**
1. Convert a linear differential equation into a state space form.
1. Convert a transfer function into a state space form.
1. Convert a linear differential equation into a transfer function.
1. What does it mean for a linear differential equation to be stable?
**Section 2**
1. You have a linear system: <math>{\displaystyle {\dot {x}}=Ax+Bu}</math>  and a cost function: a) <math>{\textstyle J=\int (x^{\top }Qx+u^{\top }Iu)dt}</math>  b) <math>{\textstyle J=\int (x^{\top }Ix+u^{\top }Ru)dt}</math>  Write Riccati eq. and find LQR gain analytically.
1. You have a linear system a) <math>{\textstyle {\begin{bmatrix}{\dot {x}}_{1}\\{\dot {x}}_{2}\end{bmatrix}}={\begin{bmatrix}1&10\\-3&4\end{bmatrix}}{\begin{bmatrix}x_{1}\\x_{2}\end{bmatrix}}}</math>  b) <math>{\textstyle {\begin{bmatrix}{\dot {x}}_{1}\\{\dot {x}}_{2}\end{bmatrix}}={\begin{bmatrix}-2&1\\2&40\end{bmatrix}}{\begin{bmatrix}x_{1}\\x_{2}\end{bmatrix}}}</math>  Prove whether or not it is stable.
1. You have a linear system a) <math>{\displaystyle {\begin{bmatrix}{\dot {x}}_{1}\\{\dot {x}}_{2}\end{bmatrix}}={\begin{bmatrix}1&10\\-3&4\end{bmatrix}}{\begin{bmatrix}x_{1}\\x_{2}\end{bmatrix}}+{\begin{bmatrix}u_{1}\\u_{2}\end{bmatrix}}}</math>  b) <math>{\displaystyle {\begin{bmatrix}{\dot {x}}_{1}\\{\dot {x}}_{2}\end{bmatrix}}={\begin{bmatrix}-2&1\\2&40\end{bmatrix}}{\begin{bmatrix}x_{1}\\x_{2}\end{bmatrix}}+{\begin{bmatrix}u_{1}\\u_{2}\end{bmatrix}}}</math>  Your controller is: a) <math>{\textstyle {\begin{bmatrix}u_{1}\\u_{2}\end{bmatrix}}={\begin{bmatrix}100&1\\1&20\end{bmatrix}}{\begin{bmatrix}x_{1}\\x_{2}\end{bmatrix}}}</math>  b) <math>{\textstyle {\begin{bmatrix}u_{1}\\u_{2}\end{bmatrix}}={\begin{bmatrix}7&2\\2&5\end{bmatrix}}{\begin{bmatrix}x_{1}\\x_{2}\end{bmatrix}}}</math>  Prove whether the control system is stable.
1. You have linear dynamics:
a) <math>{\textstyle 2{\ddot {q}}+3{\dot {q}}-5q=u}</math> 
b) <math>{\textstyle 10{\ddot {q}}-7{\dot {q}}+10q=u}</math> 
c) <math>{\textstyle 15{\ddot {q}}+17{\dot {q}}+11q=2u}</math> 
d) <math>{\textstyle 20{\ddot {q}}-{\dot {q}}-2q=-u}</math> 
If <math>{\textstyle u=0}</math> , which are stable (a - d)?
Find <math>{\textstyle u}</math>  that makes the dynamics stable.
Write transfer functions for the cases <math>{\textstyle u=0}</math>  and <math>{\textstyle u=-100x}</math> .
1. What is the difference between exponential stability, asymptotic stability and optimality?
**Section 3**
1. Write a model of a linear system with additive Gaussian noise.
1. Derive and implement an observer.
1. Derive and implement a filter.

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

<!-- catix:relations -->
## Relations

- Prerequisites: [BSc: Analytic Geometry And Linear Algebra I](/courses/bsc-analytic-geometry-and-linear-algebra-i.md) ([CSE204 - Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-i.md): Semidefinite matrices, Eigenvalues, Eigendecomposition (weak prerequisite), matrix exponentials (weak prerequisite), SVD (weak prerequisite)); [BSc: Differential Equations](/courses/bsc-differential-equations.md) ([CSE205 - Differential Equations](/courses/bsc-differential-equations.md))
- Required for: [BSc: Capstone Project](/courses/bsc-capstone-project.md), [BSc: Robotic Systems](/courses/bsc-robotic-systems.md)
- Taught by: [Aleksandr Maloletov](/people/aleksandrmaloletov.md), [Sergey Savin](/people/sergeysavin.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Control Theory](https://eduwiki.innopolis.university/index.php/BSc%3A_Control_Theory), revision 7253

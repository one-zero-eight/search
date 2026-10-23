---
type: course
title: "Control Theory (Linear Control)"
description: "Course description for Control Theory (Linear Control), covering key concepts, objectives, evaluation methods, and detailed section breakdowns."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3AControlTheoryLinearControl"
tags: ["control-theory", "linear-control", "robotics", "engineering", "msccourse"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3AControlTheoryLinearControl"
    id: "127"
    title: "MSc:ControlTheoryLinearControl"
    last_modified: "2021-07-30T11:24:55Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:30:36+00:00"
status: draft
stale_after: "2023-07-30T11:24:55+00:00"
prerequisite_of: ["/courses/msc-fundamentals-of-robot-control.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Control Theory (Linear Control)

## Control Theory (Linear Control)

- **Course name:** Control Theory (Linear Control)
- **Course number:** [F19] CI

### Course Characteristics

### What subject area does your course (discipline) belong to?

Sensors and actuators; Robotic control.

#### Key concepts of the class

- Introduction to Linear Control, Stability of linear dynamical systems
- Controller design
- Sensing, observers, Adaptive control

#### What is the purpose of this course?

Linear Control Theory is both an active tool for modern industrial engineering and a prerequisite for most of the state-of-the-art level control techniques and the corresponding courses. With this in mind, the Linear Control course is both building a foundation for the following development of the student as a learner in the fields of Robotics, Control, Nonlinear Dynamics and others, as well as it is one of the essential practical courses in the engineering curricula.

#### Course objectives based on Bloom’s taxonomy

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to outline:

- methods for control synthesis (linear controller gain tuning)
- methods for controller analysis
- methods for sensory data processing for linear systems

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to understand:

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

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to

- Turn a system of linear differential equations into a state-space model.
- Design a controller by solving Algebraic Riccati eq.
- Find if a system is stable or not, using eigenvalue analysis.

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 20 | 30 |
| Interim performance assessment | 30 | 20 |
| Exams | 50 | 50 |

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 | 85-100 |
| B. Good | 75-89 | 70-84 |
| C. Satisfactory | 60-74 | 50-69 |
| D. Poor | 0-59 | 0-49 |

#### Resources and reference material

Main textbook:

- Ogata, K., 1994. Solving control engineering problems with MATLAB. Englewood Cliffs, NJ: Prentice-Hall.

Other reference material:

- Williams, R.L. and Lawrence, D.A., 2007. Linear state-space control systems. John Wiley &amp; Sons.
- Ogata, K., 1995. Discrete-time control systems (Vol. 2, pp. 446-480). Englewood Cliffs, NJ: Prentice Hall.

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Introduction to Linear Control, Stability of linear dynamical systems | 6 |
| 2 | Controller design | 6 |
| 3 | Sensing, observers, Adaptive control | 6 |

#### Section 1

##### Section title:

Introduction to Linear Control, Stability of linear dynamical systems

#### Topics covered in this section:

- Control, introduction. Examples.
- Single input single output (SISO) systems. Block diagrams.
- From linear differential equations to state space models.
- DC motor as a linear system.
- Spring-damper as a linear system.
- The concept of stability of the control system. Proof of stability for a linear system with negative real parts of eigenvalues.
- Multi input multi output (MIMO) systems.
- Linear Time Invariant (LTI) systems and their properties.
- Linear Time Varying (LTV) systems and their properties.
- Transfer function representation.

#### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 0 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 1 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

#### Typical questions for ongoing performance evaluation within this section

1. What is a linear dynamical system?
1. What is an LTI system?
1. What is an LTV system?
1. Provide examples of LTI systems.
1. What is a MIMO system?

#### Typical questions for seminar classes (labs) within this section

1. Simulate a linear dynamic system as a higher order differential equation or in state-space form (Language is a free choice, Python and Google Colab are recommended. Use built-in solvers or implement Runge-Kutta or Euler method.

#### Test questions for final assessment in this section

1. Convert a linear differential equation into a state space form.
1. Convert a transfer function into a state space form.
1. Convert a linear differential equation into a transfer function.
1. What does it mean for a linear differential equation to be stable?

#### Section 2

##### Section title:

Controller design.

#### Topics covered in this section:

- Stabilizing control. Control error.
- Proportional control.
- PD control. Order of a system and order of the controller.
- PID control.
- P, PD and PID control for DC motor.
- Trajectory tracking. Control input types. Standard inputs (Heaviside step function, Dirac delta function, sine wave).
- Tuning PD and PID. Pole placement.
- Formal statements about stability. Lyapunov theory.
- Types of stability; Lyapunov stability, asymptotic stability, exponential stability.
- Eigenvalues in stability theory. Reasoning about solution of the autonomous linear system.
- Stability proof for PD control.
- Stability in stabilizing control and trajectory tracking.
- Frequency response. Phase response.
- Optimal control of linear systems. From Hamilton-Jacobi-Bellman to algebraic Riccati equation. LQR.
- Stability of LQR.
- Controllability.

#### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 0 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 0 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

#### Typical questions for ongoing performance evaluation within this section

1. What is stability in the sense of Lyapunov?
1. What is stabilizing control?
1. What is trajectory tracking?
1. Why the control for a state-space system does not include the derivative of the state variable in the feedback law?
1. How can a PD controller for a second-order linear mechanical system can be re-written in the state-space form?
1. Write a closed-loop dynamics for an LTI system with a proportional controller.
1. Give stability conditions for an LTI system with a proportional controller.
1. Provide an example of a LTV system with negative eigenvalues that is not stable.
1. Write algebraic Riccati equation for a standard additive quadratic cost.
1. Derive algebraic Riccati equation for a given additive quadratic cost.
1. Derive differential Riccati equation for a standard additive quadratic cost.
1. What is the meaning of the unknown variable in the Riccati equation? What are its property in case of LTI dynamics.
1. What is a frequency response?
1. What is a phase response?

#### Typical questions for seminar classes (labs) within this section

1. Design control for an LTI system using pole placement.
1. Design control for an LTI system using Riccati (LQR).
1. Simulate an LTI system with LQR controller.

#### Test questions for final assessment in this section

1. You have a linear system: <math display="block">\dot x = Ax + Bu</math> and a cost function: a) <math display="inline">J = \int (x^{\top} Q x + u^{\top} I u) dt</math> b) <math display="inline">J = \int (x^{\top} I x + u^{\top} R u) dt</math> Write Riccati eq. and find LQR gain analytically.
2. You have a linear system a) <math display="inline">\begin{bmatrix}
          \dot x_{1} \\
          \dot x_{2}
         \end{bmatrix} =  
\begin{bmatrix}
    1 & 10 \\
    -3 & 4
\end{bmatrix}   
\begin{bmatrix}
            x_{1} \\
            x_{2}
         \end{bmatrix}</math> b) <math display="inline">\begin{bmatrix}
          \dot x_{1} \\
          \dot x_{2}
         \end{bmatrix} =  
\begin{bmatrix}
    -2 & 1 \\
    2 & 40
\end{bmatrix}   
\begin{bmatrix}
            x_{1} \\
            x_{2}
         \end{bmatrix}</math> Prove whether or not it is stable.
3. You have a linear system a) <math display="block">\begin{bmatrix}
          \dot x_{1} \\
          \dot x_{2}
         \end{bmatrix} =  
\begin{bmatrix}
    1 & 10 \\
    -3 & 4
\end{bmatrix}   
\begin{bmatrix}
            x_{1} \\
            x_{2}
\end{bmatrix} + 
         \begin{bmatrix}
            u_{1} \\
            u_{2}
         \end{bmatrix}</math> b) <math display="block">\begin{bmatrix}
          \dot x_{1} \\
          \dot x_{2}
         \end{bmatrix} =  
\begin{bmatrix}
    -2 & 1 \\
    2 & 40
\end{bmatrix}   
\begin{bmatrix}
            x_{1} \\
            x_{2}
\end{bmatrix}+
         \begin{bmatrix}
            u_{1} \\
            u_{2}
         \end{bmatrix}</math> Your controller is: a) <math display="inline">\begin{bmatrix}
            u_{1} \\
            u_{2}
         \end{bmatrix} = 
\begin{bmatrix}
    100 & 1 \\
    1 & 20
\end{bmatrix}   
\begin{bmatrix}
            x_{1} \\
            x_{2}
         \end{bmatrix}</math> b) <math display="inline">\begin{bmatrix}
            u_{1} \\
            u_{2}
         \end{bmatrix} = 
\begin{bmatrix}
    7 & 2 \\
    2 & 5
\end{bmatrix}   
\begin{bmatrix}
            x_{1} \\
            x_{2}
         \end{bmatrix}</math> Prove whether the control system is stable.
4. You have linear dynamics:


| a) <math display="inline">2 \ddot q + 3 \dot q - 5 q = u</math> | b) <math display="inline">10 \ddot q - 7 \dot q + 10 q = u</math> |
| --- | --- |
| c) <math display="inline">15 \ddot q + 17 \dot q + 11 q = 2u</math> | d) <math display="inline">20 \ddot q - \dot q - 2 q = -u</math> |

<li>If <math display="inline">u = 0</math>, which are stable (a - d)?</li>
<li>Find <math display="inline">u</math> that makes the dynamics stable.</li>
<li>Write transfer functions for the cases <math display="inline">u = 0</math> and <math display="inline">u = -100x</math>.</li></ol>
</li>
<li>What is the difference between exponential stability, asymptotic stability and optimality?</li></ol>

#### Section 3

##### Section title:

Sensing, observers, Adaptive control

##### Topics covered in this section:

- Modelling digital sensors: quantization, discretization, lag.
- Modelling sensor noise. Gaussian noise. Additive models. Multiplicative models. Dynamic sensor models.
- Observability.
- Filters.
- State observers.
- Optimal state observer for linear systems.
- Linearization of nonlinear systems.
- Linearization along trajectory.
- Linearization of Inverted pendulum dynamics.
- Model errors. Differences between random disturbances and unmodeled dynamics/processes.
- Adaptive control.
- Control for sets of linear systems.
- Discretization, discretization error.
- Control for discrete linear systems.
- Stability of discrete linear systems.

#### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 0 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 0 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

#### Typical questions for ongoing performance evaluation within this section

1. What are the sources of sensor noise?
1. How can we combat the lack of sensory information?
1. When it is possible to combat the lack of sensory information?
1. How can we combat the sensory noise?
1. What is an Observer?
1. What is a filter?
1. How is additive noise different from multiplicative noise?

##### Typical questions for seminar classes (labs) within this section

1. Simulate an LTI system with proportional control and sensor noise.
1. Design an observer for an LTI system with proportional control and lack of sensory information.

##### Test questions for final assessment in this section

1. Write a model of a linear system with additive Gaussian noise.
1. Derive and implement an observer.
1. Derive and implement a filter.

<!-- catix:relations -->
## Relations

- Required for: [Fundamentals of Robot Control](/courses/msc-fundamentals-of-robot-control.md)
<!-- /catix:relations -->

# Citations

1. [MSc:ControlTheoryLinearControl](https://eduwiki.innopolis.university/index.php/MSc%3AControlTheoryLinearControl), revision 127

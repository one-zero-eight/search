---
type: course
title: "Fundamentals of Robot Control"
description: "Course F19 covering nonlinear control for robotics, including stability analysis, feedback linearization, and robust control design using MATLAB."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Fundamentals_of_Robot_Control"
tags: ["robotics", "control-theory", "nonlinear-control", "matlab", "msccourse"]
aliases: ["MSc:FundamentalsofRobotControl"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Fundamentals_of_Robot_Control"
    id: "7466"
    title: "MSc: Fundamentals of Robot Control"
    last_modified: "2022-08-29T08:44:23Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:35:07+00:00"
status: draft
stale_after: "2024-08-28T08:44:23+00:00"
prerequisites: [{"as_written": "python,"}, {"as_written": "numpy library,"}, {"as_written": "Google Colab environment"}, {"course": "/courses/bsc-mathematicalanalysis-i.md", "as_written": "CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II]: integration and differentiation, exponentials, gradient.", "via": "model"}, {"course": "/courses/bsc-mathematicalanalysis-ii.md", "as_written": "CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II]: integration and differentiation, exponentials, gradient.", "via": "model"}, {"course": "/courses/msc-analyticalgeometryandlinearalgebrai.md", "as_written": "CSE202 — Analytical Geometry and Linear Algebra I"}, {"course": "/courses/bsc-analytic-geometry-and-linear-algebra-ii.md", "as_written": "CSE204 — Analytic Geometry And Linear Algebra II: matrix multiplication, eigenvector and eigenvalue."}, {"course": "/courses/bsc-differential-equations.md", "as_written": "CSE205 — Differential Equations: state-space representation, homogeneous and nonhomogeneous equations, general solution of linear 1st and 2nd order ODEs, stability of solutions."}, {"course": "/courses/msc-controltheorylinearcontrol.md", "as_written": "Linear control theory: concepts of feedback, open- and closed-loop systems, linear controllers (PD, PID)", "via": "model"}]
relations_by: "process:catix-wiki-graph/0.1"
---

# Fundamentals of Robot Control

## Fundamentals of Robot Control
- **Course name**: Fundamentals of Robot Control
- **Code discipline**: F19
- **Subject area**: 

### Short Description
This course covers the following concepts: Introductory nonlinear control over dynamic systems with the focus on robotics; Stability, pros and cons of nonlinear control systems.

### Prerequisites

#### Prerequisite subjects
- python,
- numpy library,
- Google Colab environment
- CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II]: integration and differentiation, exponentials, gradient.
- CSE202 — Analytical Geometry and Linear Algebra I
- CSE204 — Analytic Geometry And Linear Algebra II: matrix multiplication, eigenvector and eigenvalue.
- CSE205 — Differential Equations: state-space representation, homogeneous and nonhomogeneous equations, general solution of linear 1st and 2nd order ODEs, stability of solutions.
- Linear control theory: concepts of feedback, open- and closed-loop systems, linear controllers (PD, PID)

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Motion. Kinematics. Dynamics. | # Free body motion <br> # Manipulator position and orientation <br> # Homogeneous transformations <br> # Forward and inverse kinematics <br> # Kinetic and potential energy <br> # Euler-Lagrange equations |
| Linear systems. Stability | # State-space equations <br> # Eigenvalues and eigenvectors <br> # Phase plane analysis <br> # Energy and stability <br> # Lyapunov’s direct method <br> # Lyapunov stability analysis |
| Feedback control systems | # Feedback and building control loops <br> # Stabilization and trajectory tracking <br> # Linear regulators (P, PD, PID) |
| Feedback linearization | # Joint-space inverse dynamics of serial manipulators <br> # Stabilization and trajectory tracking problems <br> # Input-state linearization |
| Robust control | # Sliding modes in dynamic systems <br> # Robust control in scalar and matrix form <br> # Stability and tuning of robust controllers <br> # Control law smoothening. |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
Control theory is an integral part of modern robotics, and there is a high chance that most students majoring in Robotics would face the problems of controlling a physical plant (a robot, manipulator, drone, autonomous vehicle) in their research and graduation work as well as their professional careers. Therefore, the main purpose of this course is to prepare the students for solving practical control problems by teaching the most fundamental approaches of nonlinear control used in modern robotics applications.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Basic structure of differential equations describing motion of robotic manipulators,
- Motivation behind and the basic structure of feedback control systems,
- How to find control system’s error dynamics and methods to analyze it,
- General structure of linear controllers (P, PD, PID),
- Physical motivation behind Lyapunov stability analysis,
- Basic structure of robust control system.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Name the main sources of nonlinearities in physical systems,
- Explain the cons of applying PID controllers to nonlinear systems,
- Understand pros and cons of feedback linearization method,
- Name pros and cons of robust control approach,
- Numerically solve differential equations in MATLAB environment.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Know how to analyze stability of physical systems with Lyapunov direct method,
- Design feedback linearization systems,
- Synthesize robust control systems and tune them,
- Implement nonlinear control in MATLAB environment to simulate the behavior of multi-DOF robotic systems. 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 80-100 | - |
| B. Good | 60-79 | - |
| C. Satisfactory | 40-59 | - |
| D. Poor | 0-39 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 0 |
| Interim performance assessment | 60 |
| Exams | 40 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- “Applied nonlinear control,” J.-J. Slotine & Weiping Li. Pearson, 1991.
- “Robotics: modelling, planning and control,” Bruno Siciliano, Lorenzo Sciavicco, Luigi Villani, and Giuseppe Oriolo. Springer Science & Business Media, 2010.
- “Robot modeling and control,” Mark Spong, Seth Hutchinson, M. Vidyasagar. John Wiley & Sons, 2006.
- “Modern Control Systems” (13th Edition), Richard Dorf & Robert H. Bishop. Pearson, 2016.
- “Modern Robotics: Mechanics, Planning, and Control,” Kevin Lynch, Frank Park. Cambridge University Press, 2017 (also, check out their video materials on YouTube).

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 | Section 5 |
| --- | --- | --- | --- | --- | --- |
| Homework and group projects | 1 | 1 | 0 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 0 | 1 | 0 |
| Discussions | 1 | 1 | 1 | 1 | 1 |
| Oral polls | 0 | 1 | 1 | 1 | 1 |
| Reports | 0 | 0 | 0 | 0 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Given initial and final object position and orientations, obtain the corresponding transformation matrix. | 1 |
| Question | Find the Jacobian for a given manipulator. | 1 |
| Question | For a given differential equation describing a physical system, and for given kinetic (K) and potential energies (U) do the following: <br> Show that there always exists a solution with respect to acceleration and that it is unique; <br> Demonstrate that the system’s Hamiltonian H = K + U remains constant in the absence of external torques and forces; <br> Show that the rate of change of the total energy equals instantaneous mechanical power. | 1 |
| Question | For a given manipulator with known Jacobian, do the following: <br> Find kinetic and potential energies of the robot; <br> Drive the Euler-Lagrange differential equation of motion. | 1 |
| Question | Do the following with MATLAB Robotics Toolbox: <br> Compute basic rotation and homogeneous transformation matrices; <br> Create a two-link manipulator and solve its forward kinematics; <br> Simulate forward dynamics; <br> Compute inertial, Coriolis and gravitational forces for the manipulator. | 0 |
| Question | Compute and analyze inertial tensor for a given robotic manipulator; | 0 |
| Question | For manipulators with different kinematic configurations, analytically derive their Jacobian matrices; | 0 |
| Question | Derive and analyze Euler-Lagrange equations describing dynamics of a given manipulator (required torques, singularities). | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Convert given differential equation into state-space form | 1 |
| Question | Find eigenvalue for a given matrix | 1 |
| Question | Show that given a constant matrix <math>{\textstyle {\textbf {M}}}</math>  and any time-varying vector <math>{\textstyle {\textbf {x}}}</math> , the time derivative of the scalar <math>{\textstyle \mathbf {x} ^{T}\mathbf {Mx} }</math>  can be written in the given form. | 1 |
| Question | For a given system of differential equations: <br> Find equilibria points; <br> Given a Lyapunov function, analyze system stability using Lyapunov’s direct method; <br> Analyze system stability in a given range. | 1 |
| Question | For a given differential equation, find the values of coefficients <math>{\textstyle k_{1}}</math>  and <math>{\textstyle k_{2}}</math>  that would make it critically damped. | 0 |
| Question | Convert a given system of differential equations into state-space form. | 0 |
| Question | For an equation given in the state space form, write it as an ordinary differential equation for specified input and output variables. | 0 |
| Question | Analyze system’s stability given equation of its full energy. | 0 |
| Question | Apply Lyapunov’s direct method to analyze stability of a physical system. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Give an example of using feedback in activities of daily life | 1 |
| Question | Drive error dynamics equations for a given feedback control law | 1 |
| Question | What are the physical analogies for the individual terms of PD-controller? | 1 |
| Question | How to implement PD regulator in MATLAB software? | 1 |
| Question | Solve numerically in MATLAB a second-order ODE for the following controller types: P, PD, PID. | 0 |
| Question | Analyze stability of a given linear control system. | 0 |
| Question | How individual gains of PD and PID controllers affect transient and steady-state response? | 0 |
| Question | How does underestimation of system parameters affect performance of linear controllers and how to improve it? | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | For a given differential equation that describes pendulum dynamicsm do the following: <br> Find control law transforming original dynamics into that of a linear mass-spring-damper system; <br> Write position error dynamics for the designed control law (inverse dynamics); <br> Repeat the previous steps if there are uncertainties in some of the system’s parameters. | 1 |
| Question | For a given general form of dynamics equation, demonstrate that the following control laws guarantee system stability. | 1 |
| Question | Simulate dynamics of given nonlinear system in MATLAB for given control law. | 1 |
| Question | Perform input-state linearization for a given system of differential equations. | 1 |
| Question | Find control law that linearizes a given differential equation. | 0 |
| Question | Analyze stability of given nonlinear systems and contribution of individual terms to system stability. | 0 |
| Question | Find general feedback linearization law for a given system of differential equations. | 0 |
| Question | Analyze stability and limitations of a given feedback linearization control law over a two-link manipulator. | 0 |
##### Section 5
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Name uncertainties typical for mechanical systems | 1 |
| Question | Analyze system behavior in sliding mode | 1 |
| Question | Simulate system behavior with robust control in MATLAB | 1 |
| Question | Numerically implement control law smoothening for a robust controller. | 1 |
| Question | How to synthesize robust controller for a given range of system parameters’ deviations? | 0 |
| Question | Describe the effect of robust gain coefficient <math>{\textstyle k}</math>  on system stability, control output and resulting system behavior. | 0 |
| Question | Design robust controller for a dynamical system described by a given set of differential equations and implement it in MATLAB. | 0 |
| Question | Analyze stability of robust control system for a robotic manipulator with given equation of motion. | 0 |
#### Final assessment
**Section 1**
1. What is a rotation matrix and what does it describe?
1. How to find a homogeneous transformation matrix? How is it different from rotation matrix?
1. What is manipulator Jacobian? How does it relate static forces and torques? How can one use the Jacobian to analyze manipulator singularities?
1. What is physical nature of the terms of Euler-Lagrange equations of robot motion?
1. What are the main properties of the basic terms of differential equations of motion (invertibility, positive definiteness, singularities, limits).
**Section 2**
1. Evaluate stability of a linear system whose dynamics is written in the state-space form.
1. What must be the properties of Lyapunov function candidate and its time derivative to confirm
Local stability,
Global stability of the system.
1. How to analyze system’s stability based on its phase portrait (with examples)?
1. Describe physical motivation behind Lyapunov’s direct method and how it used to analyze stability of dynamical systems.
**Section 3**
1. What is the physical analog of PD-regulator in application to control over second-oder mechanical systems?
1. For a given system described by differential equations, design a linear control system and analyze its stability.
1. Describe pros and cons of linear controllers in application to nonlinear system control.
**Section 4**
1. What are the pros and cons of feedback linearization approach?
1. Provide examples of systems (differential equations) for which feedback linearization can result in infinite control effort.
1. What are the typical issues when applying feedback linearization approach to control over robotic manipulators?
**Section 5**
1. Describe typical sources of uncertainties and parameter deviations in models of physical and mechanical systems, their typical ranges and influence on system behavior.
1. Name pros and cons of robust control systems with and without control law smoothening.
1. How to tune robust controller terms to compensate for system uncertainties?

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

**Section 5**

<!-- catix:relations -->
## Relations

- Prerequisites: python,; numpy library,; Google Colab environment; [BSc: Mathematical Analysis I](/courses/bsc-mathematicalanalysis-i.md) (CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II]: integration and differentiation, exponentials, gradient., matched by the model); [BSc: Mathematical Analysis II](/courses/bsc-mathematicalanalysis-ii.md) (CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II]: integration and differentiation, exponentials, gradient., matched by the model); [Analytical Geometry and Linear Algebra I](/courses/msc-analyticalgeometryandlinearalgebrai.md) (CSE202 — Analytical Geometry and Linear Algebra I); [BSc: Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md) (CSE204 — Analytic Geometry And Linear Algebra II: matrix multiplication, eigenvector and eigenvalue.); [BSc: Differential Equations](/courses/bsc-differential-equations.md) (CSE205 — Differential Equations: state-space representation, homogeneous and nonhomogeneous equations, general solution of linear 1st and 2nd order ODEs, stability of solutions.); [Control Theory (Linear Control)](/courses/msc-controltheorylinearcontrol.md) (Linear control theory: concepts of feedback, open- and closed-loop systems, linear controllers (PD, PID), matched by the model)
<!-- /catix:relations -->

# Citations

1. [MSc: Fundamentals of Robot Control](https://eduwiki.innopolis.university/index.php/MSc%3A_Fundamentals_of_Robot_Control), revision 7466

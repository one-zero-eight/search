---
type: course
title: "BSc: Robotic Systems"
description: "A course covering robot hardware, feedback control, trajectory tracking, and advanced control algorithms for robotic systems with 1 and 2 degrees of freedom."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Robotic_Systems"
tags: ["robotics", "control", "robotic-systems", "bsc", "course"]
aliases: ["BSc:RoboticSystems"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Robotic_Systems"
    id: "7218"
    title: "BSc: Robotic Systems"
    last_modified: "2022-07-12T09:58:29Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:48:38+00:00"
status: draft
stale_after: "2024-07-11T09:58:29+00:00"
prerequisites: [{"course": "/courses/bsc-mathematicalanalysis-ii.md", "as_written": "CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II: ordinary and partial derivatives, definite and indefinite integrals.", "via": "model"}, {"course": "/courses/bsc-mathematicalanalysis-i.md", "as_written": "CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II: ordinary and partial derivatives, definite and indefinite integrals.", "via": "model"}, {"course": "/courses/bsc-analyticalgeometryandlinearalgebrai-cs.md", "as_written": "CSE202 — Analytical Geometry and Linear Algebra I and ACSE204 — Analytic Geometry And Linear Algebra II: matrix operations, eigenvalues and eigenvectors", "via": "model"}, {"course": "/courses/bsc-analytic-geometry-and-linear-algebra-ii.md", "as_written": "CSE202 — Analytical Geometry and Linear Algebra I and ACSE204 — Analytic Geometry And Linear Algebra II: matrix operations, eigenvalues and eigenvectors", "via": "model"}, {"course": "/courses/bsc-differential-equations.md", "as_written": "CSE205 — Differential Equations: first- and second-order ODEs, state-space representation and modeling, concepts of stability (Lyapunov, asymptotic, exponential)"}, {"as_written": "What are the fundamental principles behind DC and BLDC motors,"}, {"as_written": "How to tune PD controllers to achieve critically damped response,"}, {"as_written": "What is gravity compensation and how it is implemented in robotic systems,"}, {"as_written": "What is inverse dynamics."}, {"as_written": "What are the advantages of BLDC motors over DC motors,"}, {"as_written": "Why PD and PID controllers constitute the majority of industrial controllers,"}, {"as_written": "What methods exist for trajectory generation and tracking,"}, {"course": "/courses/bsc-nonlinearcontroltheory.md", "as_written": "How to design an inverse dynamics controller.", "via": "model"}, {"course": "/courses/bsc-control-theory.md", "as_written": "Tune PD and PID controllers,", "via": "model"}, {"as_written": "Design stable position controllers for manipulators,"}, {"course": "/courses/bsc-nonlinearcontroltheory.md", "as_written": "Develop nonlinear controllers such as gravity compensation and inverse dynamics,", "via": "model"}, {"course": "/courses/bsc-microcontrollersandembeddedhardware.md", "as_written": "Interface practical robotic hardware (BLDC motors, encoders, microcontrollers) and implement their control algorithms.", "via": "model"}, {"course": "/courses/bsc-control-theory.md", "as_written": "Interface practical robotic hardware (BLDC motors, encoders, microcontrollers) and implement their control algorithms.", "via": "model"}]
taught_by: ["/people/igorgaponov.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSc: Robotic Systems

## Robotic Systems
- **Course name**: Robotic Systems
- **Code discipline**: 
- **Subject area**: Robotics; Robotic components; Robotic control.

### Short Description
This course covers the following concepts: Robot hardware; Feedback control in application to robotic systems; Trajectory tracking and advanced control algorithms.

### Prerequisites

#### Prerequisite subjects
- CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II: ordinary and partial derivatives, definite and indefinite integrals.
- CSE202 — Analytical Geometry and Linear Algebra I and ACSE204 — Analytic Geometry And Linear Algebra II: matrix operations, eigenvalues and eigenvectors
- CSE205 — Differential Equations: first- and second-order ODEs, state-space representation and modeling, concepts of stability (Lyapunov, asymptotic, exponential)
- What are the fundamental principles behind DC and BLDC motors,
- How to tune PD controllers to achieve critically damped response,
- What is gravity compensation and how it is implemented in robotic systems,
- What is inverse dynamics.
- What are the advantages of BLDC motors over DC motors,
- Why PD and PID controllers constitute the majority of industrial controllers,
- What methods exist for trajectory generation and tracking,
- How to design an inverse dynamics controller.
- Tune PD and PID controllers,
- Design stable position controllers for manipulators,
- Develop nonlinear controllers such as gravity compensation and inverse dynamics,
- Interface practical robotic hardware (BLDC motors, encoders, microcontrollers) and implement their control algorithms.

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Robot Hardware | # DC and BLDC motors <br> # Position sensors (encoders) <br> # CAN bus |
| Feedback Control | # Review of feedback control <br> # PD controllers <br> # PID controllers <br> # Gravity compensation <br> # Stability of linear systems |
| Position tracking in robots | # Linear feedback control in application to manipulators <br> # Lyapunov stability analysis <br> # Stabilization and trajectory tracking |
| Energy, impedance, and force control | # Joint-space inverse dynamics of serial manipulators <br> # Energy-based control of compliant robots <br> # Passivity-based control <br> # Adaptive control of flexible joint manipulators |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The purpose of this course is to review the concepts of linear control theory and then learn some advanced control methods while applying them to practical simple robotic systems with 1 and 2 degrees of freedom. The course also presents all the necessary background of such fundamental components of robotic manipulators as DC and BLDC motors, encoders, microcontrollers and CAN bus (communication protocol). Based on these, the course teaches the student to design and implement on practice simple and advanced control approaches and teaches the students to tune and analyze stability of selected controllers in application to robotic systems.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- What are the fundamental principles behind DC and BLDC motors,
- How to tune PD controllers to achieve critically damped response,
- What is gravity compensation and how it is implemented in robotic systems,
- What is inverse dynamics.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- What are the advantages of BLDC motors over DC motors,
- Why PD and PID controllers constitute the majority of industrial controllers,
- What methods exist for trajectory generation and tracking,
- How to design an inverse dynamics controller.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Tune PD and PID controllers,
- Design stable position controllers for manipulators,
- Develop nonlinear controllers such as gravity compensation and inverse dynamics,
- Interface practical robotic hardware (BLDC motors, encoders, microcontrollers) and implement their control algorithms. 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 85-100 | - |
| B. Good | 70-84 | - |
| C. Satisfactory | 55-69 | - |
| D. Poor | 0-54 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 30 |
| Quizzes | 30 |
| Final exam | 40 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources


#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 |
| --- | --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 0 | 0 | 0 |
| Homework and group projects | 1 | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 |
| Reports | 1 | 1 | 0 | 0 |
| Discussions | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Describe the basic operation principle of DC motors. | 1 |
| Question | What are the main advantages of BLDC motors over DC motors? | 1 |
| Question | Describe operation principles of optical and magnetic encoders. | 1 |
| Question | Rewrite the equation of DC motor in the state space form. | 0 |
| Question | Rewrite the equation of cart pole system in the state space form with the state <math>{\textstyle \mathbf {x} =[\theta ,{\dot {\theta }},x,{\dot {x}}]^{T}}</math> . | 0 |
| Question | Find eigen system (values and vectors) of following matrices by hand | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are overshoot and settling time? | 1 |
| Question | How do the gains of PD controller affect transient response parameters? | 1 |
| Question | sdf | 1 |
| Question | Find stiffness matrix of a given parallel robotic platform. | 0 |
| Question | Perform matrix structural analysis of a cantilever beam. | 0 |
| Question | Find stiffness matrix of a two-link manipulator with elastic joint. | 0 |
| Question | Estimate identification accuracy for 3-link manipulator. | 0 |
| Question | Comment on differences between compliance matrix of a manipulator obtained via CAD modeling and identification results. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Give an example of using feedback in activities of daily life. | 1 |
| Question | Drive error dynamics equations for a given feedback control law. | 1 |
| Question | For a given differential equation describing robot dynamics and several control laws, find which ones are stable using Lyapunov stability theory. | 1 |
| Question | How does elasticity affect error dynamics in robot control applications? | 1 |
| Question | What components of mechanical energy exist in robots with compliance? | 1 |
| Question | Design PD controller for a rigid two-link manipulator. | 0 |
| Question | Numerically model behavior of compliant robot with PID controller. | 0 |
| Question | Compare performance of linear controllers in application to rigid and 2-link manipulator control. | 0 |
| Question | Analyze stability of a given controller. | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Provide examples of passive and active systems. | 1 |
| Question | What are limit cycles? | 1 |
| Question | What happens with the energy of passive systems with time? | 1 |
| Question | For a given differential equation that describes pendulum dynamics, do the following: | 1 |
| Question | Perform input-state linearization for a given system of differential equations. | 1 |
| Question | Find limit cycles of a given robot with compliance. | 0 |
| Question | Design gravity and compliance compensator for a robot with flexible joints. | 0 |
| Question | Implement and simulate passivity-based control over given robot. | 0 |
| Question | For a given differential equation that describes pendulum dynamics, do the following: <br> Find control law transforming original dynamics into that of a linear mass-spring-damper system; <br> Write position error dynamics for the designed control law (inverse dynamics); <br> Repeat the previous steps if there are uncertainties in some of the system’s parameters. | 0 |
#### Final assessment
**Section 1**
1. Write a differential equation that describes the mechanical part of DC motor.
1. Write a differential equation that describes the electrical part of DC motor.
1. How many CPTs must a 2-channel magnetic encoder have if you want to measure the output displacement of a DC motor with the resolution of 0.1 degree?
**Section 2**
1. Describe main stiffness modeling approaches, their particularities, advantages and limitations.
1. Use variable joint model for a serial manipulator (assume all elements are flexible) to find stiffness matrix.
1. Describe particularities and difficulties of the elastostatic calibration.
1. Find the controller gains that will stabilize a system described by a second order differential equation.
**Section 3**
1. What challenges does robot compliance pose for a control system?
1. Design a position tracking controller for a given compliant system.
1. How does cable elasticity affect dynamics and control of tendon-driven robots?
**Section 4**
1. Provide examples of practical systems with non-collocated feedback. What unique challenges does this pose for control systems?
1. Design a position tracking controller for a given compliant system.
1. Analyze stability of a given system with passivity-based controller
1. What are the physical fundamentals behind the concept of passivity and passivity-based control?

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

<!-- catix:relations -->
## Relations

- Prerequisites: [BSc: Mathematical Analysis II](/courses/bsc-mathematicalanalysis-ii.md) (CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II: ordinary and partial derivatives, definite and indefinite integrals., matched by the model); [BSc: Mathematical Analysis I](/courses/bsc-mathematicalanalysis-i.md) (CSE201 — Mathematical Analysis I and CSE203 — Mathematical Analysis II: ordinary and partial derivatives, definite and indefinite integrals., matched by the model); [Analytical Geometry and Linear Algebra I (CS)](/courses/bsc-analyticalgeometryandlinearalgebrai-cs.md) (CSE202 — Analytical Geometry and Linear Algebra I and ACSE204 — Analytic Geometry And Linear Algebra II: matrix operations, eigenvalues and eigenvectors, matched by the model); [BSc: Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md) (CSE202 — Analytical Geometry and Linear Algebra I and ACSE204 — Analytic Geometry And Linear Algebra II: matrix operations, eigenvalues and eigenvectors, matched by the model); [BSc: Differential Equations](/courses/bsc-differential-equations.md) (CSE205 — Differential Equations: first- and second-order ODEs, state-space representation and modeling, concepts of stability (Lyapunov, asymptotic, exponential)); What are the fundamental principles behind DC and BLDC motors,; How to tune PD controllers to achieve critically damped response,; What is gravity compensation and how it is implemented in robotic systems,; What is inverse dynamics.; What are the advantages of BLDC motors over DC motors,; Why PD and PID controllers constitute the majority of industrial controllers,; What methods exist for trajectory generation and tracking,; [Nonlinear Control Theory](/courses/bsc-nonlinearcontroltheory.md) (How to design an inverse dynamics controller., matched by the model); [BSc: Control Theory](/courses/bsc-control-theory.md) (Tune PD and PID controllers,, matched by the model); Design stable position controllers for manipulators,; [Nonlinear Control Theory](/courses/bsc-nonlinearcontroltheory.md) (Develop nonlinear controllers such as gravity compensation and inverse dynamics,, matched by the model); [Microcontrollers and Embedded Hardware](/courses/bsc-microcontrollersandembeddedhardware.md) (Interface practical robotic hardware (BLDC motors, encoders, microcontrollers) and implement their control algorithms., matched by the model); [BSc: Control Theory](/courses/bsc-control-theory.md) (Interface practical robotic hardware (BLDC motors, encoders, microcontrollers) and implement their control algorithms., matched by the model)
- Taught by: [Igor Gaponov](/people/igorgaponov.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Robotic Systems](https://eduwiki.innopolis.university/index.php/BSc%3A_Robotic_Systems), revision 7218

---
type: course
title: "Advanced Robotics"
description: "A course on elastostatic modeling, calibration, and advanced control approaches for compliant robotic systems, covering stiffness modeling, kinematics, and passivity-based control."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Advanced_Robotics"
tags: ["robotics", "control", "compliance", "calibration", "elastostatic", "advanced"]
aliases: ["MSc:Advanced Robotics"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Advanced_Robotics"
    id: "7470"
    title: "MSc: Advanced Robotics"
    last_modified: "2022-08-29T08:48:29Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:11:59+00:00"
status: draft
stale_after: "2024-08-28T08:48:29+00:00"
prerequisites: [{"as_written": "Matlab or Python, Numpy library,"}, {"as_written": "Google Colab environment."}, {"course": "/courses/bsc-mathematicalanalysis-i.md", "as_written": "CSE201 — Mathematical Analysis I", "via": "model"}, {"course": "/courses/bsc-mathematicalanalysis-ii.md", "as_written": "CSE203 — Mathematical Analysis II: differentiation, exponentials, gradient.", "via": "model"}, {"course": "/courses/msc-analyticalgeometryandlinearalgebrai.md", "as_written": "CSE202 — Analytical Geometry and Linear Algebra I"}, {"course": "/courses/bsc-analytic-geometry-and-linear-algebra-ii.md", "as_written": "CSE204 — Analytic Geometry And Linear Algebra II: matrix multiplication, change of the bases, orthonormal spaces, cross product and skew-symmetric matrices, eigenvector and eigenvalue, SVD."}, {"course": "/courses/bsc-physics-i.md", "as_written": "CSE402 — Physics I (Mechanics) and CSE410 — Physics II - Electrical Engineering]: Kinematics, Statics and Dynamics."}, {"course": "/courses/msc-advanced-statistics.md", "as_written": "Statistics: Linear regression, .Covariance matrix, Information matrix, Observability matrix, Design of Experiments, Statistical evaluation", "via": "model"}, {"as_written": "Screw theory."}, {"as_written": "Product of Exponents (PoE)"}]
taught_by: ["/people/alexanderklimchik.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Advanced Robotics

## Advanced Robotics
- **Course name**: Advanced Robotics
- **Code discipline**: 
- **Subject area**: Robotic control.

### Short Description
This course covers the following concepts: Elastostatic modeling and calibration of robots; Advanced control approaches for compliant robotic systems.

### Prerequisites

#### Prerequisite subjects
- Matlab or Python, Numpy library,
- Google Colab environment.
- CSE201 — Mathematical Analysis I
- CSE203 — Mathematical Analysis II: differentiation, exponentials, gradient.
- CSE202 — Analytical Geometry and Linear Algebra I
- CSE204 — Analytic Geometry And Linear Algebra II: matrix multiplication, change of the bases, orthonormal spaces, cross product and skew-symmetric matrices, eigenvector and eigenvalue, SVD.
- CSE402 — Physics I (Mechanics) and CSE410 — Physics II - Electrical Engineering]: Kinematics, Statics and Dynamics.
- Statistics: Linear regression, .Covariance matrix, Information matrix, Observability matrix, Design of Experiments, Statistical evaluation
- Screw theory.
- Product of Exponents (PoE)

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Stiffness modeling | # Position and velocity kinematics <br> # Virtual joint modeling <br> # Finite element analysis <br> # Matrix structural analysis |
| Robot calibration | # Types of robot calibration <br> # Sources of uncertainties and model errors in practical robots <br> # Robot errors <br> # Complete, irreducible geometric models <br> # Elastostatic calibration |
| Position tracking | # Adaptive control of flexible joint manipulators <br> # Adaptive robust control <br> # Modeling and control of cable-driven robotic systems |
| Energy, impedance, and force control | # Energy-based control of compliant robots <br> # Limit cycles <br> # Passivity-based control <br> # Impedance control |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
While traditional robotics studies rigid robots and manipulators, many practical robotic systems exhibit non-negligible compliance. Its effects can be both detrimental (for instance, decrease in positioning accuracy of industrial manipulators) and beneficial (improved safety during human-robot interaction), depending on the application. However, regardless of whether the robot’s compliance is positive or negative, it must be accurately accounted for during modeling, trajectory tracking and robot control tasks. The main purpose of this course is to introduce elastostatic modeling of manipulators and robotic systems, methods for calibration of these devices, as well as advanced approaches to control robotic systems with non-negligible stiffness.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- How to derive expressions for position kinematics and differential kinematics of serial manipulators,
- What approaches exist to model robot joints’ elasticity,
- How to model dynamics of compliant robots,
- Fundamental principles of position tracking control for robots with compliance,
- Motivation behind energy-based approaches to control elastic robots.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- How to find Jacobian for series and parallel robots and use it to compute forces and torques,
- What constitutes a common manipulator calibration procedure,
- Reasons and examples of singularities for serial and parallel robots,
- How to drive elastic robots into limit cycles and what benefits does it bring in terms of control effort,
- How to model and control tendon-driven robots.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Find stiffness matrix for given manipulator,
- Analyze joint constraints and find singularities,
- Perform robot calibration procedure,
- Apply passivity principle to design stable position controllers,
- Design force controller for elastic and compliant robots. 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 90-100 | - |
| B. Good | 75-89 | - |
| C. Satisfactory | 60-74 | - |
| D. Poor | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 10 |
| Interim performance assessment | 60 |
| Exams | 30 |

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
| Homework and group projects | 1 | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Name types of robot workspace. | 1 |
| Question | Name key features and differences between serial and parallel manipulators. | 1 |
| Question | What is Jacobian matrix and how to use it for singularity analysis. | 1 |
| Question | What is stiffness matrix of manipulator and what does it describe? | 1 |
| Question | Find stiffness matrix of a given parallel robotic platform. | 0 |
| Question | Apply direct FEA method to analyze compliance of a given manipulator. | 0 |
| Question | Perform matrix structural analysis of a cantilever beam. | 0 |
| Question | Find stiffness matrix of a two-link manipulator with elastic joint. | 0 |
| Question | Model stiffness of a non-rigid mobile platform. | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Why is robot calibration needed? | 1 |
| Question | What are the main sources of errors in robot parameters? | 1 |
| Question | Give examples of geometric and non-geometric errors. | 1 |
| Question | Describe typical steps of calibration procedure. | 1 |
| Question | Drive information matrix of a 2-link manipulator. | 0 |
| Question | Estimate identification accuracy for 4-link manipulator. | 0 |
| Question | Comment on differences between compliance matrix of a manipulator obtained via CAD modeling and identification results. | 0 |
| Question | Perform model reduction for a given manipulator. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What challenges does robot compliance pose for a control system? | 1 |
| Question | What are the mathematical fundamentals of adaptive control? | 1 |
| Question | How does cable elasticity affect dynamics of tendon-driven robots? | 1 |
| Question | How to perform feedback linearization for a given compliant robot? | 1 |
| Question | Design PD controller with gravity compensation for a manipulator with elastic joint. | 0 |
| Question | Numerically model behavior of compliant robot with nonlinear controller. | 0 |
| Question | Numerically model and compare accuracy and power efficiency of robust and adaptive controllers for a cable-driven robot. | 0 |
| Question | Analyze stability of adaptive controller. | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Provide examples of passive and active systems. | 1 |
| Question | What are limit cycles? | 1 |
| Question | What components of mechanical energy exist in robots with compliance? | 1 |
| Question | What happens with the energy of passive systems with time? | 1 |
| Question | Find limit cycles of a given robot with compliance. | 0 |
| Question | Design gravity and compliance compensator for a robot with flexible joints. | 0 |
| Question | Simulate numerically behavior of a compliant robot during cyclic motion. | 0 |
| Question | Implement and simulate passivity-based control over given robot. | 0 |
#### Final assessment
**Section 1**
1. Describe main stiffness modeling approaches, their particularities, advantages and limitations.
1. Use variable joint model for a serial manipulator (assume all elements are flexible) to find stiffness matrix.
1. Drive VSJ and MSA models of the tripteron robot shown.
**Section 2**
1. Describe particularities and difficulties of the elastostatic calibration.
1. What do good/bad accuracy and repeatability mean?
1. What is complete, irreducible geometric model and why do we need it?
1. Find complete and irreducible model for geometric calibration of robot presented below.
**Section 3**
1. Provide examples of practical systems with non-collocated feedback. What unique challenges does this pose for control systems?
1. Design a position tracking controller for a given compliant system.
1. Analyze stability of a given nonlinear control approach.
**Section 4**
1. What are the physical fundamentals behind the concept of passivity and passivity-based control?
1. Drive the dynamics of a given elastically actuated robot.
1. Analyze stability of a given system with passivity-based controller.

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

<!-- catix:relations -->
## Relations

- Prerequisites: Matlab or Python, Numpy library,; Google Colab environment.; [BSc: Mathematical Analysis I](/courses/bsc-mathematicalanalysis-i.md) (CSE201 — Mathematical Analysis I, matched by the model); [BSc: Mathematical Analysis II](/courses/bsc-mathematicalanalysis-ii.md) (CSE203 — Mathematical Analysis II: differentiation, exponentials, gradient., matched by the model); [Analytical Geometry and Linear Algebra I](/courses/msc-analyticalgeometryandlinearalgebrai.md) (CSE202 — Analytical Geometry and Linear Algebra I); [BSc: Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md) (CSE204 — Analytic Geometry And Linear Algebra II: matrix multiplication, change of the bases, orthonormal spaces, cross product and skew-symmetric matrices, eigenvector and eigenvalue, SVD.); [Physics I (mechanics)](/courses/bsc-physics-i.md) (CSE402 — Physics I (Mechanics) and CSE410 — Physics II - Electrical Engineering]: Kinematics, Statics and Dynamics.); [Advanced Statistics](/courses/msc-advanced-statistics.md) (Statistics: Linear regression, .Covariance matrix, Information matrix, Observability matrix, Design of Experiments, Statistical evaluation, matched by the model); Screw theory.; Product of Exponents (PoE)
- Taught by: [Alexander Klimchik](/people/alexanderklimchik.md)
<!-- /catix:relations -->

# Citations

1. [MSc: Advanced Robotics](https://eduwiki.innopolis.university/index.php/MSc%3A_Advanced_Robotics), revision 7470

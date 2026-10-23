---
type: course
title: "BSc: Signals And Systems"
description: "Course covering discrete signals, systems classification, filters, DFT, and FFT, including prerequisites, learning outcomes, and assessment details."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Signals_And_Systems"
tags: ["signals", "systems", "dsp", "bsc", "engineering"]
aliases: ["BSc:SignalsAndSystems"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Signals_And_Systems"
    id: "7255"
    title: "BSc: Signals And Systems"
    last_modified: "2022-07-13T10:11:46Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:14:20+00:00"
status: draft
stale_after: "2024-07-12T10:11:46+00:00"
prerequisites: [{"course": "/courses/bsc-analytic-geometry-and-linear-algebra-i.md", "as_written": "[CSE202 — Analytical Geometry and Linear Algebra](/courses/bsc-analytic-geometry-and-linear-algebra-i.md): complex numbers, vecrors and matrix operations, basis and basis decomposition, concept of eigen values and vectors."}, {"course": "/courses/bsc-mathematical-analysis-i.md", "as_written": "[CSE201 — Mathematical Analysis I](/courses/bsc-mathematical-analysis-i.md): limits and absolutly summabale series, exponent function, besic integration."}, {"course": "/courses/bsc-logic-and-discrete-mathematics.md", "as_written": "[CSE113 — Philosophy I - (Discrete Math and Logic)](/courses/bsc-logic-and-discrete-mathematics.md): Algorithm time and space complexity."}]
taught_by: ["/people/nikolayshilov.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSc: Signals And Systems

## Signals and Systems
- **Course name**: Signals and Systems
- **Code discipline**: XYZ
- **Subject area**: Electric Engineering

### Short Description
This course covers the following concepts: discrete(-time) signals, their impulse and frequency domains; classification of (discrete) systems (bound-input-bound-output, linear and shift-invariant); filters and filtering, finite and infinite impulse response filters; discrete(-time) Fourier transform and fast Fourier transform.

### Prerequisites

#### Prerequisite subjects
- [CSE202 — Analytical Geometry and Linear Algebra](/courses/bsc-analytic-geometry-and-linear-algebra-i.md): complex numbers, vecrors and matrix operations, basis and basis decomposition, concept of eigen values and vectors. 
- [CSE201 — Mathematical Analysis I](/courses/bsc-mathematical-analysis-i.md): limits and absolutly summabale series, exponent function, besic integration.
- [CSE113 — Philosophy I - (Discrete Math and Logic)](/courses/bsc-logic-and-discrete-mathematics.md): Algorithm time and space complexity.

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Complex numbers and functions, vector and Hilbert Spaces, computational aspects | # Complex numbers and their matrix representation <br> # Vector spaces with dot-product <br> # Metrics and convergence, Hilbert spaces <br> # Algorithms and their computational (space and time) complexity |
| Discrete Fourier Transform and Fast Fourier Transforms (DFT and FFT) | # Circular convolution, eigen vectors and values of the circular convolution <br> # Discrete Fourier Transform (DFT) and its inverse <br> # Circutate filters and filtering <br> # Fast Fourier Transform (FFT),its inverse, and computational aspects of DFT and fast FFT |
| Discrete-time signals and systems: properties and classification | # Kotelnikov-Whittaker–Nyquist–Shannon  sampling Theorem. <br> # Discrete signals as sequences, spaces of absolutely summable and bounded sequences. <br> # Auto- and cross-correlation; memoryless, causal and shift-invariant systems <br> # Linear systems, their matrix representation and properties <br> # Convolution and its relations to linear shift-invariant systems |
| Convolution, Discrete-time Fourier Transformation, filtering | # Math preliminaries on complex exponent and Euler formulas. <br> # Introduction of the discrete-time Fourier transform via convolution eigen values and vectors. <br> # Discrete-time Fourier transform as the frequency response of a linear shift-invariant system. <br> # Inverse discrete-time Fourier transform. <br> # DTFT properties (including convolution theorem). <br> # Elements of ideal Filter Design. |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The goal of the course is to present mathematical foundations of digital signal processing altogether with practical experience to design finite and infinite impulse response filters. The course is aimed to provide basic mathematical knowledge and practical skills needed for further studies of applied signal processing and digital signal processing from engineering as well as from mathematical perspective.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- discrete (time) signals and systems, their classification
- linear shift-invariant systems, filters and filtering
- Discrete Fourier Transformation (DFT)
- Fast discrete Fourier Transformation (FFT)
- Discrete-Time Fourier Transformation (DTFT),

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- relations between analog and digital signals (sampling)
- relations between convolution, correlation, and filtering of discrete signals
- role of impulse and frequency  domains of discrete signals
- differences between infinite and finite discrete signals
- role of discrete time Fourier transform and its inverse
- role of discrete Fourier transform (DFT) and fast DFT (FFT)

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- basic numerical tools from mathematical package SciLab/Octave
- classify discrete signals and systems
- design and implement infinite and finite impulse response filters
- implement and use discrete time Fourier transform,
- implement and use discrete Fourier transform and fast DFT. 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 104-130 | - |
| B. Good | 84-103 | - |
| C. Satisfactory | 65-83 | - |
| D. Poor | 0-64 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 20 |
| Interim performance assessment | 90 |
| Exams | 20 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Martin Vetterli, Jelena Kovacevic, and Vivek K Goyal.Foundations of Signal Processing.Cambridge University Press, 2014. ISBN 10703860X
- Oppenheim, Alan V., and A. S. Willsky. Signals and Systems (2nd ed.) Prentice Hall, 1996. ISBN  0-13-814757-4.
- Richard G. Lyons.UnderstandingDigitalSignalProcessing. Prentice Hall, 2010. ISBN 978-0137027415

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 |
| --- | --- | --- | --- | --- |
| Homework and group projects | 1 | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 0 | 0 | 0 |
| Reports | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 |
| Development of individual parts of software product code | 0 | 1 | 1 | 1 |
| Midterm evaluation | 0 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Prove that each complex number has a square root. | 1 |
| Question | Prove that the neutral element is unique in a vector space. | 1 |
| Question | Prove that pixel (Manhattan) and Euclidean norms are equivalent in finite-dimensional real (complex) spaces. | 1 |
| Question | Is the set of integers complete in the discrete metrics? | 1 |
| Question | What is space and time complexity of dot product in a complex n-dimensional vector space? | 1 |
| Question | Prove that each complex number but zero has the inverse. | 0 |
| Question | Prove that each vector of a vector space has unique opposite element. | 0 |
| Question | Prove that pixel and the universal norms are equivalent in finite-dimensional real(complex) spaces. | 0 |
| Question | Is the set of rational numbers complete in the discrete metrics? | 0 |
| Question | What is space and time complexity of finite matrices multiplication (according to the definition)? | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Compute circular convolution of given two short  integer signals. | 1 |
| Question | Explain Discrete Fourier Transform  as orthogonal vector decomposition. | 1 |
| Question | Compute DFT and FFT for given short  integer signal. | 1 |
| Question | Prove circular impulse shift property. | 0 |
| Question | Study commutativity,  linearity and associativity of the circular convolution. | 0 |
| Question | Give matrix representation for the circular convolution for several small dimensions. | 0 |
| Question | Recall 2-redex fast Fourier transform and draw its matrices  for several small dimensions. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Give examples of (infinite) absolutely summable/non-summable, bounded/unbounded,etc., signals. | 1 |
| Question | Is autocorrelation linear system? Is it shift-invariant? | 1 |
| Question | Prove that a linear system is memoryless iff its matrix is diagonal. | 1 |
| Question | Prove that a linear system is causal iff its matrix is low-triangle. | 0 |
| Question | A linear system is shift-invariant iff its matrix consists (exclusively) of diagonals of some constant (individual for each diagonal). | 0 |
| Question | Prove that product of finite power series is convolution of the finite signals consisting of the coefficients of these series. | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Do there exists a periodic function with non-commensurable periods? | 1 |
| Question | Prove that product of two exponents is equal to the exponent with sum of powers. | 1 |
| Question | Prove conjugate property for DTFT. | 1 |
| Question | Prove DTFT-correspondence for impulse shift. | 0 |
| Question | Prove DTFT-correspondence for frequency shift. | 0 |
| Question | Design a low-band filter with a given spectrum consisting of a single box. | 0 |
#### Final assessment
**Section 1**
1. Build if possible (or prove that it isn’t) ...
**Section 2**
1. Assume that a finite signal ...
**Section 3**
1. Compute cross-correlation of two box signals.
1. Study properties (linearity, causality, stability, etc.) of a weighted accumulator
**Section 4**
1. Show that exponent with imaginary power is a periodic function, find the smallest period.
1. Prove sampling and scaling properties for the Dirac Delta function.

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

<!-- catix:relations -->
## Relations

- Prerequisites: [BSc: Analytic Geometry And Linear Algebra I](/courses/bsc-analytic-geometry-and-linear-algebra-i.md) ([CSE202 — Analytical Geometry and Linear Algebra](/courses/bsc-analytic-geometry-and-linear-algebra-i.md): complex numbers, vecrors and matrix operations, basis and basis decomposition, concept of eigen values and vectors.); [BSc: Mathematical Analysis I](/courses/bsc-mathematical-analysis-i.md) ([CSE201 — Mathematical Analysis I](/courses/bsc-mathematical-analysis-i.md): limits and absolutly summabale series, exponent function, besic integration.); [Logic and Discrete Mathematics (CSE113)](/courses/bsc-logic-and-discrete-mathematics.md) ([CSE113 — Philosophy I - (Discrete Math and Logic)](/courses/bsc-logic-and-discrete-mathematics.md): Algorithm time and space complexity.)
- Taught by: [Nikolay Shilov](/people/nikolayshilov.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Signals And Systems](https://eduwiki.innopolis.university/index.php/BSc%3A_Signals_And_Systems), revision 7255

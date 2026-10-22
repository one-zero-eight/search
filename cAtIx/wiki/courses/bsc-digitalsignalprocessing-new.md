---
type: course
title: "Digital Signal Processing"
description: "Course description for Digital Signal Processing (XYZ), covering key concepts, objectives, evaluation methods, and section details."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3ADigitalSignalProcessing_new"
tags: ["digital-signal-processing", "course", "electric-engineering", "dsp", "signal-processing"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3ADigitalSignalProcessing_new"
    id: "29"
    title: "BSc:DigitalSignalProcessing new"
    last_modified: "2021-07-30T10:06:42Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:51:23+00:00"
status: draft
stale_after: "2023-07-30T10:06:42+00:00"
prerequisite_of: ["/courses/bsc-practical-machine-learning-deep-learning.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Digital Signal Processing

## Digital Signal Processing

- **Course name:** Digital Signal Processing
- **Course number:** XYZ
- **Subject area:** Electric Engineering

### Course characteristics

#### Key concepts of the class

- discrete(-time) signals, their impulse and frequency domains
- finite and infinite impulse response filters
- discrete(-time) Fourier transform and fast Fourier transform

#### What is the purpose of this course?

The goal of the course is to present mathematical foundations of signal processing altogether with practical experience to design finite and infinite impulse response filters. The course is aimed to provide basic mathematical knowledge and practical skills needed for further studies of applied signal processing and digital signal processing from engineering as well as from mathematical perspective.

#### Course Objectives Based on Bloom’s Taxonomy

#### - What should a student remember at the end of the course?

- discrete time signals and systems, their classification,
- linear shift-invariant systems, filters and filtering,
- Discrete-time Fourier Transformation (DTFT),
- Discrete Fourier Transformation (DTFT),
- Fast Discrete Fourier Transformation (FDFT).

#### - What should a student be able to understand at the end of the course?

- relations between analog and digital signals,
- what are discrete signals, their convolution, auto-correlation and cross-correlation,
- role of impulse and frequency domains of discrete signals,
- differences between infinite and finite discrete signals,
- role of discrete time Fourier transform and its inverse,
- role of discrete Fourier transform (DFT) and fast DFT.

#### - What should a student be able to apply at the end of the course?

- basic numerical tools from mathematical package SciLab/Octave,
- classify discrete signals and systems,
- design and implement infinite and finite impulse response filters,
- implement and use discrete time Fourier transform,
- implement and use discrete Fourier transform and fast DFT.

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 20 | 20 |
| Interim performance assessment | 30 | 90 |
| Exams | 50 | 60 |

If necessary, please indicate freely your course’s features in terms of students’ performance assessment:

##### Labs/seminar classes:

- In-class participation 1 point for each individual contribution in a class but not more than 1 point a week (i.e. 14 points in total for 14 study weeks),
- overall course contribution (to accumulate extra-class activities valuable to the course progress, e.g. a short presentation, book review, very active in-class participation, etc.) up to 6 points.

##### Interim performance assessment:

- Each of 6 home-made individual lab (computational) assignments costs 15 points (i.e. 90 points for all 6 assignments).

##### Exams:

- in-class tests up to 10 points for each of 2 test (i.e. up to 20 points for both test),
- mid-term exam and final examination costs up to 20 points each (i.e. 40 points for both).

##### Overall score:

170 points (100%).

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 | 136-170 |
| B. Good | 75-89 | 119-135 |
| C. Satisfactory | 60-74 | 102-118 |
| D. Poor | 0-59 | 0-101 |

If necessary, please indicate freely your course’s grading features:

- A: at least 80% of the overall score;
- B: at least 70% of the overall score;
- C: at least 60% of the overall score;
- D: less than 60% of the overall score.

#### Resources and reference material

##### Textbook:

- 

##### Reference material:

- 
- 

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Lectures** | **Seminars** | **Self-study** | **Knowledge** |
| --- | --- | --- | --- | --- | --- |
| **Number** |  | **(hours)** | **(labs)** |  | **evaluation** |
| 1 | Complex numbers and functions, vector and Hilbert Spaces, computational aspects | 4 | 4 | 4 | 1 |
| 2 | Discrete-time signals and systems: properties and classification | 6 | 6 | 6 | 2 |
| 3 | Discrete-time Fourier Transformation | 6 | 6 | 6 | 0 |
| 4 | Discrete Fourier Transform (DFT) and Fast Discrete Fourier Transforms (FDFT’s) | 6 | 6 | 6 | 1 |
| Final examination |  |  |  |  | 2 |

#### Section 1

##### Section title:

Complex numbers and functions, vector and Hilbert Spaces, computational aspects

#### Topics covered in this section:

- Complex numbers and their matrix representation
- Vector spaces with dot-product
- Metrics and convergence, Hilbert spaces
- Algorithms and their computational (space and time) complexity

#### What forms of evaluation were used to test students’ performance in this section?



|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 1

Homework and group projects &amp; 0

Midterm evaluation &amp; 0

Testing (written or computer based) &amp; 1

Reports &amp; 1

Essays &amp; 0

Oral polls &amp; 0

Discussions &amp; 1





#### Typical questions for ongoing performance evaluation within this section

1. Prove that each complex number has a square root.
1. Prove that the neutral element is unique in a vector space.
1. Prove that pixel (Manhattan) and Euclidean norms are equivalent in finite-dimensional real (complex) spaces.
1. Is the set of integers complete in the discrete metrics?
1. What is space and time complexity of dot product in a complex n-dimensional vector space?

#### Typical questions for seminar classes (labs) within this section

1. Prove that each complex number but zero has the inverse.
1. Prove that each vector of a vector space has unique opposite element.
1. Prove that pixel and the universal norms are equivalent in finite-dimensional real (complex) spaces.
1. Is the set of rational numbers complete in the discrete metrics?
1. What is space and time complexity of finite matrices multiplication (according to the definition)?

#### Test questions for final assessment in this section

1. Build if possible (or prove that it isn’t) a real <math display="inline">2\times 2</math> matrix with given real eigen values <math display="inline">d>0</math> and <math display="inline">m>0</math>.
1. Let <math display="inline">X</math> be a set and function <math display="inline">d:X\rightarrow R</math> be defined as <math display="inline">d(a,b)=\ if\ a=b\ then\ 0\ else\ 10^6</math>. Prove that this function is a metrics.
1. What is time complexity to compute product of two real polynomials of order <math display="inline">n\geq 0</math>?.

#### Section 2

##### Section title:

Discrete-time signals and systems: properties and classification

#### Topics covered in this section:

- Discrete signals as sequences, spaces <math display="inline">l^1</math>, <math display="inline">l^2</math> and <math display="inline">l^\infty</math>
- Auto- and cross-correlation; memoryless, causal and shift-invariant systems
- Linear systems, their matrix representation and properties
- Convolution and its relations to linear shift-invariant systems

#### What forms of evaluation were used to test students’ performance in this section?



|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 1

Homework and group projects &amp; 0

Midterm evaluation &amp; 1

Testing (written or computer based) &amp; 0

Reports &amp; 1

Essays &amp; 0

Oral polls &amp; 0

Discussions &amp; 1





#### Typical questions for ongoing performance evaluation within this section

1. Give examples of (infinite) signals in <math display="inline">l^1</math>, <math display="inline">l^2\setminus l^1</math>, <math display="inline">l^\infty\setminus l^2</math>.
1. Is autocorrelation linear system? Is it shift-invariant?
1. Prove that a linear system is memoryless iff its matrix is diagonal.
1. Assuming a signal in <math display="inline">l^2</math> and <math display="inline">\epsilon>0</math>, evaluate number of component of the signal that is sufficient to compute autocorrelation with (component-wise) accuracy <math display="inline">\epsilon</math>.

#### Typical questions for seminar classes (labs) within this section

1. Prove that a linear system is causal iff its matrix is low-triangle.
1. A linear system is shift-invariant iff its matrix consists (exclusively) of diagonals of some constant (individual for each diagonal).
1. Assuming a signal <math display="inline">a</math> in <math display="inline">l^2</math>, a signal <math display="inline">b</math> in <math display="inline">l^2</math> and <math display="inline">\epsilon>0</math>, evaluate number of component of the signal <math display="inline">a</math> that is sufficient to compute convolution <math display="inline">(a*b)</math> with (component-wise) accuracy <math display="inline">\epsilon</math>.
1. Prove that product of finite power series is convolution of the finite signals consisting of the coefficients of these series.

#### Test questions for final assessment in this section

1. Compute cross-correlation of two box signals.
1. Study properties (linearity, causality, stability, etc.) of a weighted accumulator.
1. Prove associativity of convolution of finite signals (using finite series interpretation).
1. Let <math display="inline">u</math> be Heaviside signal, <math display="inline">D</math> — be signal delay operator, <math display="inline">\mathbf{\delta}</math> — be Kroneker signal, and <math display="inline">\mathbf{1}</math> — be a constant signal where all components are <math display="inline">1</math>; compare <math display="inline">\left(u*\left(\mathbf{\delta}-D(\mathbf{\delta})\right)\right)*\mathbf{1}</math> and <math display="inline">u*\left(\left(\mathbf{\delta}-D(\mathbf{\delta})\right)*\mathbf{1}\right)</math> and conclude about convolution associativity for the infinite signals.

#### Section 3

##### Section title:

#### Typical questions for ongoing performance evaluation within this section

1. Prove <math display="inline">e^a\times e^b=e^{a+b}</math> for all complex numbers <math display="inline">a</math> and <math display="inline">b</math>.
1. Do there exists a periodic function with periods <math display="inline">1</math> and <math display="inline">\sqrt{2}</math> simultaneously?
1. Let <math display="inline">h</math> be a signal. Express <math display="inline">H(e^{-j\omega})</math> in terms of <math display="inline">H(e^{j\omega})</math>
1. Apply filter <math display="inline">h_n=\ if\ n=0\ then\ 0\ else\ \frac{1}{n^2}</math> to the signals with the angular frequencies <math display="inline">\omega\in\{0, \frac{\pi}{4}, \frac{\pi}{3}, \frac{2\pi}{3}, \frac{\pi}{2}, \frac{4\pi}{3}, \frac{5\pi}{4}, \pi\}</math>.
1. Prove conjugate property for DTFT: <math display="inline">x_n^*\stackrel{DTFT}{\longleftrightarrow}X^*(e^{j\omega})</math>.

#### Typical questions for seminar classes (labs) within this section

1. Assuming <math display="inline">h</math> to be a real-valued signal; what are real-valued eigen-sequences of LSI-system <math display="inline">H</math>? (– I.e. what is <math display="inline">\omega</math>-frequency <math display="inline">\lambda_\omega</math> to be real?).
1. Prove DTFT-correspondence for impulse shift: <math display="inline">x_{n-m}\stackrel{DTFT}{\longleftrightarrow}e^{-jm\omega}X(e^{j\omega})</math>.
1. Assume that <math display="inline">(c_n)</math> is the cross-correlation of two signals <math display="inline">x</math> and <math display="inline">y</math>; prove that <math display="inline">c_n\stackrel{DTFT}{\longleftrightarrow}X(e^{j\omega})Y^*(e^{j\omega})</math>.
1. Prove that <math display="inline">\int_{-\infty}^{+\infty}f(t+t_0)\delta(t)dt\ =\ \int_{-\infty}^{+\infty}f(t)\delta(t-t_0)dt\ =\ f(t_0)</math> (where <math display="inline">\delta</math> is the Dirac Delta-function).
1. Design a low-band filter with a given spectrum consisting of a single box in the range <math display="inline">[-\pi,+\pi]</math>.

#### Test questions for final assessment in this section

1. Show that <math display="inline">e^{ix}</math> is a periodic function, find the smallest period of <math display="inline">e^{ix}</math>.
1. Prove DTFT-correspondence for frequency shift: <math display="inline">e^{jn\phi}x_n \stackrel{DTFT}{\longleftrightarrow}X(e^{j(\omega-\phi)})</math>.
1. Prove sampling and scaling properties for the Dirac Delta function:
  - <math display="inline">g\left(t\right)\delta\left(t\right)=g\left(0\right)\delta\left(t\right)</math>;
  - <math display="inline">\delta\left(\frac{t}{a}\right)=\left|a\right|\delta
        \left(t\right)</math> for every real <math display="inline">a\neq 0</math>.
1. Explain how to design a low-band filter with a given spectrum consisting of superposition of several boxes (each in the range <math display="inline">[-\pi,+\pi]</math>).

#### Section 4

##### Section title:

Discrete Fourier Transform (DFT) and Fast Discrete Fourier Transforms (FDFT’s)

#### Topics covered in this section:

- Circular convolution and its relations to the linear convolution
- Eigen vectors and values of the circular convolution
- Discrete Fourier transform and its relations to DTFT
- Computational aspects of DFT and fast DFT
- Kotelnikov-Nyquist–Shannon theorem

#### What forms of evaluation were used to test students’ performance in this section?



|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 1

Homework and group projects &amp; 0

Midterm evaluation &amp; 0

Testing (written or computer based) &amp; 1

Reports &amp; 1

Essays &amp; 0

Oral polls &amp; 0

Discussions &amp; 1





#### Typical questions for ongoing performance evaluation within this section

1. Then linear convolution of a circularly extended finite signal <math display="inline">x</math> with period <math display="inline">m</math> with any signal <math display="inline">h</math> is also a signal with period <math display="inline">m</math>.
1. Let <math display="inline">u</math> be the Heaviside filter and <math display="inline">h_n=\frac{u_n}{3^n}</math>. Compute and represent the periodized filters <math display="inline">h^1</math>, <math display="inline">h^2</math>, <math display="inline">h^3</math>, <math display="inline">h^4</math> and <math display="inline">h^m</math> (where <math display="inline">m\geq 5</math>).
1. Study commutativity, linearity and associativity of the circular convolution.
1. Compute and compare linear and circular convolution (with period <math display="inline">m\in [3..8]</math>) for signals <math display="inline">x=(\mathbf{4}, 5, 6, 2)</math> and <math display="inline">y=(\mathbf{a},2, a)</math>.
1. Compute all circular exponent signals for <math display="inline">m=4</math>.
1. Explain discrete Fourier transform as orthogonal vector decomposition.

#### Typical questions for seminar classes (labs) within this section

1. Prove that linear convolution of an absolutely summable filter with a circular signal equals to the circular extension of the periodized filter with the main period of the signal.
1. Prove circular impulse shift: <math display="inline">x_{(n-p)\mod{m}} \stackrel{DFT}{\longleftrightarrow} W^{kp}_m X_k</math>.
1. Give matrix representation for the circular convolution <math display="inline">(x^(*^)y)</math> where <math display="inline">x=(\mathbf{1},2,3,4,5)</math>.
1. Recall 2-redex fast Fourier transform and draw matrices <math display="inline">A_m</math> for several first natural values <math display="inline">m</math>.

#### Test questions for final assessment in this section

1. Assume that a finite signal <math display="inline">y</math> has a finite support <math display="inline">[-m,+m]</math> (for some <math display="inline">m\geq 0</math>); then <math display="inline">x_n*_n y_n\ =\ \sum_{k=-m}^{k=+m} x_k y_{n-k}</math> every signal <math display="inline">x</math> (not necessary finite).
1. Assume that signal <math display="inline">h\in l^1</math>; prove that periodized signal <math display="inline">(h^m)_n=\sum_{k\in\mathbf{Z}}h_{n+km}</math> is correctly defined for all integer <math display="inline">m\geq 0</math>.
1. Prove circular frequency shift (also known as modulation): <math display="inline">W^{-kp}_m x_n \stackrel{DFT}{\longleftrightarrow} X_{(k-p)\mod{m}}</math>.
1. Give matrix representation for DFT and IDFT for some first natural <math display="inline">m</math>.
1. Explain the inverse of the discrete Fourier transform as reconstruction of a vector after its orthogonal decomposition.
1. Give example of applications of Kotelnikov-Nyquist–Shannon theorem.

<!-- catix:relations -->
## Relations

- Required for: [Practical Machine Learning and Deep Learning](/courses/bsc-practical-machine-learning-deep-learning.md)
<!-- /catix:relations -->

# Citations

1. [BSc:DigitalSignalProcessing new](https://eduwiki.innopolis.university/index.php/BSc%3ADigitalSignalProcessing_new), revision 29

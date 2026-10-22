---
type: course
title: "Numerical Modelling"
description: "A mathematics course covering numerical algorithms, differentiation, integration, interpolation, and solving algebraic and differential equations."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3ANumericalModelling"
tags: ["course", "mathematics", "numerical-methods", "programming", "simulation"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3ANumericalModelling"
    id: "77"
    title: "BSc:NumericalModelling"
    last_modified: "2021-07-30T10:48:29Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:41:06+00:00"
status: draft
stale_after: "2023-07-30T10:48:29+00:00"
---

# Numerical Modelling

## Numerical Modelling

- **Course name:** Numerical Modelling
- **Course number:** XYZ
- **Subject area:** Math

### Course characteristics

#### Key concepts of the class

- An understanding of the basic "canon" of numerical algorithms and numerical methods relevant to computing given task

#### What is the purpose of this course?

This course answer on the next questions. To what problems does an algorithm or method apply? How does the method work? How does the method compare to alternatives (in terms of appropriate computational metrics)? What can go wrong? What are the sources of error and uncertainty?

#### Course Objectives Based on Bloom’s Taxonomy

#### - What should a student remember at the end of the course?

- Understand key principles involved in numerical solution of typical mathematical problems.
- Become familiar with numerical differentiation and integration.
- Solve systems of non/linear algebraic equations numerically by different ways.
- Become familiar with methods of interpolation and regression.
- Get hands-on experience with numerical solving system of nonlinear differential equations.

#### - What should a student be able to understand at the end of the course?

- Key principles involved in numerical solution of typical mathematical problems.
- How to apply numerical differentiation and integration.
- How to solve systems of non/linear algebraic equations numerically by different ways.
- How to apply methods of interpolation and regression.
- How to make numerical solving system of nonlinear differential equations.

#### - What should a student be able to apply at the end of the course?

- Numerical solution of typical mathematical problems
- Make nonlinear regression and interpolation
- Make numerical differentiation and integration
- Numerical solution systems of non/linear algebraic equations
- Numerical solving system of nonlinear differential equations

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 20 | 30 |
| Interim performance assessment | 30 | 30 |
| Exams | 50 | 50 |

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 | 85-100 |
| B. Good | 75-89 | 65-84 |
| C. Satisfactory | 60-74 | 50-64 |
| D. Poor | 0-59 | 0-49 |

#### Resources and reference material

##### Textbooks:

- Gilbert Strang. Computational Science and Engineering. Wellesley, MA: Wellesley-Cambridge Press, 2007. 727 Pg. ISBN: 9780961408817.
- I.B. Petrov, A.I. Lobanov. Lectures in Computational Mathematics. M.: Internet University of Information Technology, 2006. 523 c. ISBN: 5-94774-542-9.

##### Reference material:

- Jaan Kiusalaas. Numerical Methods in Engineering with Python. Cambridge University Press, 2005. 433 Pg. ISBN: 978-0-521-85287-6.

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Lectures** | **Seminars** | **Self-study** | **Knowledge** |
| --- | --- | --- | --- | --- | --- |
| **Number** |  | **(hours)** | **(labs)** |  | **evaluation** |
| 1 | Numerical differentiation and integration, functions interpolation, solution of system of linear algebraic equations. | 14 | 14 | 28 | 2 |
| 2 | Solution of nonlinear algebraic equations and systems. Solving of ODEs and PDEs. Discrete Fourier Series. | 12 | 12 | 24 | 2 |
| Final examination |  |  |  |  | 2 |

#### Section 1

##### Section title:

Numerical differentiation and integration, functions interpolation, solution of system of linear algebraic equations

#### Topics covered in this section:

- Key concerns of numerical computations. Accuracy of floating-point arithmetic.
- Numerical differentiation. Method of undetermined coefficients.
- Interpolation of functions. Splines.
- Numerical integration. Quadrature formulas.
- Solution of system of linear algebraic equations.

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| --- | --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 1 |
| Reports | 0 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

#### Typical questions for ongoing performance evaluation within this section

1. How to perform numerical differentiation by the method of undetermined coefficients?
1. How to perform interpolation of function by using splines?
1. How to perform numerical integration by using quadrature formulas?
1. How to solve a system of linear algebraic equations by using iteration methods?
1. How to solve a system of linear algebraic equations by using variation methods?

#### Typical questions for seminar classes (labs) within this section

1. To make numerical differentiation by the method of undetermined coefficients.
1. To make function interpolation by using splines.
1. To make numerical integration by using quadrature formulas.
1. To Solve a system of linear algebraic equations by using iteration methods?
1. To solve a system of linear algebraic equations by using variation methods?

#### Test tasks for final assessment in this section

1. You are requested to compute the integral of a black box function. The function would be supplied to you at the compile time in the form of a header file `blackbox.h`. At the very beginning of your program you should read single integer `n` from the standard input call the function `blackbox-init(n)`. `blackbox-init` should only be called once. All other functions should only be called after `blackbox-init`. Calling `blackbox_init` with argument different from the one supplied via standard input leads to undefined behaviour.
When you want to get the value of the function at point `x` you should call `blackbox(x)`. This function is guaranteed to be thread-safe. `x` should be in range [-1; 1].
If you want to get the maximum absolute value of the `k-th` derivative of the black box function on the integration interval, you should call `blackbox-df(k)`. The `k` should be integer from 1 to 6.
To check if the black box function is oscillating you should call `blackbox-period()`.
The returned value would be the period length if the function is oscillating, and 0 otherwise.
The required absolute precision is `10^-9`. The truncated `blackbox.h` file (implementing only one of possible blackbox functions) and an example (suboptimal) solution `solution.cpp` are available to you on the “Files” tab in PCMS.
You should only submit your `solution.c/solution.cpp` file. The appropriate `blackbox.h` will be supplied by the testing system.
You should not try to reverse-engineer the black box and/or interact with it in any way except through the four functions listed above.
2. The task is simple: you have to fit a set of points with a 9-degree polynomial
$y = a_9x^9+a_8x^8+...+a_1x+a_0$.
Your program receives the following stream of commands:
- ADD `x` `y` Read values `x` and `y`.
- FIT Print the coefficients for a polynomial fitted through all the points read since the beginning of the program. You will have no more than 13 FIT commands in each test.
- END Print the coefficients for a polynomial fitted through all the points read since the beginning of the program, and quit.

You will get no more than 107 commands before END.
3. The task is simple: you have to solve a system of linear algebraic equations (SLAE) $Ax = b$ with residual no more than $10^-9$.
And the matrix $A$ is very nice: non-singular, symmetric and strictly diagonally dominant. A piece of cake, you might think. The catch: you do not have $A$ in any explicit form.
You can only get the result of its multiplication with the vector.
You have a number of the blackbox functions through which you work with the SLAE:
- void `blackbox-init()` – initializes the internal blackbox data structures. Should be called in the very beginning of the program! No other blackbox function should be called before it, and no reading from the `stdin` shall be made (or at least, as they say, “be kind, rewind”).
- int `blackbox-size()` – returns the number of equations (which is equal to the number of unknowns) of the system. The number of equations lies between 10 and 10000 (inclusive).
- void `blackbox-mult` (const double `*x`, double `*out`) – compute the product of $A$ and vector $x$, write the results to out. The pointers $x$ and out should point to different chunks of memory of size at least `blackbox-size() * sizeof(double)` bytes each.

void blackbox-rhs(double *b) – write the right-hand side of the SLAE (i.e., vector b) to the array b. The pointer b should point to the chunk if memory of size at least blackbox-size() * sizeof(double) bytes.
void blackbox-submit(double *solution) – write the result of the program. The array solution should contain the solution to the SLAE: blackbox-size() values of type double. This should the last function to be called by your program (besides return 0;).

#### Section 2

##### Section title:

Solution of nonlinear algebraic equations and systems. Solving of ODEs and PDEs. Discrete Fourier Series.

#### Topics covered in this section:

- Numerical solution of nonlinear algebraic equations and systems.
- Basic concepts of the theory of difference schemes. Numerical methods for solving of initial value problem for ordinary differential equations (ODEs).
- Numerical methods for solving of boundary value problems for ODEs.
- Discrete Fourier Series. Numerical solution of second-order ODEs by Discrete Fourier Series. Numerical solution of the partial differential equations (PDEs) by Discrete Fourier Series.
- Variable-directions method. Numerical solution of the PDEs by finite difference methods.

#### What forms of evaluation were used to test students’ performance in this section?



|a|c| & **Yes/No**

Development of individual parts of software product code & 1

Homework and group projects & 1

Midterm evaluation & 1

Testing (written or computer based) & 1

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 1





#### Typical questions for ongoing performance evaluation within this section

1. How to perform numerical solution of nonlinear algebraic equations and systems.
1. How to perform numerical solution of initial value problem for ordinary differential equations (ODEs).
1. How to perform numerical solution of boundary value problems for ODEs.
1. How to perform numerical solution of ODEs and PDEs by Discrete Fourier Series.
1. How to perform numerical solution of the PDEs by finite difference methods.

#### Typical questions for seminar classes (labs) within this section

1. To make numerical solution of nonlinear algebraic equations and systems.
1. To make numerical solution of initial value problem for ordinary differential equations (ODEs).
1. To make numerical solution of boundary value problems for ODEs.
1. To make numerical solution of ODEs and PDEs by Discrete Fourier Series.
1. To make numerical solution of the PDEs by finite difference methods.

#### Test tasks for final assessment in this section

<ol>
<li>You have to build software for a new GPS/GLONASS receiver. The satellite navigation works as follows (of course, this is a rather simplified description of a real-world situation). There are <math display="inline">N</math> &lt; 30 satellites. Every satellite broadcasts its position (<math display="inline">x_i; y_i; z_i</math>) and high-precision synchronized time <math display="inline">t_i</math>. These signals take time to reach the receiver (e.g., the one that’s in your smartphone). If the receiver has position <math display="inline">x</math>; <math display="inline">y</math>; <math display="inline">z</math>, and receives the signal at time <math display="inline">t</math>, the following equation (called “Navigation equation”) holds true (For simplicity, we choose the speed of light <math display="inline">c</math> = 1):
<math display="inline">(x - x_i)^2 + (y - y_i)^2 + (z - z_i)^2 = (t - t_i)^2</math>
As we can see, we have four unknowns (the position of the receiver <math display="inline">x</math>; <math display="inline">y</math>; <math display="inline">z</math> and the precise time <math display="inline">t</math> when it received the signal). So, we need at least <math display="inline">N</math> = 4 satellites to get the location of the receiver (“fix”). The system of exactly four navigational equations might, in general, have multiple solutions. But usually, more than <math display="inline">N</math> &gt; 4 satellites are visible, and we have an overdetermined system of nonlinear equations (due to noise, the equations can not be satisfied exactly). In this case, our goal is to minimize the sum of squares of residuals:
<math display="inline">Sum_i((x - x_i)^2 + (y - y_i)^2 + (z - z_i)^2 - (t - t_i)^2) \xrightarrow{} min</math>.
You program should continuously read data from a virtual GPS receiver and print the position in each moment until the signal is lost. The number of satellites (and their order) can change. The initial position is unknown, but the position between successive readings does not change too much. The required accuracy is given by
<math display="inline">Sum_i((x - x_i)^2 + (y - y_i)^2 + (z - z_i)^2 - (t - t_i)^2) < 10^{-6}</math>.
It is guaranteed that such solution exists. The coordinates <math display="inline">x</math>; <math display="inline">y</math>; <math display="inline">z</math> are in range [-10; 10], the time <math display="inline">t</math> is in range [-1000; 1000].
The number of readings is guaranteed not to exceed <math display="inline">10^5</math>.</li>
<li>You have to build a simulation software for a new chemical reactor. Your program is given a list of chemical reactions and initial concentrations of all components. You should output the concentrations after time <math display="inline">t</math>.
In first-order reactions, only one molecule is necessary for the reaction, and the reaction rate is proportional to the concentration of this reagent:
<math display="inline">A\xrightarrow{k_1} n_1B_1 + n_2B_2 + ... + n_IB_I</math>.
For this reaction, we can write down the following system of ODEs:
<math display="inline">d[A]/dt=-k_1[A]</math>
<math display="inline">d[B_i]/dt=n_ik_1[A]</math>, <math display="inline">i=1,...,I</math>.
Here, <math display="inline">[A]</math> is the concentration of molecule <math display="inline">A</math>, <math display="inline">[B_i]</math> is the concentration of <math display="inline">B_i</math> molecules, and <math display="inline">k_1</math> is the reaction rate constant.
In second order reactions, two molecules are necessary for the reaction to proceed:
<math display="inline">A+C\xrightarrow{k_2} n_1B_1 + n_2B_2 + ... + n_IB_I</math>.
<math display="inline">d[A]/dt=-k_2[A][C]</math>
<math display="inline">d[B_i]/dt=n_ik_2[A][C]</math>, <math display="inline">i=1,...,I</math>.</li>
<li>The simplest example of oscillating chemical system is the Oregonator <http://www.scholarpedia.org/article/Oregonator>, which consists of the following reactions:
<math display="inline">A+Y\xrightarrow{k_1}X+P</math>.
<math display="inline">X+Y\xrightarrow{k_2}2P</math>.
<math display="inline">A+X\xrightarrow{k_3}2X+2Z</math>.
<math display="inline">2X\xrightarrow{k_4}A+P</math>.
<math display="inline">B+Z\xrightarrow{k_5}Y</math>.
The reaction rates will always be within order of magnitude from their respective values in the example input file.
Input
The first line contains a single integer number <math display="inline">T</math> = 1...1000 – how long we will run our virtual reactor. The second line contains six floating-point values – the initial concentrations of <math display="inline">X</math>, <math display="inline">Y</math>, <math display="inline">Z</math>, <math display="inline">A</math>, <math display="inline">B</math> and <math display="inline">P</math>. The third line contains five floating-point values – the reaction rate constants <math display="inline">k_1,...,k_5</math>.
Output
The output should contains six floating-point values – the final concentrations of <math display="inline">X</math>, <math display="inline">Y</math>, <math display="inline">Z</math>, <math display="inline">A</math>, <math display="inline">B</math> and <math display="inline">P</math>. Required precision is <math display="inline">10^-6</math>.</li></ol>

### Exams and retake planning

#### Exam

Exams will be project-based and will be conducted in a form of problem solving, where the problems will be similar to those mentioned above. Students will be given 1-2 weeks to complete the exam.

#### Retake 1

First retake will be paper-based and will be conducted in a form of problem solving. Students will be given 2-3 hours to complete the exam.The weight of the retake exam will be the same as the all course.

#### Retake 2

Second retake will be paper-based and will be conducted in a form of problem solving. Students will be given 2-3 hours to complete the exam.The weight of the retake exam will be the same as the all course.

# Citations

1. [BSc:NumericalModelling](https://eduwiki.innopolis.university/index.php/BSc%3ANumericalModelling), revision 77

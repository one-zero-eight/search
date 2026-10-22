---
type: course
title: "BSc: Probability And Statistics"
description: "A second-year BS course covering probability theory and mathematical statistics, including random variables, limit theorems, and statistical inference."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Probability_And_Statistics"
tags: ["probability", "statistics", "mathematics", "bs", "computer-science"]
aliases: ["BSc:ProbabilityAndStatistics"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Probability_And_Statistics"
    id: "6547"
    title: "BSc: Probability And Statistics"
    last_modified: "2022-04-26T12:55:59Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T09:33:25+00:00"
status: draft
review: table positions in the text could not be kept
stale_after: "2024-04-25T12:55:59+00:00"
prerequisite_of: ["/courses/bsc-capstone-project.md", "/courses/bsc-game-theory.md", "/courses/bsc-introduction-to-machine-learning.md", "/courses/bsc-natural-language-processing.md", "/courses/bsc-practical-machine-learning-deep-learning.md", "/courses/msc-advanced-statistics.md"]
taught_by: ["/people/sergeygorodetsky.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSc: Probability And Statistics

## Probability and Statistics

- **Course name:** Probability and Statistics
- **Course number:** XYZ
- **Knowledge area:** Math, Computational Science

### Administrative details

- **Faculty:** Computer Science and Engineering
- **Year of instruction:** 2nd year of BS
- **Semester of instruction:** 2nd semester
- **No. of Credits:** 4 ECTS
- **Total workload on average:** 144 hours overall
- **Class lecture hours:** 2 per week
- **Class tutorial hours:** 2 per week
- **Lab hours:** 2 per week
- **Individual lab hours:** 0
- **Frequency:** weekly throughout the semester
- **Grading mode:** letters: A, B, C, D

### Prerequisites

- [CSE201 — Mathematical Analysis I](/courses/bsc-mathematical-analysis-i.md)
- [CSE113 — Philosophy I - (Discrete Math and Logic)](/courses/bsc-logic-and-discrete-mathematics.md)

### Course outline

The course is designed to provide Software Engineers and Computer Scientists by correct knowledge of basic (core) concepts, definitions, theoretical results and applied methods & techniques of Probability Theory and Mathematical Statistics. The main idea of the course is to study mathematical basis of modelling random experiments. The course includes constructing a probability space, a model of a random experiment, and its applications to practice. After that, random variables and their properties are considered. As examples of applying this theoretical background, limit theorems of probability theory are proved (law of large numbers, central limit theorem) and some elements of mathematical statistics are studied.

### Expected learning outcomes

- Probability and sample (probability) spaces
- Discrete and continuous distribution
- Mean and variance
- Multivariate discrete & continuous distributions
- Central limit theorem, law of large numbers
- Linear regression and correlation

### Expected acquired core competences

- Basic (core) concepts, definitions, theoretical results and applied methods & techniques of Probability Theory and Mathematical Statistics

### Reference material

### Required computer resources

Any electronic spreadsheet (Excel for example) that provides data sorting and graph & chart drawing.

### Course Characteristics

#### Key concepts of the class

- Probability space & probability basics
- Random variables and their characteristics
- Limit theorems
- Introduction into mathematical statistics

#### What is the purpose of this course?

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to:

- construct a mathematical model of a random experiment (probability space)
- calculate conditional probabilities
- use probability generating functions for discrete random variables
- find confidence intervals for parameters of a normal distribution
- estimate unknown parameters of distributions

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to understand:

- probability function and its properties
- law of total probability and Bayes’ theorem
- independence of events and of random variables
- different continuous distributions
- multivariate distributions for discrete and continuous cases
- maximum likelihood estimator method

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to ...

- find expected value, variance and other characteristics of a random variable
- apply limit theorems (law of large numbers and central limit theorem)
- find parameters of a simple linear regression

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Weekly tests | ? | 25 |
| Midterm | ? | 25 |
| Final exam | ? | 50 |

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 | 85-100 |
| B. Good | 75-89 | 70-84 |
| C. Satisfactory | 60-74 | 50-69 |
| D. Poor | 0-59 | 0-49 |

#### Resources and reference material

** Textbook **

- Durrett Rick. (2019) Probability. Theory and Examples,
- Suhov Y, Kelbert M (2005) Probability and Statistics by Example, Cambridge University Press

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Basics of Probability | 12 |
| 2 | Univariate Distributions | 24 |
| 3 | Multivariate distributions | 24 |
| 4 | Limit theorems &amp; Introduction into Mathematical Statistics | 30 |
| hline |  |  |

#### Section 1

##### Section title:

Basics of Probability

#### Topics covered in this section:

- Probability space. <math display="inline">\sigma</math>-algebra of events. Axiomatic definition of probability
- Classical model of probability
- Independence of events
- Conditional probability
- Probability of a sum of events (of a product of events)
- Law of total probability. Bayes theorem.

#### What forms of evaluation were used to test students’ performance in this section?

|a|c|

& **Yes/No**

Development of individual parts of software product code & 0

Homework and group projects & 1

Midterm evaluation & 1

Testing (written or computer based) & 1

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 0

#### Typical questions for ongoing performance evaluation within this section

1. Give an example of three events that are pairwise independent, but not mutually independent.
1. Can disjoint events be independent?
1. A six-sided die is rolled. Construct an algebra of events for this random experiment.
1. Derive the formula for calculating the probability of a sum <math display="inline">P(A+B+C)</math>.

#### Typical questions for seminar classes (labs) within this section

1. Each game of a match between two equal players can end with a victory of one of them with probability <math display="inline">0{.}5</math> independently of the other games. Each victory yields one point, and the match is played until one of the players scores 6 points. Due to technical reasons the match was interrupted when the score was <math display="inline">5:3</math> in favour of the first player. What do you think is a fair way to distribute the prize between the players?
1. Seventy numbers are chosen at random from integers <math display="inline">1,2,3,\cdot,100</math>. What is the probability that the largest number chosen is <math display="inline">98</math>?
1. A hospital specialises in curing three types of diseases: <math display="inline">A</math>, <math display="inline">B</math> and <math display="inline">C</math>. On average, there are <math display="inline">50\%</math> of patients who suffer from disease <math display="inline">A</math>, <math display="inline">30\%</math> of patients with disease <math display="inline">B</math>, and <math display="inline">20\%</math> of patients with disease <math display="inline">C</math> (each of the patients has exactly one of these diseases). The probabilities to fully recover from the diseases are equal to <math display="inline">0{.}95</math>, <math display="inline">0{.}9</math> and <math display="inline">0{.}85</math> respectively. A patient who came to the hospital recovered completely. What is the probability that he had disease <math display="inline">B</math>?
1. A white ball is added into an urn that initially contained <math display="inline">n</math> balls. It is known that the probabilities of having <math display="inline">0,1,2,\ldots n</math> white balls (at the start) in the urn are equal to each other. (a) One ball is taken at random from the urn. What is the probability that the ball is white? (b) The ball taken from the urn has turned out to be white. Find the most probable number of white balls that were in the urn from the start.

#### Test questions for final assessment in this section

1. The probabilities for three students to pass the exam are equal to <math display="inline">\frac{11}{12}</math>, <math display="inline">\frac{11}{14}</math> and <math display="inline">\frac{18}{25}</math> respectively. Determine the probability that at least one student passes the exam given that they pass or fail independently of each other.
1. One of 10-digit numbers in which digits go in non-increasing order is chosen at random. Find the probability that exactly 4 different digits are used in this number.
1. Two persons play a game. They take turns in rolling a 10-sided fair die. The first one wins as soon as he rolls 9 or 10, whereas the second one wins as soon as he gets no more than 4. (The game goes on until one of the player’s winning conditions is met). Determine the probability for the first player to win the game.
1. Two dice are rolled simultaneously. What is the probability that the sum is even given that it is a multiple of 3?
1. There are 5 white balls and 7 green balls in the first urn; 2 white balls and 10 green balls in the second urn. The third urn, that has initially been empty, is filled with the balls: 4 balls are taken from the first urn, 6 balls are taken from the second urn, and they are placed into the third urn. After that, 2 balls are taken at random from the third urn. It turns out that both these balls are green. Determine the probability that these balls originate from different urns.

#### Section 2

##### Section title:

Univariate Distributions

#### Topics covered in this section:

1. Let <math display="inline">\mathbf{X}</math> be a random vector with mean <math display="inline">\boldsymbol{\mu}</math> and covariance matrix <math display="inline">\boldsymbol{\Sigma}</math>. Find the expected value and covariance matrix of <math display="inline">\mathbf{Y} = \mathbf{A}\mathbf{X} + \mathbf{b}</math>, where <math display="inline">\mathbf{A}</math> is a constant matrix and <math display="inline">\mathbf{b}</math> is a constant vector.
2. Let <math display="inline">X_1, X_2, \ldots, X_n</math> be independent random variables, each uniformly distributed on <math display="inline">(0, 1)</math>. Find the probability density function of the sum <math display="inline">S_n = X_1 + X_2 + \ldots + X_n</math>.
3. Let <math display="inline">(X, Y)</math> be a random vector uniformly distributed on the unit disk <math display="inline">x^2 + y^2 \leq 1</math>. Find the marginal density functions of <math display="inline">X</math> and <math display="inline">Y</math>, and determine if <math display="inline">X</math> and <math display="inline">Y</math> are independent.
4. Let <math display="inline">X</math> and <math display="inline">Y</math> be independent exponential random variables with parameters <math display="inline">\lambda_1</math> and <math display="inline">\lambda_2</math> respectively. Find the distribution of <math display="inline">Z = \min(X, Y)</math>.
5. Let <math display="inline">X</math> and <math display="inline">Y</math> be jointly normal random variables with means <math display="inline">\mu_X, \mu_Y</math>, variances <math display="inline">\sigma_X^2, \sigma_Y^2</math>, and correlation coefficient <math display="inline">\rho</math>. Find the conditional distribution of <math display="inline">Y</math> given <math display="inline">X = x</math>.

#### Section 1

##### Section title:

Limit Theorems and Introduction into Mathematical Statistics

#### Topics covered in this section:

- Chebyshev’s inequality. Law of large numbers
- Central limit theorem
- Estimating unknown distribution parameters
- Simple linear regression

#### What forms of evaluation were used to test students’ performance in this section?



#### Typical questions for ongoing performance evaluation within this section

1. Is it possible that for some random variable an equality is reached in Chebyshev’s inequality?
1. Give an example of a sequence of random variables that satisfies the law of large numbers, and another sequence that does not satisfy it.
1. What is a maximum likelihood estimator? Calculate maximum likelihood estimators for parameters of a normally distributed sample.
1. Are least square estimators of parameters of a linear regression unbiased? Are they consistent?

#### Typical questions for seminar classes (labs) within this section

1. Let <math display="inline">\xi_n\sim\begin{pmatrix}-\sqrt n & 0 & \sqrt n\\ 1/2n & 1-1/n & 1/2n\end{pmatrix}</math>. Does this sequence comply the law of large numbers?
1. Let <math display="inline">\xi_n\sim\begin{pmatrix}- n & 0 &  n\\ 2^{-n} & 1-2^{-n+1} & 2^{-n}\end{pmatrix}</math>. Does this sequence comply the law of large numbers?
1. Find a maximum likelihood estimator for a parameter of a sample with Poisson distribution.
1. Prove that sample variance is a biased estimator of variance for a sample of independent identically distributed random variables. Show that Bessel’s correction makes it an unbiased estimator.
1. Provide an example of an unbiased estimator that does not have the least mean square error possible.

#### Test questions for final assessment in this section

1. The probabilities for three students to pass the exam are equal to <math display="inline">\frac{11}{12}</math>, <math display="inline">\frac{11}{14}</math> and <math display="inline">\frac{18}{25}</math> respectively. Determine the probability that at least one student passes the exam given that they pass or fail independently of each other.
1. Let us consider independent identically distributed random variables with uniform distribution on <math display="inline">(\theta;\theta+3)</math>. Find the maximum likelihood estimator of <math display="inline">\theta</math>. Which one of these estimators is unbiased? Justify your answer.
1. Find the smallest possible value of <math display="inline">P\bigl(|\xi-E\xi|\leq3\sqrt{Var \xi}\bigr)</math>.
1. The probability that a new-born baby is a boy is equal to <math display="inline">0{.}52</math>. Find the interval which contains the quantity of boys out of <math display="inline">10\,000</math> newborn babies with probability <math display="inline">0{.}98</math>.
1. Prove that for multivariate normal distribution uncorrelatedness implies independence.
1. Use characteristic functions to show that a sum of independent (and not necessarily identically distributed) random variables also has normal distribution.

## Tables

| <math display="inline">\eta\backslash \xi</math> | <math display="inline">-1</math> | 0 | 1 |
| --- | --- | --- | --- |
| <math display="inline">-2</math> | <math display="inline">\frac{\mathstrut3}{\mathstrut17}</math> | <math display="inline">\frac4{17}</math> | <math display="inline">\frac1{17}</math> |
| 2 | <math display="inline">\frac{\mathstrut1}{\mathstrut17}</math> | <math display="inline">\frac5{17}</math> | <math display="inline">\frac3{17}</math> |

<!-- catix:relations -->
## Relations

- Required for: [BSc: Capstone Project](/courses/bsc-capstone-project.md), [BSc: Game Theory](/courses/bsc-game-theory.md), [Introduction To Machine Learning](/courses/bsc-introduction-to-machine-learning.md), [BSc: Natural Language Processing](/courses/bsc-natural-language-processing.md), [Practical Machine Learning and Deep Learning](/courses/bsc-practical-machine-learning-deep-learning.md), [Advanced Statistics](/courses/msc-advanced-statistics.md)
- Taught by: [Sergey Gorodetsky](/people/sergeygorodetsky.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Probability And Statistics](https://eduwiki.innopolis.university/index.php/BSc%3A_Probability_And_Statistics), revision 6547

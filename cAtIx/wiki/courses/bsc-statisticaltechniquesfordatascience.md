---
type: course
title: "Statistical Techniques for Data Science"
description: "A BSc course covering non-standard statistics, including hypothesis testing, resampling, simulation methods, and time series analysis."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3AStatisticalTechniquesForDataScience"
tags: ["statistics", "data-science", "machine-learning", "simulation", "hypothesis-testing"]
aliases: ["BSc:StatisticalTechniquesForDataScience.S21"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3AStatisticalTechniquesForDataScience"
    id: "4959"
    title: "BSc:StatisticalTechniquesForDataScience"
    last_modified: "2022-04-04T19:58:51Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T02:11:12+00:00"
status: draft
stale_after: "2024-04-03T19:58:51+00:00"
prerequisite_of: ["/courses/bsc-capstone-project.md"]
taught_by: ["/people/vladimirivanov.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Statistical Techniques for Data Science

## Statistical Techniques for Data Science

- **Course name:** Statistical Techniques for Data Science
- **Course number:** BS-STDS

### Course characteristics

#### Key concepts of the class

- Statistical Hypothesis Testing
- Resampling
- Statistical ML
- MCMC

#### What is the purpose of this course?

The course covers non-standard statistics, applicable in a wide set of contexts, including non-parametric statistics, simulation methods, and time series analysis.

This course will provide an opportunity for participants to learn: random variables, elementary probability, and distributions; relevant probabilistic inequalities; random vectors, marginal and joint distributions; sequences of random variables and concepts of convergences; Markov chains; processes in continuous time; univariate and multivariate simulation methods; non-parametric and parametric resampling methods.

#### Course Objectives Based on Bloom’s Taxonomy

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to recognize and define

- Estimation methods: point estimates, MLE
- Confidence interval, p-value
- Estimation and Non-parametric Tests. Kolmogorov-Smirnov Test
- Sampling. Metropolis-Hastings. Markov Chains. MCMC

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to describe and explain (with examples)

- Describe the Statistical Hypothesis Testing, p-value, Power of a test and Sample size
- Explain ANOVA, Chi-square tests
- Smoothing methods with examples

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to apply

- Apply Non-parametric Tests, such as KS-test
- Apply resampling methods (jackknife, bootstrap)
- Apply Markov chain Monte-Carlo methods

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 20 | 40 |
| Interim performance assessment | 30 | 30 |
| Exams | 50 | 30 |

If necessary, please indicate freely your course’s features in terms of students’ performance assessment: None

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 | 80-100 |
| B. Good | 75-89 | 65-79 |
| C. Satisfactory | 60-74 | 50-64 |
| D. Poor | 0-59 | 0-49 |

If necessary, please indicate freely your course’s grading features: The semester starts with the default range as proposed in the Table 1, but it may change slightly (usually reduced) depending on how the semester progresses.

#### Resources and reference material

- Murphy K.P. Machine Learning: A Probabilistic Perspective. Massachusetts Institute of Technology, 2012. — 1067 p.
- Bishop Christopher. Pattern Recognition and Machine Learning. Springer, 2006. — 738 p.
- M. Ross. Introduction to Statistics. Prentice Hall. 1989
- Efron, R. J. Tibshirani. An introduction to the bootstrap. Springer. 1993
- G. Casella, R. L. Berger. Statistical Inference. Thomson Press. 2006
- S. Hojsgaard, D. Edwards, S. Lauritzen. Graphical Models with R. Springer. 2012
- Hastie, T. Tibshirani, R. and Friedman, J. (2008) The Elements of Statistical Learning 2ed. Springer
- Steven M. Kay. Fundamentals of Statistical Signal Processing: Estimation Theory (v. 1). Prentice Hall. 1993

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Parametric Statistics | 42 |
| 2 | Non-parametric Statistics | 24 |
| 3 | Sampling and Simulation | 24 |

#### Section 1

#### Section title:

Parametric Statistics

#### Topics covered in this section:

- Review of Probability Theory. Random variables. Density. Distributions. Expected value
- Exploring the Data Distributions. Multivariate distributions. Plots
- Data and Sampling Distributions. Standard error. CLT
- Experiment Design. Confidence intervals. Introduction to Hypotheses Testing
- A/B Testing, T-test, ANOVA, Chi-square.

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| --- | --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 1 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

#### Typical questions for ongoing performance evaluation within this section

1. What is the Central Limit Theorem?
1. What is statistic?
1. What is sampling distribution?
1. What is standard error?
1. What are Type I and Type II errors?
1. What is t-statistic error? T-test?

#### Typical questions for seminar classes (labs) within this section

1. Create a bi-modal dataset, which has the mean less than the median, draw a histogram.
1. Poisson Distribution in practice: seaching patterns of palindromes in DNA.
1. Experiments and A/B testing.
1. A researcher claims that Democrats will win the next election. 4300 voters were polled; 2200 said they would vote Democrat. Decide if you should support or reject null hypothesis. Is there enough evidence at *alpha* = 0.05 to support this claim?

#### Test questions for final assessment in this section

1. Prove Chebyshov inequality
1. Prove Markov inequality
1. What is ANOVA, what is the difference with Chi-square test?

#### Section 2

#### Section title:

Non-parametric Statistics

#### Topics covered in this section:

- Empirical CDF. Resampling. Jackknife and Bootstrap
- Density Estimation
- Estimation and Non-parametric Tests. KS Test
- Non-parametric Tests. Kruskal-Wallis Test. Multi-arm Bandits

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| --- | --- | --- |
| Development of individual parts of software product code | 0 |
| Homework and group projects | 0 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 0 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

#### Typical questions for ongoing performance evaluation within this section

1. What is Empirical CDF?
1. How to apply resampling? Jackknife and Bootstrap?
1. What is Kernel Density Estimation?
1. What is Smoothing?

#### Typical questions for seminar classes (labs) within this section

1. Implement Kernel Density Estimation.
1. Apply KS-test.
1. Apply Kruskal-Wallis Test
1. Implement Multi-arm Bandits

#### Test questions for final assessment in this section

1. What is epsilon-greedy algorithm?
1. Perform 1 sample KS test in Python and Scipy. Compare KS test to visual approaches for checking normality assumptions
1. Plot CDF and ECDF to visualize parametric and empirical cumulative distribution functions

#### Section 3

#### Section title:

Sampling and Simulation

#### Topics covered in this section:

- Sampling. Metropolis-Hastings.
- Rejection Sampling. Gibbs Sampling
- Thompson Sampling. Upper confidence bound
- Markov Chains. MCMC
- Time Series: Tools and Applications

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| --- | --- | --- |
| Development of individual parts of software product code | 0 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 0 |
| Reports | 0 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

#### Typical questions for ongoing performance evaluation within this section

1. What is Thompson Sampling?
1. What Upper confidence bound algorithm?
1. What is stationary distribution?

#### Typical questions for seminar classes (labs) within this section

1. Given density function, implement Accept-Reject sampling
1. Run Metropolis Hastings and Accept-Reject (on the same f(x)) (n=1000, 10000, 100000). Compare results
1. Apply Gibbs Sampling
1. Apply tools for time series analysis and prediction

#### Test questions for final assessment in this section

1. Consider a transition matrix of a Markov Chain (MC).
  - Show that this is a regular MC (A MC is called regular if for some integer n all entries of transition matrix after n steps are strictly positive).
  - Find the limiting probability vector w
1. Compare Gibbs Sampling to Metropolis Hastings.

<!-- catix:relations -->
## Relations

- Required for: [BSc: Capstone Project](/courses/bsc-capstone-project.md)
- Taught by: [Vladimir Ivanov](/people/vladimirivanov.md)
<!-- /catix:relations -->

# Citations

1. [BSc:StatisticalTechniquesForDataScience](https://eduwiki.innopolis.university/index.php/BSc%3AStatisticalTechniquesForDataScience), revision 4959

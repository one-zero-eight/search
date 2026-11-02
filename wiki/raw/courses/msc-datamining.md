---
type: course
title: "Data Mining (346)"
description: "A project-based course on Data Mining methods applied to Financial Trading, covering data processing, market micro-structure, and machine learning integration."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3ADataMining"
tags: ["data-mining", "finance", "machine-learning", "algorithmic-trading", "course"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3ADataMining"
    id: "129"
    title: "MSc:DataMining"
    last_modified: "2021-07-30T11:26:12Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:31:40+00:00"
status: draft
stale_after: "2023-07-30T11:26:12+00:00"
---

# Data Mining (346)

## Data Mining

- **Course name:** Data Mining
- **Course number:** 346

### Course Characteristics

#### Key concepts of the class

- The role, subject, problems and methods of Data Mining in the context of other Data Science and Data Engineering disciplines and activities.
- Data Mining in Finance, in particular in Algorithmic Financial Trading: in-depth study of problems and methods.

#### What is the purpose of this course?

The main purpose of this course is two-fold:

- to provide the students with a general understanding of the role of Data Mining which is closely connected to, but not identical to, Data Acquisition on one side, and Big Data Analysis / Machine Learning on the other side;
- to provide the students with a hands-on experience in application of Data Mining methods and techniques in a real-life modern area such as Financial Industry (more specifically, Algorithmic Financial Trading).

.

#### Course objectives based on Bloom’s taxonomy

1. Understand the role, subject, problems and methods of Data Mining in relation to other Data Science and Data Engineering disciplines, such as Data Acquisition and Big Data Analysis / Machine Learning.
1. Define and understand the key concepts of Data Science for Finance: Financial Assets, Instruments, Markets and Trading, Exchanges, Prices, Volumes.
1. Define and understand the key concepts of Financial Markets micro-structure: Orders, Order Books, Bids, Asks, Matching Engines, Trades.
1. Understand the principal problems and solution methods of Data Mining with application to Financial Trading:
  - construction of Order Books and Trades from Order Logs or incremental updates;
  - data cleaning (e.g. resolving Bid-Ask collisions, wrong trade sizes, stale orders);
  - construction of descriptive statistics for Order Books and Trades;
  - feature generation for subsequent Data Analysis (e.g. WVAPs, Volumes, Market Pressure etc).
1. Develop hands-on experience with complex, industrial-strength Data Mining processes related to Financial Trading data.
1. Understand and apply the classical and modern methods of statistical data analysis, such as Principal Component Analysis (PCA) and Independent Component Analysis (ICA).
1. Understand the methods of feature generation for Machine Learning methods.
1. Understand and apply patterns of Machine Learning methods to analyze financial trading data.

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to:

- Know the differences between Data Mining and Data Acquisition (on one hand) and Big Data Analysis (on the other hand).
- Know the principal definitions and terminology related to Financial Trading data.
- Know the importance of data clearing / pre-processing in Data Mining in general and for Financial Trading data in particular.
- Know that Machine Learning methods of data analysis cannot be used effectively without proper data pre-processing and feature engineering.
- Know the relationship between Statistical and Machine Learning-based methods of data analysis.

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to:

- Understand the mechanisms of exchange-based financial trading.
- Understand the micro-structure of financial markets (orders, order books, matching, trades etc).
- Understand the methods of constructing Order Book and Trades data from the raw data in Finance.
- Understand the typical errors which occur in Financial Trading data, and the methods for their detection and correction.
- Understand the modern methods of statistical analysis of financial time series data, in particular, the method of ICA and its advantages over PCA.
- Understand the methods of feature generation for analysis of Financial Trading data using Machine Learning methods.
- Understand how the statistical and machine learning-based methods of data analysis can efficiently be integrated to achieve the best results.

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to:

- Develop sufficiently complex, “industrial-strength” software solutions (e.g. in Python) for processing raw Financial Trading data into Order Books and Trades, providing:
  - adequate temporal and spatial efficiency;
  - necessary logic for data clean-up and resolution of data errors / inconsistencies.
- Judiciously select and apply the appropriate Machine Learning methods for analysis of Financial Trading data and prediction of financial time series.

#### Course evaluation

The course is largely project-based, thus higher weights are assigned to Labs; Final Project Presentation is provided in place of a Final Exam:

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs | 20 | 40 |
| Interim performance assessment | 30 | 20 |
| Final Project Presentation | 50 | 40 |

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 | 85–100 |
| B. Good | 75-89 | 70–84 |
| C. Satisfactory | 60-74 | 50–69 |
| D. Poor | 0-59 |  |

#### Resources and reference material

- M. Kolanovich, *Big Data and AI Strategies*, JP Morgan, 2017.
- K. Kim, *Electronic and Algorithmic Trading Technology: The Complete Guide*, Elsevier, 2007.
- M. Durbin, *All About High-Frequency Trading*, McGrow-Hill, 2010.
- I. Aldridge, *High-Frequency Trading*, Wiley, 2010.

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Introduction into Data Mining | 2 |
| 2 | Data Mining and Data Analysis in Financial Trading | 4 |
| 3 | Micro-Structure of Financial Markets | 16 |
| 4 | Feature Engineering for Machine Learning in Financial Trading | 4 |
| 5 | Descriptive Statistics of Financial Trading Data | 4 |
| 6 | Principal and Independent Component Analysis (PCA and ICA) | 8 |
| 7 | Machine Learning Methods for Prediction of Financial Data | 16 |

#### Section 1

##### Section title:

Introduction into Data Mining

#### Topics covered in this section:

- The subject, problems and methods of Data Mining. Data Mining as a Data Engineering discipline.
- Relationships between Data Mining, Data Acquisition, Big Data Analysis and Machine Learning.
- A typical data processing workflow.

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 0

Homework and group projects &amp; 0

Midterm evaluation &amp; 1

Testing (written or computer based) &amp; 0

Reports &amp; 0

Essays &amp; 0

Oral polls &amp; 1

Discussions &amp; 1

#### Typical questions for ongoing performance evaluation within this section

1. Is Data Mining a science or an engineering discipline?
1. Explain a typical data processing workflow from Acquisition to Analysis and the role of Data Mining in this process.
1. What are the main problems and methods of Data Mining?
1. How is Data Mining related to Data Analysis and Machine Learning?

#### Typical questions for seminar classes (labs) within this section

None

#### Test questions for final assessment in this section

1. Explain the main methods of detecting data outliers and gaps.
1. Do you concur with the statement that Machine Learning algorithms are in general capable of discerning arbitrarily-complex relationships in data, provided that the training dataset is large enough?
1. Explain how Data Mining can be used to facilitate efficient Machine Learning.

#### Section 2

##### Section title:

Data Mining and Data Analysis in Financial Trading

#### Topics covered in this section:

- Financial Asset Classes: Equities, Currencies, Commodities, Interest Rate Products and others.
- Financial Instruments, Trading and Exchanges.
- Stochastic dynamics of prices and trading volumes of financial instruments. The notion of stochastic differential equations. Trends and Volatilities.
- The nomenclature of professional specializations in Quantitative Finance related to data science and data engineering: Quantitative Analysts, Quantitative Researchers, Quantitative Developers, Research Analysis. Their relationship to Data Mining.

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 0

Homework and group projects &amp; 0

Midterm evaluation &amp; 1

Testing (written or computer based) &amp; 0

Reports &amp; 0

Essays &amp; 0

Oral polls &amp; 1

Discussions &amp; 1

#### Typical questions for ongoing performance evaluation within this section

1. What are Equities as a financial asset class?
1. Explain the difference between the QA and QR professional specializations.
1. Which of professional specializations in quantitative finance is mostly concerned with Data Mining?

#### Typical questions for seminar classes (labs) within this section

None

#### Test questions for final assessment in this section

1. Explain the components of stochastic dynamics of financial assets (HINT: Trends and Volatilities).
1. Provide two definitions of the Trend, and explain how they are related to each other.
1. What are the main differences between stochastic dynamics of Equity and IRP prices? In the price prediction problem, where would the role of data science be more important?
1. Explain the differences between QA and QR specializations regarding the subject of their research.

#### Section 3

##### Section title:

Micro-Structure of Financial Markets

##### Topics covered in this section:

- The “mechanics” of Exchange-based trading in financial instruments.

- Explain the problem of predicting financial time series in Algorithmic Trading.
- Explain the importance of feature engineering over the “best non-linear method” selection.
- Explain the danger of over-fitting and the methods of controlling it.

1. Explain the differences between Reinforcement Learning and Supervised Learning.
1. Explain why careful feature engineering is so important in Machine Learning in general, and for predicting financial time series in particular.
1. Explain the objectives and potential time horizons of price prediction in Algorithmic Trading.

##### Typical questions for seminar classes (labs) within this section

PROJECT WORK: Based on the solutions implemented in Sections 3–6, implement an price prediction methods for USD/RUB instruments at MOEX:

1. apply the features constructed in Section 4;
1. apply an explicit linear regression with Lasso regularization;
1. then construct an ANN and compare the quality of predictions.

##### Test questions for final assessment in this section

1. What is over-fitting in ML and how can it be controlled?
1. Explain the similarities and differences between SVMs and ANNs.
1. Describe in detail the API of Machine Learning library you have been using in your Lab Project.

# Citations

1. [MSc:DataMining](https://eduwiki.innopolis.university/index.php/MSc%3ADataMining), revision 129

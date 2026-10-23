---
type: course
title: "BSc: Information Retrieval"
description: "Course CSE306 covering practical and theoretical aspects of information search, recommender systems, indexing, ranking, and multimedia retrieval."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Information_Retrieval"
tags: ["information-retrieval", "recommender-systems", "data-science", "cse306", "indexing"]
aliases: ["BSc:InformationRetrieval"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Information_Retrieval"
    id: "8534"
    title: "BSc: Information Retrieval"
    last_modified: "2023-09-16T09:46:17Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:19:56+00:00"
status: draft
stale_after: "2025-09-15T09:46:17+00:00"
prerequisites: [{"course": "/courses/bsc-analytic-geometry-and-linear-algebra-ii.md", "as_written": "CSE204 — Analytic Geometry And Linear Algebra II: matrix multiplication, matrix decomposition (SVD, ALS) and approximation (matrix norm), sparse matrix, stability of solution (decomposition), vector spaces, metric spaces, manifold, eigenvector and eigenvalue."}, {"as_written": "CSE113 — Philosophy I - (Discrete Math and Logic): graphs, trees, binary trees, balanced trees, metric (proximity) graphs, diameter, clique, path, shortest path."}, {"as_written": "CSE206 — Probability And Statistics: probability, likelihood, conditional probability, Bayesian rule, stochastic matrix and properties. Analysis: DFT, [discrete] gradient."}]
taught_by: ["/people/stanislavprotasov.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSc: Information Retrieval

## Information Retrieval
- **Course name**: Information Retrieval
- **Code discipline**: CSE306
- **Subject area**: Data Science; Computer systems organization; Information systems; Real-time systems; Information retrieval; World Wide Web; Recommender systems

### Short Description
The course gives an introduction to practical and theoretical aspects of information search and recommender systems.
This course covers the following concepts: Indexing; Search quality assessment; Relevance; Ranking; Information retrieval; Query; Recommendations; Multimedia retrieval.

### Prerequisites

#### Prerequisite subjects
- CSE204 — Analytic Geometry And Linear Algebra II: matrix multiplication, matrix decomposition (SVD, ALS) and approximation (matrix norm), sparse matrix, stability of solution (decomposition), vector spaces, metric spaces, manifold, eigenvector and eigenvalue.
- CSE113 — Philosophy I - (Discrete Math and Logic): graphs, trees, binary trees, balanced trees, metric (proximity) graphs, diameter, clique, path, shortest path.
- CSE206 — Probability And Statistics: probability, likelihood, conditional probability, Bayesian rule, stochastic matrix and properties. Analysis: DFT, [discrete] gradient.

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Information retrieval basics | # Introduction to IR, major concepts. <br> # Crawling and Web. <br> # Quality assessment. |
| Text processing and indexing | # Building inverted index for text documents. Boolean retrieval model. <br> # Language, tokenization, stemming, searching, scoring. <br> # Spellchecking and wildcard search. <br> # Suggest and query expansion. <br> # Language modelling. Topic modelling. |
| Vector model and vector indexing | # Vector model <br> # Machine learning for vector embedding <br> # Vector-based index structures |
| Advanced topics. Media processing | # Image and video processing, understanding and indexing <br> # Content-based image retrieval <br> # Audio retrieval <br> # Relevance feedback |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The course is designed to prepare students to understand background theories of information retrieval systems and introduce different information retrieval systems. The course will focus on the evaluation and analysis of such systems as well as how they are implemented. Throughout the course, students will be involved in discussions, readings, and assignments to experience real world systems. The technologies and algorithms covered in this class include machine learning, data mining, natural language processing, data indexing, and so on.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Terms and definitions used in area of information retrieval,
- Search engine and recommender system essential parts,
- Quality metrics of information retrieval systems,
- Contemporary approaches to semantic data analysis,
- Indexing strategies.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Understand background theories behind information retrieval systems,
- How to design a recommender system from scratch,
- How to evaluate quality of a particular information retrieval system,
- Core ideas and system implementation and maintenance,
- How to identify and fix information retrieval system problems.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Build a recommender service from scratch,
- Implement a proper index for an unstructured dataset,
- Plan quality measures for a new recommender service,
- Run initial data analysis and problem evaluation for a business task, related to information retrieval. 
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
| Assignments | 60 |
| Quizzes | 40 |
| Exams | 0 |

#### Recommendations for students on how to succeed in the course

The simples way to succeed is to participate in labs and pass coding assignments in timely manner. This guarantees up to 60% of the grade. Participation in lecture quizzes allow to differentiate the grade.

### Resources, literature and reference materials

#### Open access resources
- Manning, Raghavan, Schütze, An Introduction to Information Retrieval, 2008, Cambridge University Press
- Baeza-Yates, Ribeiro-Neto, Modern Information Retrieval, 2011, Addison-Wesley
- Buttcher, Clarke, Cormack, Information Retrieval: Implementing and Evaluating Search Engines, 2010, MIT Press
- [Course repository in github](https://github.com/IUCVLab/information-retrieval).

#### Closed access resources


#### Software and tools used within the course

## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 |
| --- | --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 1 | 1 | 1 |
| Homework and group projects | 1 | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Enumerate limitations for web crawling. | 1 |
| Question | Propose a strategy for A/B testing. | 1 |
| Question | Propose recommender quality metric. | 1 |
| Question | Implement DCG metric. | 1 |
| Question | Discuss relevance metric. | 1 |
| Question | Crawl website with respect to robots.txt. | 1 |
| Question | What is typical IR system architecture? | 0 |
| Question | Show how to parse a dynamic web page. | 0 |
| Question | Provide a framework to accept/reject A/B testing results. | 0 |
| Question | Compute DCG for an example query for random search engine. | 0 |
| Question | Implement a metric for a recommender system. | 0 |
| Question | Implement pFound. | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Build inverted index for a text. | 1 |
| Question | Tokenize a text. | 1 |
| Question | Implement simple spellchecker. | 1 |
| Question | Implement wildcard search. | 1 |
| Question | Build inverted index for a set of web pages. | 0 |
| Question | build a distribution of stems/lexemes for a text. | 0 |
| Question | Choose and implement case-insensitive index for a given text collection. | 0 |
| Question | Choose and implement semantic vector-based index for a given text collection. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Embed the text with an ML model. | 1 |
| Question | Build term-document matrix. | 1 |
| Question | Build semantic index for a dataset using Annoy. | 1 |
| Question | Build kd-tree index for a given dataset. | 1 |
| Question | Why kd-trees work badly in 100-dimensional environment? | 1 |
| Question | What is the difference between metric space and vector space? | 1 |
| Question | Choose and implement persistent index for a given text collection. | 0 |
| Question | Visualize a dataset for text classification. | 0 |
| Question | Build (H)NSW index for a dataset. | 0 |
| Question | Compare HNSW to Annoy index. | 0 |
| Question | What are metric space index structures you know? | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Extract semantic information from images. | 1 |
| Question | Build an image hash. | 1 |
| Question | Build a spectral representation of a song. | 1 |
| Question | Whats is relevance feedback? | 1 |
| Question | Build a "search by color" feature. | 0 |
| Question | Extract scenes from video. | 0 |
| Question | Write a voice-controlled search. | 0 |
| Question | Semantic search within unlabelled image dataset. | 0 |
#### Final assessment
**Section 1**
1. Implement text crawler for a news site.
1. What is SBS (side-by-side) and how is it used in search engines?
1. Compare pFound with CTR and with DCG.
1. Explain how A/B testing works.
1. Describe PageRank algorithm.
**Section 2**
1. Explain how (and why) KD-trees work.
1. What are weak places of inverted index?
1. Compare different text vectorization approaches.
1. Compare tolerant retrieval to spellchecking.
**Section 3**
1. Compare inverted index to HNSW in terms of speed, memory consumption?
1. Choose the best index for a given dataset.
1. Implement range search in KD-tree.
**Section 4**
1. What are the approaches to image understanding?
1. How to cluster a video into scenes and shots?
1. How speech-to-text technology works?
1. How to build audio fingerprints?

#### The retake exam
**Section 1**
1. Solve a complex coding problem similar to one of the homework or lab.
**Section 2**
1. Solve a complex coding problem similar to one of the homework or lab.
**Section 3**
1. Solve a complex coding problem similar to one of the homework or lab.
**Section 4**
1. Solve a complex coding problem similar to one of the homework or lab.

<!-- catix:relations -->
## Relations

- Prerequisites: [BSc: Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md) (CSE204 — Analytic Geometry And Linear Algebra II: matrix multiplication, matrix decomposition (SVD, ALS) and approximation (matrix norm), sparse matrix, stability of solution (decomposition), vector spaces, metric spaces, manifold, eigenvector and eigenvalue.); CSE113 — Philosophy I - (Discrete Math and Logic): graphs, trees, binary trees, balanced trees, metric (proximity) graphs, diameter, clique, path, shortest path.; CSE206 — Probability And Statistics: probability, likelihood, conditional probability, Bayesian rule, stochastic matrix and properties. Analysis: DFT, [discrete] gradient.
- Taught by: [Stanislav Protasov](/people/stanislavprotasov.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Information Retrieval](https://eduwiki.innopolis.university/index.php/BSc%3A_Information_Retrieval), revision 8534

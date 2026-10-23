---
type: course
title: "Information Theory"
description: "A course introducing Information Theory, covering coding, transmission, compression, entropy, and channel capacity with practical implementation labs."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3AInformationTheory"
tags: ["information-theory", "course", "coding", "entropy", "compression"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3AInformationTheory"
    id: "46"
    title: "BSc:InformationTheory"
    last_modified: "2021-07-30T10:33:45Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T09:39:58+00:00"
status: draft
stale_after: "2023-07-30T10:33:45+00:00"
duplicate_of: ["/courses/bsc-informationtheory-986.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Information Theory

## Information Theory

- **Course name:** Information Theory
- **Course number:** N/A

### Course Characteristics

#### Key concepts of the class

- Information coding
- Information transmission

#### What is the purpose of this course?

This course provides a basic introduction to the Information Theory and its applications to digital systems. In particular, it focuses on the theoretical and practical aspects that are connected to the data compression and transmission highlighting the different problems and approaches to overcome the limitations. Moreover, a short introduction about the mathematical requirements will focuses on the probability and basic statistical concepts that will be used throughout the course.

#### Course objectives based on Bloom’s taxonomy

#### - What should a student remember at the end of the course?

- Information definitions.
- Entropy definitions.
- Encoding techniques.
- Transmission techniques.
- Compression techniques.

#### - What should a student be able to understand at the end of the course?

- How random variables and signals are connected.
- The concept of information and how it is connected to entropy.
- The different types of transmission channels.
- How encoding works.
- How compression works.

#### - What should a student be able to apply at the end of the course?

- Implement a compression algorithm.
- Select the most suitable channel for transmission.
- Identify and correct errors in data exchanges.

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 20 |  |
| Interim performance assessment | 30 |  |
| Exams | 50 |  |

If necessary, please indicate freely your course’s features in terms of students’ performance assessment.

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 |  |
| B. Good | 75-89 |  |
| C. Satisfactory | 60-74 |  |
| D. Poor | 0-59 |  |

If necessary, please indicate freely your course’s grading features.

#### Resources and reference material

- Slides and material provided during the course.
- Videos recorded during the lectures.
- MacKay, D.J.C. Information Theory, Inference, and Learning Algorithms. Cambridge University Press, 2003. Available for free at: https://www.inference.org.uk/itprnn/book.pdf
- Raymond W. Yeung. A First Course in Information Theory. Springer, 2006. ISBN-10: 1408813068. Available for free at: http://iest2.ie.cuhk.edu.hk/~whyeung/post/draft7.pdf
- Robert M. Gray. Entropy and Information Theory. Springer, 2011. ISBN-13: 978-1-4419-7969-8. Available for free at: https://ee.stanford.edu/~gray/it.pdf
- Stefan M. Moser. Information Theory - Lecture Notes. Available for free at: http://moser-isi.ethz.ch/scripts.html

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Introduction | 2 |
| 2 | Probability and Information | 4 |
| 3 | Information and Entropy | 4 |
| 4 | Encoding | 6 |
| 5 | Channels | 6 |
| 6 | Compression | 6 |
| 7 | Errors | 2 |

#### Section 1

##### Section title:

Introduction

#### Topics covered in this section:

- Definition of information
- Communication systems
- Uncertainty
- Shannon paper

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| & **Yes/No**

Development of individual parts of software product code & 0

Homework and group projects & 0

Midterm evaluation & 1

Testing (written or computer based) & 0

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 0

#### Typical questions for ongoing performance evaluation within this section

1. Describe the components of a communication system
1. How is it possible to measure information?
1. Definition of uncertainty
1. What is information?

#### Typical questions for seminar classes (labs) within this section

1. Design the structure of a communication system
1. Possible ways to measure the information of a message
1. Make an example on how information and uncertainty is related
1. Analyze the Shannon’s paper

#### Test questions for final assessment in this section

1. Shennon’s definition of information
1. Definition of uncertainty and its relation with information.
1. Describe the different ways of measuring information

#### Section 2

##### Section title:

Probability and Information

#### Topics covered in this section:

- Discrete probability
- Random variables
- Bayes’ theorem
- Naive Bayesian Classifier

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| & **Yes/No**

Development of individual parts of software product code & 0

Homework and group projects & 0

Midterm evaluation & 1

Testing (written or computer based) & 0

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 0

#### Typical questions for ongoing performance evaluation within this section

1. Define simple, joint, marginal, and conditional probability
1. Define an ergodic process
1. Describe the implications of the Bayes’ theorem
1. What is a classifier?

#### Typical questions for seminar classes (labs) within this section

1. Draw the possibility tree for a certain set of events
1. Given a process, check if it is ergodic
1. Write the code for the implementation of a Naive Bayesian Classifier
1. Write the code to test the ergodicity of a process

#### Test questions for final assessment in this section

1. Describe the relationships among the different kinds of probabilities.
1. Compare the characteristics of different distributions and how they relate to real problems.
1. Make examples of the application of the Bayes’ theorem in real-life problems.

#### Section 3

##### Section title:

Information and Entropy

##### Topics covered in this section:

- Entropy
- Relative entropy
- Mutual information
- Jensen’s inequality
- Gibbs’ inequality

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| & **Yes/No**

Development of individual parts of software product code & 0

Homework and group projects & 0

Midterm evaluation & 1

Testing (written or computer based) & 0

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 0

#### Typical questions for ongoing performance evaluation within this section

1. Describe the entropy properties
1. Define joint and conditional entropy
1. Describe the Jensen’s inequality
1. Describe the Gibbs’ inequality

##### Typical questions for seminar classes (labs) within this section

1. Calculate the entropy in different conditions
1. Calculate relative entropy in different conditions
1. Calculate mutual information in different conditions
1. Applications of convex functions

##### Test questions for final assessment in this section

1. Calculate the entropy of a message.
1. Describe the relationship between relative entropy and mutual information.
1. Compare the entropy of the same message sent using different encodings.

#### Section 4

##### Section title:

Encoding

##### Topics covered in this section:

- Source coding theorem
- Huffman coding
- Arithmetic coding

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| & **Yes/No**

Development of individual parts of software product code & 1

Homework and group projects & 0

Midterm evaluation & 1

Testing (written or computer based) & 0

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 0

#### Typical questions for ongoing performance evaluation within this section

1. Describe the source coding theorem
1. Describe Huffman coding
1. Describe arithmetic coding
1. Compare different coding techniques

##### Typical questions for seminar classes (labs) within this section

1. Write a piece of code that implement the Huffman encoding
1. Write a piece of code that implement the arithmetic encoding
1. Write a piece of code that implement the Huffman decoding
1. Write a piece of code that implement the arithmetic decoding

##### Test questions for final assessment in this section

1. How the performances of the Huffman coding change based on the changes of the size of the dictionary.
1. Describe advantages and disadvantages of coding techniques based on dictionaries.
1. Describe advantages and disadvantages of coding techniques not based on dictionaries

#### Section 5

##### Section title:

Channels

##### Topics covered in this section:

- Types and characteristics of channels
- Noise
- Capacity
- Schedules

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| & **Yes/No**

Development of individual parts of software product code & 0

Homework and group projects & 0

Midterm evaluation & 1

Testing (written or computer based) & 0

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 0

#### Typical questions for ongoing performance evaluation within this section

1. Compare different channel types.
1. How is it possible to communicate over a noisy channel?
1. Make examples of different channel types.
1. What is the capacity of a channel?

##### Typical questions for seminar classes (labs) within this section

1. Calculate the capacity of a channel.
1. How the capacity changes based on the type of channel?

1. Send the same message through different channel types with no noise. Which are the differences?
1. Send the same message through different channel types with noise. Which are the differences?

##### Test questions for final assessment in this section

1. What is the effect of the noise in the different channel types?
1. What is the relation between codes and channels?
1. Calculate the entropy of a message before and after a channel.

#### Section 6

##### Section title:

Compression

##### Topics covered in this section:

- Lempel-Ziv coding
- Block codes
- Lossy compression

#### What forms of evaluation were used to test students’ performance in this section?



#### Typical questions for ongoing performance evaluation within this section

1. Differences between stream and block coding algorithms
1. Principles of lossy compression
1. Describe Lempel-Ziv coding
1. Examples of block codes

##### Typical questions for seminar classes (labs) within this section

1. Write a piece of code that implement the Lempel-Ziv coding
1. Write a piece of code that implement a lossy compression algorithm
1. Write a piece of code for a block code
1. Write a piece of code for a stream code

##### Test questions for final assessment in this section

1. Compare Huffman coding and Lempel-Ziv coding
1. Analyse the different versions of the Lempel-Ziv coding
1. Given a message, calculate the Huffman code.

#### Section 7

##### Section title:

Errors

##### Topics covered in this section:

- Error detection techniques
- Error correction techniques
- Hamming code

#### What forms of evaluation were used to test students’ performance in this section?



#### Typical questions for ongoing performance evaluation within this section

1. Describe the error detection techniques
1. Describe the error correction techniques
1. Describe the Hamming code
1. Describe the parity detection techniques

##### Typical questions for seminar classes (labs) within this section

1. Write a piece of code that implements the Hamming code
1. Calculate the Hamming code of a data sequence
1. Given a message extract the Hamming code
1. Given a message check its correctness using the Hamming code

##### Test questions for final assessment in this section

1. Compare the requirements for the detection and correction of errors using the Hamming code
1. Compare the requirements for detecting and correcting errors
1. Given a message with an error and using the Hamming code, calculate the correct message

<!-- catix:relations -->
## Relations

- Duplicate of (the page edited last): [Теория информации](/courses/bsc-informationtheory-986.md)
<!-- /catix:relations -->

# Citations

1. [BSc:InformationTheory](https://eduwiki.innopolis.university/index.php/BSc%3AInformationTheory), revision 46

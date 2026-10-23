---
type: course
title: "Fundamentals of Computer Security"
description: "An introductory course covering basic security concepts, encryption techniques, and network security principles, including symmetric and asymmetric cryptography."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3APrincipelsOfComputerSecurity"
tags: ["computer-security", "cryptography", "encryption", "network-security", "course"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3APrincipelsOfComputerSecurity"
    id: "86"
    title: "BSc:PrincipelsOfComputerSecurity"
    last_modified: "2021-07-30T10:53:29Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:46:32+00:00"
status: draft
stale_after: "2023-07-30T10:53:29+00:00"
---

# Fundamentals of Computer Security

## Fundamentals of Computer Security

- **Course name:** Fundamentals of Computer Security
- **Course number:**

### Course characteristics

#### Key concepts of the class

- Basic security concepts
- Encryption techniques

#### What is the purpose of this course?

This is an introductory course in computer security. During the course, students will learn the fundamental principles and techniques that constitute the basis for the modern computer security. The aim is to provide a practical knowledge of both the principles and practice of cryptography and network security. Practical applications that have been implemented and are in use to provide network security will be introduced in the final part of this course.

#### Course Objectives Based on Bloom’s Taxonomy

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to recognize and define

- Different security demands
- Basic Encryption techniques
- Symmetric encryption
- Asymmetrical encryption
- Message authentication algorithms
- Digital signature technique

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to describe and explain (with examples)

- Difference between security and cryptography
- Difference between stream cipher and block cipher
- Concept of DES and AES
- Symmetrical encryption
- Asymmetrical encryption
- Cryptographic hash function
- Difference between message authentication and Digital signature

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to apply

- How to encrypt and decrypt messages using different methods
- How to use Hash functions for cryptography
- Different brute force attacks

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 20 | 30 |
| Interim performance assessment | 30 | 10 |
| Exams | 50 | 60 |

If necessary, please indicate freely your course’s features in terms of students’ performance assessment: None

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 |  |
| B. Good | 75-89 |  |
| C. Satisfactory | 60-74 |  |
| D. Poor | 0-59 |  |

If necessary, please indicate freely your course’s grading features: The semester starts with the default range as proposed in the Table [tab:MLCourseGradingRange], but it may change slightly (usually reduced) depending on how the semester progresses.

#### Resources and reference material

- William Stallings, *Cryptography and Network Security: Principles and Practice, 6th Edition.*
- Bruce Schneier, *Applied Cryptography, Second Edition: Protocols, Algorthms, and Source Code in C (cloth).*

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Classical Encryption Techniques | 8 |
| 2 | Symmetric encryption | 12 |
| 3 | Asymmetric encryption | 12 |
| 4 | Cryptographic hash functions | 8 |

#### Section 1

#### Section title:

Classical Encryption Techniques

#### Topics covered in this section:

- Present an overview of the main concepts of symmetric cryptography
- Explain the difference between cryptanalysis and brute-force attack
- The operation of a monoalphabetic substitution cipher
- The operation of a polyalphabetic cipher.
- The Hill cipher

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| :--- | :--- | :--- |
| Development of individual parts of software product code | 0 | |
| Homework and group projects | 1 | |
| Midterm evaluation | 1 | |
| Testing (written or computer based) | 1 | |
| Reports | 0 | |
| Essays | 0 | |
| Oral polls | 0 | |
| Discussions | 1 | |

#### Typical questions for ongoing performance evaluation within this section

1. How many keys are required for two people to communicate via a cipher?
2. What is the difference between a block cipher and a stream cipher?
3. List and briefly define types of cryptanalytic attacks based on what is known to the attacker.
4. Briefly define the monoalphabetic cipher.
5. What is the difference between a monoalphabetic cipher and a polyalphabetic cipher?

#### Typical questions for seminar classes (labs) within this section

1. Using the two keys (memory words) cryptographic and network security, encrypt the following message.
2. Decrypt the ciphertext. Show your work.
3. Construct a Playfair matrix with the key largest.
4. Write a program that can encrypt and decrypt using the general Caesar cipher, also known as an additive cipher.
5. We have shown that the Hill cipher succumbs to a known plaintext attack if sufficient plaintext–ciphertext pairs are provided. It is even easier to solve the Hill cipher if a chosen plaintext attack can be mounted. Describe such an attack.

#### Test questions for final assessment in this section

1. What substitution system results when we use a 25 * 1 Playfair matrix?
2. Using the Vigenere cipher, encrypt the word “explanation” using the key leg.
3. How many one-to-one affine Caesar ciphers are there?
4. What is the difference between an unconditionally secure cipher and a computationally secure cipher?

#### Section 2

#### Section title:

Symmetric encryption

#### Topics covered in this section:

- Present an overview of the Feistel cipher and explain how decryption is the inverse of encryption
- Present an overview of Data Encryption Standard (DES)
- Discuss the cryptographic strength of DES
- Present an overview of the general structure of Advanced Encryption Standard (AES)
- Understand the four transformations used in AES

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| :--- | :--- | :--- |
| Development of individual parts of software product code | 1 | |
| Homework and group projects | 1 | |
| Midterm evaluation | 1 | |
| Testing (written or computer based) | 1 | |
| Reports | 0 | |
| Essays | 0 | |
| Oral polls | 0 | |
| Discussions | 1 | |

#### Typical questions for ongoing performance evaluation within this section

1. What is the difference between the AES decryption algorithm and the equivalent inverse cipher?
2. How is the S-box constructed?
3. Briefly describe AddRoundKey.
4. What is the difference between ShiftRows and RotWord?

#### Typical questions for seminar classes (labs) within this section

1. Create software that can encrypt and decrypt using S-AES. Test data: A binary plaintext of 0110 1111 0110 1011 encrypted with a binary key of 1010 0111 0011 1011 should give a binary ciphertext of 0000 0111 0011 1000. Decryption should work correspondingly.
2. Implement a differential cryptanalysis attack on 1-round S-AES.
3. Given the plaintext 000102030405060708090A0B0C0D0E0F and the key 01010101010101010101010101010101
4. Show the first eight words of the key expansion for a 128-bit key of all zeros.

#### Test questions for final assessment in this section

1. Compare AES to DES. For each of the following elements of DES, indicate the com- parable element in AES or explain why it is not needed in AES.
2. What was the final set of criteria used by NIST to evaluate candidate AES ciphers?
3. Verify the entry for 01 in the S-box.

#### Section 3

#### Section title:

Asymmetric encryption

#### Topics covered in this section:

- An overview of the basic principles of public-key cryptosystems
- An overview of the RSA algorithm.
- Requirements for a public-key cryptosystem.
- The two distinct uses of public-key cryptosystems.

#### What forms of evaluation were used to test students’ performance in this section?

| a | c | **Yes/No** |
| :--- | :--- | :--- |
| Development of individual parts of software product code | 1 | |
| Homework and group projects | 1 | |
| Midterm evaluation | 1 | |
| Testing (written or computer based) | 1 | |
| Reports | 0 | |
| Essays | 0 | |
| Oral polls | 0 | |
| Discussions | 1 | |

#### Typical questions for ongoing performance evaluation within this section

1. What are the principal elements of a public-key cryptosystem?
2. What are the roles of the public and private key?
3. Whaat is single-linkage and what are its pros and cons?
4. In an RSA system, the public key of a given user is e = 31, n = 3599. What is the pri- vate key of this user? Hint: First use trial-and-error to determine p and q; then use the extended Euclidean algorithm to find the multiplicative inverse of 31 modulo f(n).

#### Typical questions for seminar classes (labs) within this section

1. In a public-key system using RSA, you intercept the ciphertext C = 10 sent to a user whose public key is e = 5, n = 35. What is the plaintext M?
2. Suppose we have a set of blocks encoded with the RSA algorithm and we don’t have the private key. Assume n = pq, e is the public key. Suppose also someone tells us they know one of the plaintext blocks has a common factor with n. Does this help us in any way?

#### Test questions for final assessment in this section

1. In the RSA public-key encryption scheme, each user has a public key, e, and a private key, d. Suppose Bob leaks his private key. Rather than generating a new modulus, he decides to generate a new public and a new private key. Is this safe?
2. In using the RSA algorithm, if a small number of repeated encodings give back the plaintext, what is the likely cause?

1. Suppose we have a set of blocks encoded with the RSA algorithm and we don’t have the private key. Assume n = pq, e is the public key. Suppose also someone tells us they know one of the plaintext blocks has a common factor with n. Does this help us in any way?

#### Section 4

#### Section title:

Cryptographic hash functions

#### Topics covered in this section:

- A hash function used for message authentication.
- The differences among preimage resistant, second preimage resistant, andcollision resistant properties.
- An overview of the basic structure of cryptographic hash functions.
- SHA-512.

#### What forms of evaluation were used to test students’ performance in this section?



|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 1

Homework and group projects &amp; 1

Midterm evaluation &amp; 1

Testing (written or computer based) &amp; 1

Reports &amp; 0

Essays &amp; 0

Oral polls &amp; 0

Discussions &amp; 1





#### Typical questions for ongoing performance evaluation within this section

1. What characteristics are needed in a secure hash function?
1. What is the difference between weak and strong collision resistance?
1. What is the role of a compression function in a hash function?
1. It is possible to use a hash function to construct a block cipher with a structure similar to DES. Because a hash function is one way and a block cipher must be reversible (to decrypt), how is it possible?

#### Typical questions for seminar classes (labs) within this section

1. Suppose H(m) is a collision-resistant hash function that maps a message of arbitrary bit length into an n-bit hash value. Is it true that, for all messages x, x’ with x <math display="inline">\neq</math> x’, we have H(x) <math display="inline">\neq</math> H(x’) Explain your answer.
1. For SHA-512, show the equations for the values of W16, W17, W18, and W19.

#### Test questions for final assessment in this section

1. This problem introduces a hash function similar in spirit to SHA that operates on let- ters instead of binary data. It is called the toy tetragraph hash (tth).6 Given a message consisting of a sequence of letters, tth produces a hash value consisting of four letters. First, tth divides the message into blocks of 16 letters, ignoring spaces, punctuation, and capitalization. If the message length is not divisible by 16, it is padded out with nulls. A four-number running total is maintained that starts out with the value (0, 0, 0, 0); this is input to the compression function for processing the first block. The com- pression function consists of two rounds.
1. Consider the SHA-3 option with a block size of 1024 bits and assume that each of the lanes in the first message block (P0) has at least one nonzero bit. To start, all of the lanes in the internal state matrix that correspond to the capacity portion of the initial state are all zeros. Show how long it will take before all of these lanes have at least one nonzero bit. Note: Ignore the permutation. That is, keep track of the original zero lanes even after they have changed position in the matrix.

# Citations

1. [BSc:PrincipelsOfComputerSecurity](https://eduwiki.innopolis.university/index.php/BSc%3APrincipelsOfComputerSecurity), revision 86

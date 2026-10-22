---
type: course
title: "Security of Systems and Networks"
description: "Course SNE-08 covering network security, applied cryptography, security protocols, and their real-world applications through theory and projects."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3ASecuritySystemsNetworks"
tags: ["security", "cryptography", "networks", "course", "ssn"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3ASecuritySystemsNetworks"
    id: "6584"
    title: "MSc:SecuritySystemsNetworks"
    last_modified: "2022-04-26T14:24:05Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T09:24:10+00:00"
status: draft
stale_after: "2024-04-25T14:24:05+00:00"
prerequisite_of: ["/courses/msc-advanced-security.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Security of Systems and Networks

## Security of Systems and Networks

- **Course name:** Security of Systems and Networks (SSN)
- **Course number:** SNE-08

### Course characteristics

#### Key concepts of the class

- Network security
- Applied cryptography
- Security protocols
- Internet security

#### What is the purpose of this course?

This course will cover the fundamentals of security, security protocols, and their applications in real-world. The topics covered in this course include applied cryptography, authentication, passwords, practical security, social aspects of security, SSL/TLS, email security, PKI, and IPSec. Furthermore, this course will strengthen the security knowledge of the students and guide them in the right direction for their upcoming research projects and advanced courses. The course is divided into two parts. The first part will cover the theory and hands-on practice of the concepts taught at class. And the second part of the course will focus on the course projects. The student will work on a security project by using the concepts taught in the class.

### Course Objectives Based on Bloom’s Taxonomy

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to recognize and define

- Different aspects of system and network security
- Analyze the formation of publicly available symmetric and asymmetric algorithms
- Mathematically analyze the RSA and other related algorithms
- Authentication protocols
- Various key management protocols
- Different symmetric and asymmetric ciphers
- Security at different TCP/IP layers
- Secure UEFI booting
- Nuts and bolts of quantum cryptography

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to:

- Demonstrate the acquired knowledge and skills in applied cryptography (symmetric and asymmetric cryptography),
- Operate classical enigma machine, encode and decode messages with it
- Demonstrate the working knowledge of famous cryptographic algorithms and discuss their shortcomings
- Demonstrate and operate the already implemented security protocols over internet,
- Reason about the problems in the security of networked systems and current internet and their existing solutions,
- Solve mathematical problems (especially in number theory),
- And Demonstrate the knowledge and discuss basic quantum cryptography concepts.

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to apply

- Crypt-analyze ciphertext and decrypt through frequency analysis and other important techniques
- Design security protocols
- Find security flaws in security protocols
- Get hands-on experience of the existing enterprise cryptographic algorithms and use them in projects,
- Demonstrate the skill of finding out security issues in networked systems and internet technologies,

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 35 | 35 |
| Project | 35 | 35 |
| Exams | 30 | 30 |

If necessary, please indicate freely your course’s features in terms of students’ performance assessment: None

#### Grades range



**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 |  |
| B. Good | 75-89 |  |
| C. Satisfactory | 60-74 |  |
| D. Poor | 0-59 |  |



If necessary, please indicate freely your course’s grading features: The semester starts with the default range as proposed in the Table 1, but it may change slightly (usually reduced) depending on how the semester progresses.

#### Resources and reference material

- Lecture material
- RFCs
- Information Security by Mark Stamp

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Classical and modern cryptography | 8 |
| 2 | Authentication and Kerberos | 8 |
| 3 | SSL, TLS, and IPSec | 10 |
| 4 | Covert channels and pattern matching-based network security (IDS/IPS) | 6 |
| 5 | Quantum cryptography | 2 |
| 6 | Labs | 56 |

#### Section 1

#### Section title:

Classical and modern cryptography

#### Topics covered in this section:

- Classical cryptography
- Enigma
- Different substitution and transposition ciphers
- Stream and block ciphers
- Data Encryption Standard (DES)
- Advanced Encryption Standard (AES)
- Diffie-Hellman key exchange
- Crypto math
- RSA
- Elliptic curve cryptography

#### What forms of evaluation were used to test students’ performance in this section?



|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 0

Homework and group projects &amp; 1

Midterm evaluation &amp; 0

Testing (written or computer based) &amp; 1

Reports &amp; 1

Essays &amp; 0

Oral polls &amp; 0

Discussions &amp; 1





#### Typical questions for ongoing performance evaluation within this section

1. How do different protocols work?
1. What are the differences in stream and block ciphers from performance standpoint?
1. How to measure the security of cryptographic algorithms?
1. How to encrypt and decrypt with different asymmetric crypto algorithms?
1. How to embedd backdoors in crypto algorithms?
1. How to realize key exchange through diffie-hellman using traditional techniques and elliptic curve techniques?
1. How to make security algorithms efficient?

#### Typical questions for seminar classes (labs) within this section

1. Make enigma machine with pringle box
1. Assess the security of different setups of RSA
1. Implement man in the middle attack
1. Implement addition over elliptic curves
1. Solve crypto math problems

#### Test questions for final assessment in this section

1. As above

#### Section 2

#### Section title:

Authentication

#### Topics covered in this section:

- Kerberos
- Passwords
- Biometrics
- Authentication and key agreement protocols
- Rainbow tables
- Protocol development

#### What forms of evaluation were used to test students’ performance in this section?



|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 0

Homework and group projects &amp; 1

Midterm evaluation &amp; 0

Testing (written or computer based) &amp; 1

Reports &amp; 1

Essays &amp; 0

Oral polls &amp; 0

Discussions &amp; 1





#### Typical questions for ongoing performance evaluation within this section

1. What are pros and cons of using symmetric and asymmetric cryptographic mechanisms for authentication?
1. What is man in the middle attack?
1. Develop home-grown authentication mechanisms?
1. How Kerberos reduces the communication overhead?
1. Where is shibboleth used?

#### Typical questions for seminar classes (labs) within this section

1. Implement different variants of authentication protocols
1. Find out security flaws in authentication protocols
1. Identify shortcomings of different protocols

#### Test questions for final assessment in this section

1. As above

#### Section 3

#### Section title:

SSL, TLS, and IPSec

#### Topics covered in this section:

- SSL, TLS
- IPSec

#### What forms of evaluation were used to test students’ performance in this section?



|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 0

Homework and group projects &amp; 1

Midterm evaluation &amp; 0

Testing (written or computer based) &amp; 1

Reports &amp; 1

Essays &amp; 0

Oral polls &amp; 0

Discussions &amp; 1





#### Typical questions for ongoing performance evaluation within this section

1. How does SSL and TLS work?
1. HOw does SSL and TLS combine symmetric and asymmetric cryptography?
1. Why IPSec is so over-engineered? and what are the security flaws?
1. What are different components of IPSec

#### Typical questions for seminar classes (labs) within this section

1. Implement IPSec
1. Assess the security of SSL and TLS handshakes

#### Test questions for final assessment in this section

1. As above

#### Section 4

#### Section title:

Covert channels and pattern-matching based networks security

#### Topics covered in this section:

- Secure UEFI booting
- Pattern matching-based network security with focus on IDS and IPS
- Covering different existing tools such as Yara, Snort, Suricata, and Bro for rules definition and deployment
- Covert channels and their role in different layers
- Existing techniques in implementing covert channels

#### What forms of evaluation were used to test students’ performance in this section?



|a|c| &amp; **Yes/No**

Development of individual parts of software product code &amp; 0

Homework and group projects &amp; 1

Midterm evaluation &amp; 0

Testing (written or computer based) &amp; 1

Reports &amp; 1

Essays &amp; 0

Oral polls &amp; 0

Discussions &amp; 1





#### Typical questions for ongoing performance evaluation within this section

1. How does IDS and IPS work in a network setup, which configuration is used and which layers do they work?
1. How does the rule set work in different tools such as Suricata, Snort, Bro, and Yara?
1. How to create a covert channel and different layers of network protocol stack?
1. Which layer is ideal for creating a covert channel?
1. What are the current state of the art regarding covert channel in different layers?

#### Test questions for final assessment in this section

1. As above

#### Section 5

#### Section title:

Quantum cryptography

#### Topics covered in this section:

- Superposition of photons

- Quantum Key Distribution (QKD)
- Eavesdropper in quantum setup

#### What forms of evaluation were used to test students’ performance in this section?



#### Typical questions for ongoing performance evaluation within this section

1. How is eavesdropper kept at bay from eavesdropping on a quantum channel?
1. What are the advantages of quantum channel over traditional communication channel?

#### Test questions for final assessment in this section

1. As above

<!-- catix:relations -->
## Relations

- Required for: [Advanced Security](/courses/msc-advanced-security.md)
<!-- /catix:relations -->

# Citations

1. [MSc:SecuritySystemsNetworks](https://eduwiki.innopolis.university/index.php/MSc%3ASecuritySystemsNetworks), revision 6584

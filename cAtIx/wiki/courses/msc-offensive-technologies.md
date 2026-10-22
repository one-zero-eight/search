---
type: course
title: "MSc: Offensive Technologies"
description: "Course covering software security, malware analysis, mobile security, and network/web security, including vulnerabilities, fuzzing, and penetration testing techniques."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Offensive_Technologies"
tags: ["offensive-technologies", "security", "malware", "fuzzing", "penetration-testing"]
aliases: ["MSc:Offensive Technologies"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Offensive_Technologies"
    id: "7475"
    title: "MSc: Offensive Technologies"
    last_modified: "2022-08-29T08:57:26Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:38:26+00:00"
status: draft
stale_after: "2024-08-28T08:57:26+00:00"
prerequisites: [{"as_written": "The course has been designed to be self-included as much as possible. The successful completion will depend on prerequisite courses such as:"}, {"course": "/courses/msc-advanced-security.md", "as_written": "CSE522 - Advanced Security"}, {"as_written": "Essential skills"}, {"course": "/courses/msc-classical-internet-applications.md", "as_written": "Classical Internet Applications", "via": "model"}]
taught_by: ["/people/saifmohammedsabri.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# MSc: Offensive Technologies

## Offensive Technologies
- **Course name**: Offensive Technologies
- **Code discipline**: ?
- **Subject area**: 

### Short Description
This course covers the following concepts: Software Security; Malware Analysis; Mobile Security; Network and Web Security.

### Prerequisites

#### Prerequisite subjects
- The course has been designed to be self-included as much as possible. The successful completion will depend on prerequisite courses such as:
- CSE522 - Advanced Security
- Essential skills
- Classical Internet Applications

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Software Security | # Buffer overflow vulnerability <br> # Format string vulnerability <br> # ASLR defensive technique <br> # NX defensive technique <br> # Fuzzing security testing |
| Malware Analysis | # Malware evasion techniques <br> # Malware injection techniques <br> # Malware artifacts <br> # Virtual Machine environment hardening <br> # Professional malware analysis frameworks and tools |
| Mobile Security | # Mobile architecture <br> # Mobile security testing <br> # Detection of mobile malware <br> # Professional mobile security testing frameworks and tools |
| Network and Web Security | # Injection Flows <br> # Cookies Flows <br> # Server Misconfiguration <br> # Network Misconfiguration |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
Offensive Technology introduces methods, tools, and techniques to the students to assess the security of different services, protocols, and applications. The course aims to expose the students to real-world expertise from a security perspective and let them find vulnerabilities in both software and hardware, Also in this course, the students will learn how to analyze a malicious application and how they can understand the behavior of this application and deploy the appropriate defenses against this application. Furthermore, the students will develop projects of their choice to show their skills. In this course, the students will particularly focus on Software Testing, Fuzzing, Malware Analysis, Mobile Security, and Network and Web Security.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Common weaknesses/vulnerabilities in web application
- ASLR, NX, and how are these techniques can help to protect against a malicious attacker
- Fuzzing techniques
- Malware C&C server
- Process injection techniques that are used in malware and how to defend against it
- Mobile security analysis

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Methods and techniques bypass memory mitigation techniques
- Methods and techniques for fuzz testing
- Methods and techniques malware analysis
- Methods and techniques for mobile security testing
- Methods and techniques web penetration testing

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Perform a network discovery
- Detect/exploit common weaknesses/vulnerabilities in web applications.
- Detect vulnerabilities in software.
- Writing an exploit to bypass ASLR and NX protection.
- Perform fuzzing for a specific use case.
- Perform security assessment for mobile application
- Perform security analysis for a malicious application 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 85-100 | - |
| B. Good | 70-84 | - |
| C. Satisfactory | 60-69 | - |
| D. Poor | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 50 |
| Project | 50 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Mike O’Leary, Cyber Operations, Second Edition, Apress, 2019
- Ric Messier, Penetration Testing Basics: A Quick-Start Guide to Breaking into Systems, Apress, 2016
- Michal Zalewsk, The Tangled Web, No Starch Press, 2011
- Jon Erickson, Hacking: The Art of Exploitation, 2nd Edition, No StarchPress, 2008
- The Fuzzing Bookhttps://www.fuzzingbook.org
- Wil Allsopp, Advanced Penetration Testing: Hacking the World’s most secure Networks, Wiley, 2017
- Dafydd Stuttard, The Web Application Hacker’s Handbook: Finding and exploiting Security Flaws, 2nd edition, Wiley, 2011
- Rafay Baloch, Ethical Hacking and Penetration Testing Guide, AuerbachPublications, 2014

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 |
| --- | --- | --- | --- | --- |
| Homework and group projects | 1 | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 |
| Reports | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are the pros and cons of using ASLR? does it affect the performance? | 1 |
| Question | What is the required information to be able to identify a remote libc version? | 1 |
| Question | What are the pros and cons of writing your own fuzzer? | 1 |
| Question | Write an exploit for a given binary, also try to bypass the mitigation techniques | 0 |
| Question | Implement a fuzzer for a specific use-case | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | For a given malicious application try to find useful artifacts, for example, find encryption key, C&C server, find commands that server can send | 1 |
| Question | while setup an isolated analytic Virtual Machine, What are the required steps for hardening? | 1 |
| Question | what are the most commonly used evasion and injection in malware and how can you detect it? | 1 |
| Question | For a given malicious application try to find the evasion and injection techniques that are used by that application | 0 |
| Question | For a given malicious application try to write detection rules to be able to defend against it | 0 |
| Question | Setup an isolated analytic Virtual Machine and test it against Virtual Machine detection tools | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What privilege does root or jailbreak gives you? is it mandatory for security testing? | 1 |
| Question | What is the difference from the security perspective between some version of an old mobile operation system | 1 |
| Question | what is the pros and cons of mobile security testing? | 1 |
| Question | For a given malicious application try to find the evasion and injection techniques that are used by that application | 0 |
| Question | Setup an automated mobile security testing solution and test a given application | 0 |
| Question | try to bypass some of the security mechanisms that are enabled either on the application or on the operating system level | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is the difference between boolean-based and time-based SQL injection? | 1 |
| Question | Can regex matching protect against Directory Traversal attack? | 1 |
| Question | Does the Same Origin Policy apply to the localStorage inside the browser? | 1 |
| Question | Vulnerability analysis and exploitation for a given web application | 0 |
| Question | Write and deploy WAF rules to mitigate a specific web attack | 0 |
#### Final assessment
**Section 1**
1. As above
**Section 2**
1. As above
**Section 3**
1. As above
**Section 4**
1. As above

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

<!-- catix:relations -->
## Relations

- Prerequisites: The course has been designed to be self-included as much as possible. The successful completion will depend on prerequisite courses such as:; [Advanced Security](/courses/msc-advanced-security.md) (CSE522 - Advanced Security); Essential skills; [Classical Internet Applications](/courses/msc-classical-internet-applications.md) (Classical Internet Applications, matched by the model)
- Taught by: [SaifMohammedsabri](/people/saifmohammedsabri.md)
<!-- /catix:relations -->

# Citations

1. [MSc: Offensive Technologies](https://eduwiki.innopolis.university/index.php/MSc%3A_Offensive_Technologies), revision 7475

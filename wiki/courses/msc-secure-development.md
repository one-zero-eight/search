---
type: course
title: "Secure development"
description: "Course covering security principles, threat modeling, secure coding, and architecture to build secure systems from design to operation."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Secure_Development"
tags: ["course", "security", "secure-development", "sdl", "software-engineering"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Secure_Development"
    id: "7550"
    title: "MSc: Secure Development"
    last_modified: "2022-09-12T06:30:34Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:59:29+00:00"
status: draft
stale_after: "2024-09-11T06:30:34+00:00"
prerequisites: [{"course": "/courses/mste-introduction-to-programming.md", "as_written": "CSE101: Introduction to Programming"}, {"course": "/courses/bsc-software-systems-design.md", "as_written": "CSE112: Software Systems Analysis and Design", "via": "model"}]
relations_by: "process:catix-wiki-graph/0.1"
---

# Secure development

## Secure development
- **Course name**: Secure development
- **Code discipline**: XXX
- **Subject area**: Security and Networks

### Short Description


### Prerequisites

#### Prerequisite subjects
- CSE101: Introduction to Programming
- CSE112: Software Systems Analysis and Design

#### Prerequisite topics
- Basic programming skills, C/C++ is recommended
- Software design or software architecture
- Basics of compilers

### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Basics of security | # Security and safety. Security and code quality. Maintainability and security. Why it is so hard to develop a secure system and what approaches may be applied? When it makes sense to drive system secure? |
| Security architecture | # NIST recommendations <br> # Security principles <br> # Theoretical security: access matrix and security models <br> # Secure by design |
| Secure coding | # Security on the code level <br> # SDL <br> # Main binary vulnerabilities and their mitigations |
| Secure operating | # Security monitoring <br> # DevSecOps <br> # Dealing with 3rd parties |
| Security assurance | # Pen testing <br> # Fuzzing <br> # Bug Bounty programs |
| Linux security | # Keep it all together and see how Linux kernel deals with that. <br> # SELinux <br> # GrSec patches <br> # Why Linux is not safety system |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The main purpose of this course is to give students a security vision from up to down, because the security principle of weakest link insist that the weakest part of the process/system would be the one to be attacked.  

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Remember main security principles
- List SDL stages
- Describe the difference between security and safety
- Explain basic binary vulnerabilities
- Specify the required security assurance
- Describe the key elements of SOC systems
- Explain why fuzzing is not the same as unit or integration testing

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Perform Threat Modeling
- Review code to find insecure patterns
- Deal with open source code securely
- Explain the value of bug bounty programme and find the right moment to start it

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Suggest hardenings and architecture drifts to achieve required level of s&s
- Propose process improvement in a cost-effective manner that would drastically improve the security and safety level. 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 80-100 | - |
| B. Good | 60-79 | - |
| C. Satisfactory | 40-59 | - |
| D. Fail | 0-39 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Assignment/Labs | 70 |
| Final quiz | 30 |

#### Recommendations for students on how to succeed in the course
Participation is important. Showing up is the key to success in this course.
If you don’t have a corresponding technical background, please do not hesitate to ask lecturer. If you feel that the gap is deep, request for extra reading.
Reading the recommended literature is optional, and will give you a deeper understanding of the material.

### Resources, literature and reference materials

#### Open access resources
- Owasp.com
- MITRE SOC Operations https://www.mitre.org/sites/default/files/publications/11-strategies-of-a-world-class-cybersecurity-operations-center.pdf
- MISRA, AUTOSAR, SEI CERT
- https://www.microsoft.com/en-us/securityengineering/sdl

#### Closed access resources
- Matt Bishop, (2018) “Computer Security: Art and Science”
- D Deougun, DB Jonhsson, D Sawano (2019) “Secure by design”
- D LeBlanc, Michael Howard (2002) “Writing secure code”

#### Software and tools used within the course
- Some static analyser
- AFL 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Teaching and Learning Methods within each section**

| Teaching Techniques | Section 1 | Section 2 | Section 3 | Section 4 | Section 5 | Section 6 |
| --- | --- | --- | --- | --- | --- | --- |
| Problem-based learning (students learn by solving open-ended problems without a strictly-defined solution) | 1 | 1 | 1 | 1 | 1 | 1 |
| Modular learning (facilitated self-study) | 1 | 1 | 1 | 1 | 1 | 1 |
| Differentiated learning (provide tasks and activities at several levels of difficulty to fit students needs and level) | 1 | 1 | 1 | 1 | 1 | 1 |
| Contextual learning (activities and tasks are connected to the real world to make it easier for students to relate to them); | 1 | 1 | 1 | 1 | 1 | 1 |
| Business game (learn by playing a game that incorporates the principles of the material covered within the course). | 1 | 1 | 1 | 1 | 1 | 1 |
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 | Section 5 | Section 6 |
| --- | --- | --- | --- | --- | --- | --- |
| Lectures | 1 | 1 | 1 | 1 | 1 | 1 |
| Lab exercises | 1 | 1 | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Individual Assignments | A2: Product Ideation and Market Research <br> Find all weakness in the code snippet. Suggest how to fix them in a secure way. What is your recommendation for the code author? | 1 |
##### Section 2

##### Section 3

##### Section 4

##### Section 5

##### Section 6

#### Final assessment
**Section 1**

**Section 2**

**Section 3**

**Section 4**

**Section 5**

**Section 6**


#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

**Section 5**

**Section 6**

<!-- catix:relations -->
## Relations

- Prerequisites: [MSTE: Introduction To Programming](/courses/mste-introduction-to-programming.md) (CSE101: Introduction to Programming); [Software Systems Design](/courses/bsc-software-systems-design.md) (CSE112: Software Systems Analysis and Design, matched by the model)
<!-- /catix:relations -->

# Citations

1. [MSc: Secure Development](https://eduwiki.innopolis.university/index.php/MSc%3A_Secure_Development), revision 7550

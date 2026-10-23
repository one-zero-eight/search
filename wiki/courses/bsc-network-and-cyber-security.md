---
type: course
title: "Network and Cyber Security"
description: "A course covering Information Security Management, Web Security, Software Security, and Network Security, focusing on secure system design and vulnerability exploitation."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Network_And_Cyber_Security"
tags: ["course", "security", "network", "cyber", "bsc"]
aliases: ["BSc:NetworkAndCyberSecurity"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Network_And_Cyber_Security"
    id: "7212"
    title: "BSc: Network And Cyber Security"
    last_modified: "2022-07-12T09:57:56Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:37:06+00:00"
status: draft
stale_after: "2024-07-11T09:57:56+00:00"
taught_by: ["/people/kirillsaltanov.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Network and Cyber Security

## Network and CyberSecurity
- **Course name**: Network and CyberSecurity
- **Code discipline**: ?
- **Subject area**: 

### Short Description
This course covers the following concepts: Information Security Management; Web Security; Software Security; Network security.

### Prerequisites

#### Prerequisite subjects


#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Information Security Management | # Security Policies and Controls <br> # Risks Analysis and Threats Modeling <br> # Software Development Security Techniques |
| Web Security | # Security-related web technologies <br> # Same Origin Policy <br> # Web Attacker Model <br> # OWASP methodology <br> # Injection Flaws <br> # Authorization Flaws <br> # Cookies Flaws <br> # Server Misconfiguration |
| Software Security | # Binary Exploitation <br> # ASLR <br> # NX |
| Network Security | # Networking tools <br> # Network attacks <br> # IDS/IPS |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
Security breaches cost billions of dollars worth of damage to the computing industry. Today, cybercriminals control armies consisting of several millions of compromised machines. Attacks are increasingly being perpetrated towards enterprises, individuals, critical infrastructure and even governments. At the same time, our computer systems and platforms are fast evolving to meet the demands of the industry. Increasing the use of personalized devices, and our growing dependence on legacy computer systems that weren’t designed with security in mind is a challenge ahead. Therefore, the purpose of this course is to cover the design and implementation of different IT systems from a security perspective. This course introduces to the field of systems security: that is, how to analyze and develop secure systems. The course covers fundamental concepts of systems design, low and high-level vulnerabilities exploitation, design, and implementation flaws in different types of applications based on the real-world scenarios.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Security policies and controls
- Risks and threats related to the system design and its implementation
- Software security testing methodologies
- Software development security techniques
- Injection and authorization flaws
- Cookies and misconfiguration flaws
- Common weaknesses/vulnerabilities in web applications
- Common weaknesses/vulnerabilities in the typical systems software

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Information security management methods
- Difference between different types of risks and threats
- Security-related web technologies
- The difference in the different web application flaws
- ASLR, NX and how are these techniques can help to protect against a malicious attacker
- Covert channels
- Networking tools
- Network proxies

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Critically audit systems and code for security flaws and threats
- Design and implement exploits for real security vulnerabilities
- Develop secure systems and applications
- Be able to design defense solutions and outline their limitations
- Be able to find misconfigurations/vulnerabilities in a given network/system 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 90-100 | - |
| B. Good | 70-89 | - |
| C. Satisfactory | 60-69 | - |
| D. Poor | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 30 |
| Project | 30 |
| Exams | 40 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Mike Chapple, James Michael Stewart, Darril Gibson, CISSP Official Study Guide, 8th Edition, Sybex, 2018
- Michal Zalewsk, The Tangled Web, No Starch Press, 2011
- Jon Erickson, Hacking: The Art of Exploitation, 2nd Edition, No Starch Press, 2008

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
| Development of individual parts of software product code | 0 | 1 | 0 | 0 |
| Midterm evaluation | 0 | 1 | 0 | 0 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What types of Security Policies are exist? | 1 |
| Question | What information from a given system you need to take into account to calculate security risks? | 1 |
| Question | Explain the difference between static and dynamic analysis of application code? | 1 |
| Question | Audit the given security policy for vulnerabilities and update it accordingly | 0 |
| Question | Calculate security risks for a given system and develop necessary security measures for mitigation | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is the difference between reflected XSS and stored XSS? which one is more critical and why? | 1 |
| Question | What are the pros and cons of using regex to protect against XSS? | 1 |
| Question | what is the Same Origin Policy? and which attack does it mitigate? | 1 |
| Question | What is the difference between boolean-based and time-based SQL injection? | 1 |
| Question | Vulnerability analysis and exploitation for a given web application | 0 |
| Question | Write and deploy WAF rules to mitigate a specific web attack | 0 |
| Question | Does the Same Origin Policy apply to the localStorage inside the browser? | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are the pros and cons of using ASLR? does it affect the performance? | 1 |
| Question | What can you do with a format string vulnerability? | 1 |
| Question | What is the required information to be able to identify a remote libc version? | 1 |
| Question | Why some binaries might have the same address for their functions? what is the security risk of this? | 1 |
| Question | Vulnerability analysis and exploitation for a given binary while ASLR is disabled | 0 |
| Question | Try to rewrite the following Assembly code in any programming language | 0 |
| Question | How can you check if you have ASLR, PIE, NX enabled or not? | 0 |
| Question | Decompilers are not always accurate why? how can you improve it? | 0 |
| Question | Some binaries are shipped with debugging symbols, How can this help you in debugging? | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is the difference between VPN and sock5? | 1 |
| Question | What are IDS, IPS, and DPI? | 1 |
| Question | Why does Nmap produce false-positive when scanning a windows host? can you improve the scanning technique? | 1 |
| Question | What is covert channel? what are the most common protocols that are used for covert channel? why? | 1 |
| Question | When using a proxy for HTTPS, your browser will always complain about the certificate, how can you solve this issue? | 1 |
| Question | No lab for this section | 0 |
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

- Taught by: [Kirill Saltanov](/people/kirillsaltanov.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Network And Cyber Security](https://eduwiki.innopolis.university/index.php/BSc%3A_Network_And_Cyber_Security), revision 7212

---
type: course
title: "Classical Internet Applications"
description: "Course SNE-03 covering Internet applications, TCP/IP stack, DNS, DNSSEC, email, and web services implementation and security."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Classical_Internet_Applications"
tags: ["course", "internet", "dns", "email", "security", "networking"]
aliases: ["MSc:Classical Internet Applications"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Classical_Internet_Applications"
    id: "7471"
    title: "MSc: Classical Internet Applications"
    last_modified: "2022-08-29T08:49:31Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:28:24+00:00"
status: draft
stale_after: "2024-08-28T08:49:31+00:00"
prerequisites: [{"as_written": "The course will benefit if students already know some of the following topics: Basics of TCP/IP networks: TCP/IP stack, transport protocols, application layer protocols, IP addressing, OSI -7 layer model"}, {"course": "/courses/bste-advanced-linux.md", "as_written": "Linux OS: architecture, system calls, ELF binary structure, networking and administration", "via": "model"}, {"course": "/courses/bsc-system-and-network-administration.md", "as_written": "Shell Scripting: ability to work with the terminal as administrator and automatise tasks", "via": "model"}]
prerequisite_of: ["/courses/msc-inter-networking-and-routing.md", "/courses/msc-offensive-technologies.md"]
taught_by: ["/people/rasheedhussain.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Classical Internet Applications

## Classical Internet Applications
- **Course name**: Classical Internet Applications
- **Code discipline**: SNE-03
- **Subject area**: 

### Short Description
This course covers the following concepts: Internet applications; Focus on the application layer of the TCP/IP protocol stack; Implementation, configuration, and security of Internet applications.

### Prerequisites

#### Prerequisite subjects
- The course will benefit if students already know some of the following topics: Basics of TCP/IP networks: TCP/IP stack, transport protocols, application layer protocols, IP addressing, OSI -7 layer model
- Linux OS: architecture, system calls, ELF binary structure, networking and administration
- Shell Scripting: ability to work with the terminal as administrator and automatise tasks

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Booting, Operating Systems, and Computer Architecture | # Booting principles and disks <br> # Essentials of operating systems <br> # Fundamentals of computer architecture |
| DNS, DNSSEC, and DoH | # DNS <br> # DNSSEC <br> # DoH |
| Email | # Email architecture <br> # Spam management |
| Directory, Web, Protocol, ABNF and Deflating | # Directory services <br> # Web <br> # Protocols <br> # ABNF <br> # Deflating |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
CIA course serves as kick-start for the security and network engineering Masters program. Before diving into the depth of the topics, the students must know preliminary concepts related to computer networks services and applications therein. This course is designed to cover the basic services offered by the Internet including operating systems and computer architecture. The concepts from this course will be used throughout the course of whole masters. More precisely, this course will cover the basic computer architecture and assembly language programming, Domain Name Services (DNS), DNSSec, email, web, directories, and disks. This course will also cover protocols and ABNF. The theory part will strengthen the theoretical aspects of the concepts whereas the lab exercises will provide the students with the opportunity to have hands-on experience of the ideas they learnt in the lectures.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Identify different Internet applications and understand their working principles from the protocols point of view
- Demonstrate the acquired knowledge and skills in classical internet applications including DNS, Email, and Directory services.
- Able to write regular expressions and context-free grammar that are essential in Internet applications and information exchange through the networks
- Able to partition disks and remember the booting principles as well as secure booting

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Demonstrate knowledge and skills to use web services
- Demonstrate the essential knowledge of disks and calculate particular locations/addresses in disks
- Reason about problems in the current DNS and the need to upgrade to DNSSEC and DNS over HTTPS
- Demonstrate the knowledge of email and other services configuration

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Install, Configure, update, and manage DNS services over a network
- Configure, maintain, and update the secure DNS over a network
- Update, add, and delete records in DNS
- Configure a secure mail server and maintain it
- Get hands-on experience of the afore-mentioned technologies on their own servers. 
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
| Labs/seminar classes | 20 |
| Lab tasks assessment | 40 |
| Exams | 40 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Lecture slides
- RFCs
- Link to the online material will be provided (if any)

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
| Question | What are the different steps in booting? | 1 |
| Question | How the disks are partitioned? | 1 |
| Question | Explain UEFI booting | 1 |
| Question | Demonstrating the knowledge of booting | 0 |
| Question | Analyze assembly code at a basic level | 0 |
| Question | Demonstrate the system and library calls in operating systems | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Hows does DNS query get resolved? | 1 |
| Question | What is iterative and recursive DNS server? | 1 |
| Question | How does wildcard work in DNS? | 1 |
| Question | What is zone walking in secure DNS? | 1 |
| Question | What is delegation in DNS? | 1 |
| Question | What is NSEC and NSEC3 records in DNSSEC? | 1 |
| Question | What is the difference between DNSSEC and DoH? | 1 |
| Question | Configure DNS, DNSSEC, and DoH (with specific tasks) | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are different protocols used in email? | 1 |
| Question | What are the different agents used in email system? | 1 |
| Question | How to avoid spamming in email? | 1 |
| Question | How to configure email servers? | 1 |
| Question | Configure email server | 0 |
| Question | Configure anti-spamming techniques | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How directory services are implemented? | 1 |
| Question | How permissions are set? | 1 |
| Question | How disk partitions are made? | 1 |
| Question | How different web protocols work? | 1 |
| Question | How network packets are management in a standard way through ABNF? | 1 |
| Question | How to write new formats through ABNF? | 1 |
| Question | Implement different web services | 0 |
| Question | Configure active directory | 0 |
#### Final assessment
**Section 1**
1. Same as above
**Section 2**
1. How does DNS query get resolved in DNS?
1. How zones are formed?
1. How delegation works in DNS?
1. How resource records are verified in DNSSEC?
1. What is meant by zone walking and how is it avoided?
1. Why do we need DNSSEC where we can use simple DNS over HTTPS?
**Section 3**
1. What are different agents and their roles in email architecture?
1. How MX records work?
1. How to configure different anti-spamming policies?
**Section 4**
1. As above

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

<!-- catix:relations -->
## Relations

- Prerequisites: The course will benefit if students already know some of the following topics: Basics of TCP/IP networks: TCP/IP stack, transport protocols, application layer protocols, IP addressing, OSI -7 layer model; [BSTE: Advanced Linux](/courses/bste-advanced-linux.md) (Linux OS: architecture, system calls, ELF binary structure, networking and administration, matched by the model); [System and Network Administration](/courses/bsc-system-and-network-administration.md) (Shell Scripting: ability to work with the terminal as administrator and automatise tasks, matched by the model)
- Required for: [Inter-Networking and Routing](/courses/msc-inter-networking-and-routing.md), [MSc: Offensive Technologies](/courses/msc-offensive-technologies.md)
- Taught by: [Rasheed Hussain](/people/rasheedhussain.md)
<!-- /catix:relations -->

# Citations

1. [MSc: Classical Internet Applications](https://eduwiki.innopolis.university/index.php/MSc%3A_Classical_Internet_Applications), revision 7471

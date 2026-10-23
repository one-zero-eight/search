---
type: course
title: "BSc: Networks"
description: "An introductory course on computer networking covering TCP/IP, routing, addressing, and network programming."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Networks"
tags: ["networks", "tcp-ip", "routing", "computer-networks", "bsc"]
aliases: ["BSc:Networks"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Networks"
    id: "8746"
    title: "BSc: Networks"
    last_modified: "2024-02-08T11:48:30Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:37:19+00:00"
status: draft
stale_after: "2026-02-07T11:48:30+00:00"
prerequisite_of: ["/courses/bsc-capstone-project.md", "/courses/bsc-distributed-and-network-programming.md", "/courses/msc-inter-networking-and-routing.md"]
taught_by: ["/people/artemburmyakov.md", "/people/rasheedhussain.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSc: Networks

## Networks
- **Course name**: Networks
- **Code discipline**: —
- **Subject area**: 

### Short Description
This course covers the following concepts: Computer networking; TCP/IP layered structure; Addressing; Routing; Applications; Transport and application protocols.

### Prerequisites

#### Prerequisite subjects


#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Application layer | # Application layer functionality <br> # Application layer protocols <br> # Domain name system <br> # Web <br> # File transfer |
| Transport layer | # TCP and UDP <br> # Transmission control <br> # Quality of service <br> # Delay-tolerant networking |
| Network layer | # IP addressing <br> # Subneting <br> # Routing <br> # Inter-networking <br> # host-to-host networking |
| Physical and data link layer | # Layered structure of network <br> # Physical layer <br> # Data link layer <br> # Medium access control <br> # Congestion <br> # Swiching <br> # Sliding window protocols and other protocols in physical and link layer |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
This is an introductory course to Computer Networks. During the course, we will introduce the fundamental principles behind modern computer networks, including the OSI reference model, the fundamental communication protocols, network topologies, and peer-to-peer and client-server architectures for network applications. We will also cover the basic C functions for network programming, as well as software tools to monitor data packets in a network, the configuration of routers and routing algorithms. We will conclude the course with covering the modern problems of existing computer networks, including the security aspects.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Layered structure of a computer network
- Topologies in computer networks
- Addressing schemes in networks
- Routing algorithms
- Security at different TCP/IP layers
- Nuts and bolts of applications in networks

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- How a network is formed
- How addressing is done at different layers of the networks
- How subnets are created
- How different routing protocols work and which one is better in which scenario
- How medium is accessed on a network
- How different networks operate
- And Demonstrate the knowledge and discuss the overal functioning of a computer network

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Configure networks
- Configure routing
- Perform TCP and UDP connections
- Create networks and subnets
- Write simple network applications through sockets 
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
| Regular Quizzes (During lectures, tutorials, or labs) | 5 (excluding 3 worst) |
| Midterm Exam | 20 |
| Final Exam | 60 |
| Labs/seminar classes | 15 |

All labs must be delivered by a specified date, before the exam date, otherwise the course is failed; late labs delivery without justifying reasons is penalised.

Failing any part of the evaluation (that is scoring less than 60%) will trigger a failure in the entire course (midterm is an exception). If there are no failed components, then the final grade is computed as a weighted average of the components listed above approximated at the highest second digit and then rounded to the closest integer.

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Lecture material
- Computer networking: A top-down approach / James F. Kurose, Keith W. Ross.—6th edition (or later ones)
- Optional reading: Computer Networks / Andrew S. Tanenbaum, David J. Wetherall - 5th ed.
- Online resources

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 |
| --- | --- | --- | --- | --- |
| Homework and group projects | 1 | 1 | 1 | 1 |
| Midterm evaluation | 1 | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 |
| Reports | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How application layer protocols work? | 1 |
| Question | How DNS work with the transport layer protocols? | 1 |
| Question | How does http and https work? | 1 |
| Question | How does ftp work? | 1 |
| Question | How security is incoporated at application layer? | 1 |
| Question | Which applications need TCP and UDP at the lower layer? | 1 |

##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How does TCP 3-way handshake work? | 1 |
| Question | How reliability is achieved in TCP? | 1 |
| Question | What are the pros and cons of connectionless and connection-oriented protocols in transport layer? | 1 |
| Question | How security is provided at transport layer? | 1 |
| Question | Implement TCP connection through sockets | 0 |
| Question | Develop simple application incorporating TCP and UDP | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are different classes of IPv4 address? | 1 |
| Question | Why do we need IPv6? | 1 |
| Question | How different routing protocols work and why do we need different routing algorithms? | 1 |
| Question | How quality of service is provided at network layer? | 1 |
| Question | How to create different subnets? | 1 |
| Question | Configure routing table | 0 |
| Question | Create subnets | 0 |
| Question | Work on quality of service, congestion and related topics | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How do different protocols work at physical and link layer? | 1 |
| Question | How does a switch and a hub work? | 1 |
| Question | How does different medium access control mechanisms work? | 1 |
| Question | How to detect and correct errors in transmission? | 1 |
| Question | What are different transmission media? | 1 |
| Question | Configure switches | 0 |
| Question | Detect errors in transmission | 0 |
| Question | Play with different protocols, e.g., ARP | 0 |
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

- Required for: [BSc: Capstone Project](/courses/bsc-capstone-project.md), [BSc: Distributed And Network Programming](/courses/bsc-distributed-and-network-programming.md), [Inter-Networking and Routing](/courses/msc-inter-networking-and-routing.md)
- Taught by: [Artem Burmyakov](/people/artemburmyakov.md), [Rasheed Hussain](/people/rasheedhussain.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Networks](https://eduwiki.innopolis.university/index.php/BSc%3A_Networks), revision 8746

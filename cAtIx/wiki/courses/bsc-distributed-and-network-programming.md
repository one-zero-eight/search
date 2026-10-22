---
type: course
title: "BSc: Distributed And Network Programming"
description: "Course covering network programming, TCP/UDP sockets, multithreaded servers, and distributed systems concepts like RPC, P2P, coordination, and fault tolerance."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Distributed_And_Network_Programming"
tags: ["distributed-systems", "network-programming", "sockets", "rpc", "fault-tolerance"]
aliases: ["BSc:DistributedAndNetworkProgramming"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Distributed_And_Network_Programming"
    id: "8151"
    title: "BSc: Distributed And Network Programming"
    last_modified: "2023-03-22T15:27:31Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:08:55+00:00"
status: draft
stale_after: "2025-03-21T15:27:31+00:00"
prerequisite_of: ["/courses/bsc-capstone-project.md"]
prerequisites: [{"course": "/courses/bsc-networks.md", "as_written": "**Networks**: 1) Understanding Application, Transport, and Network layers, 2) Basic socket programming experience", "via": "model"}, {"course": "/courses/bsc-operating-systems.md", "as_written": "**Operating systems**", "via": "model"}]
taught_by: ["/people/ahsankazmi.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSc: Distributed And Network Programming

## Distributed and Network Programming
- **Course name**: Distributed and Network Programming
- **Code discipline**: XYZ
- **Subject area**: xxx

### Short Description
This course covers the following concepts: Network programming concepts: Layered architecture, TCP and UDP sockets, multithreaded servers; Distributed systems concepts: system architecture, inter-process communication, remote procedure calls, peer-to-peer systems, coordination, replication, and fault tolerance..

### Prerequisites

#### Prerequisite subjects
- **Networks**: 1) Understanding Application, Transport, and Network layers, 2) Basic socket programming experience
- **Operating systems**

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Introduction to subject, computer networks basics, transport layer protocols, and socket programming | # General introduction to the course <br> # Computer networks basic <br> # Socket programming <br> # UDP socket programming <br> # TCP socket programming |
| Multithreaded socket programming, RPCs, and distributed system architecture | # Multithreading and multithreaded socket programming <br> # Remote procedure calls (RPCs) <br> # Distributed system architectures |
| Coordination, consistency, and replication in distributed systems | # Clock synchronization algorithms (NTP, Berkeley) <br> # Logical clock (Lamport clocks) <br> # Mutual exclusion algorithms: permission-based, token-based <br> # Election algorithms: Bully, Ring <br> # Consistency models <br> # Replica management <br> # Consistency protocols |
| Fault tolerance and security in distributed systems | # Intro to fault tolerance: Failure models, Failure masking by redundancy <br> # Process resilience: process groups, process replication, consensus in faulty systems, failure detection <br> # Reliable group communication: atomic multicast, <br> # Distributed commit <br> # Recovery: checkpointing <br> # Intro to security: threats, design issues, cryptography <br> # Secure channels: authentication, message integrity and confidentiality, secure group communication <br> # Access control: general issues, firewalls, secure mobile code, denial of service <br> # Secure naming <br> # Security management: Key management, secure group management, authorization management |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
Distributed and networked systems have become an integral part of our life, we use various applications such as chatting, online transactions, or cloud storage apps. All these popular applications are supported by an infrastructure (of servers) that is organized based on some concepts of distributed systems. The purpose of this course is to provide the students with the necessary concepts, models, and real-world problem-solving techniques of network programming and distributed systems.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Concepts of network programming
- Different distributed system architectures
- Various synchronization and coordination techniques
- Different consistency models and replication methods
- Approaches to achieve fault tolerance and security in distributed systems

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Difference between different transport protocols, when and why one is preferred over another
- Difference between different distributed system architectures (centralized, decentralized, and hybrid)
- How a mutual exclusion is achieved between concurrent servers (centralized, distributed, token-ring, and decentralized)
- How a new leader is elected in peer-to-peer systems (bully, ring)
- How to achieve a consistent replicas across distributed systems (consistency models and protocols, content replication and placement)
- Some methods to achieve the fault tolerance in distributed systems

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Building a custom application protocols on top of the existing transport protocols
- Writing multithreaded server and client apps with sockets
- Using RPC for inter-process communication: command execution, file transfer
- Building peer-to-peer systems with distributed protocol such as Chord
- Building fault-tolerant systems with failure detection and leader election 
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
| Laboratory assignments | 55% |
| Final exam | 35% |
| Attendance | 10% |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Textbook: Maarten Van Steen, and Andrew S. Tanenbaum. Distributed systems (3rd Edition) Leiden, The Netherlands: Maarten van Steen, 2017. Available online: https://www.distributed-systems.net/
- Reference: George F. Coulouris, Jean Dollimore, and Tim Kindberg. Distributed systems: concepts and design (5th Edition) Addision Wesley, 2012. Available online: https://www.cdk5.net/wp/
- Reference: Sukumar Ghosh. Distributed systems: an algorithmic approach (2nd Edition) Chapman&Hall /CRC, Author’s own course material, Spring 2015. Available online: http://homepage.divms.uiowa.edu/~ghosh/16615.html

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
| Oral polls | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are the distributed systems? | 1 |
| Question | Give an example of distributed systems. | 1 |
| Question | What are the advantages of layered architecture? | 1 |
| Question | What are the roles of transport protocols? | 1 |
| Question | How the TCP and UDP differ from each other? When one is preferred over the other? | 1 |
| Question | What is socket programming? | 1 |
| Question | How socket programming is different for UDP and TCP? | 1 |
| Question | Write a simple UDP/TCP client-server echo program | 0 |
| Question | Write a simple chatting program using UDP/TCP sockets | 0 |
| Question | Given the simple echo server program, apply socket timeouts and catch timeout exceptions | 0 |
| Question | Write a UDP-based reliable file transfer protocol | 0 |
| Question | Write a program that parallelly executes the CPU-bound tasks using multiple processes | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How the threads differ from processes? | 1 |
| Question | What are the I/O and CPU-bound tasks? | 1 |
| Question | For what kind of tasks, using threads is preferred than using processes? | 1 |
| Question | What is a remote procedure call? | 1 |
| Question | What are some well-known distributed system architectures? | 1 |
| Question | Discuss the structured and unstructured decentralized architectures. | 1 |
| Question | You have a list of large numbers, and you need to find if they are prime or not. Would you use multithreading, multiprocessing, or sequential programming in order to complete the task asap? Prove it in practice. | 0 |
| Question | You need to send multiple requests to a server and receive responses. Assume there is a few msecs of delay before you receive the response from the server. Would you use multithreading, multiprocessing, or sequential programming in order to complete the task asap? Prove it in practice. (Order of the requests/responses doesn't matter) | 0 |
| Question | Discuss two ways of creating the threads using threading module in Python: 1) passing the worker function as a target, 2) subclassing the Thread class | 0 |
| Question | Given the function implemented locally, make it available to be called through RPC from remote process? Use xmlRPC. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How NTP protocol works? | 1 |
| Question | How Berkeley protocol works? | 1 |
| Question | Discuss the mutual exclusion algorithms. | 1 |
| Question | Discuss the permanent and server-initiated replicas and their difference | 1 |
| Question | Explain the Primary-backup protocol. | 1 |
| Question | Given three machines with drifting clocks, adjust their clocks using Berkeley algorithm. | 0 |
| Question | Explain how Bully algorithm for election works | 0 |
| Question | Explain how Ring algorithm for election works | 0 |
| Question | Explain the centralized (permission-based) method of mutual exclusion | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Discuss the failure models | 1 |
| Question | Discuss different failure masking techniques by redundancy | 1 |
| Question | What is k-fault tolerant group? | 1 |
| Question | What is general model of failure detection? | 1 |
| Question | Explain basic reliable multicasting | 1 |
| Question | Explain what is authentication | 1 |
| Question | Explain what are message confidentiality and integrity | 1 |
| Question | Same as above | 0 |
#### Final assessment
**Section 1**
1. Describe an advantage of layered architecture?
1. Describe the differences between TCP and UDP protocols?
1. Provide examples when using UDP can be more reasonable than TCP?
1. Describe how UDP and TCP socket programming differ from each other?
**Section 2**
1. Discuss the differences between the threads and processes.
1. What is the Race condition?
1. Discuss the ways to protect the shared data from the race condition
1. You're given the worker function that just sleeps for a second and quits, implement the same behavior in a subclass of the Thread.
1. Discuss the RPC and its advantages over using the low-level socket programming?
1. Discuss the decentralized architecture: structured and unstructured p2p systems.
**Section 3**
1. Discuss NTP and Berkeley protocols for synchronization and explain their key difference
1. Discuss permission-based and token-based solution for mutual exclusion.
1. Discuss content replication: permanent, server-initiated, and client-initiated replicas.
1. Explain the Primary-backup protocol, its advantages and disadvantages.
**Section 4**
1. Same as above

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

<!-- catix:relations -->
## Relations

- Prerequisites: [BSc: Networks](/courses/bsc-networks.md) (**Networks**: 1) Understanding Application, Transport, and Network layers, 2) Basic socket programming experience, matched by the model); [BSc: Operating Systems](/courses/bsc-operating-systems.md) (**Operating systems**, matched by the model)
- Required for: [BSc: Capstone Project](/courses/bsc-capstone-project.md)
- Taught by: [Ahsan Kazmi](/people/ahsankazmi.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Distributed And Network Programming](https://eduwiki.innopolis.university/index.php/BSc%3A_Distributed_And_Network_Programming), revision 8151

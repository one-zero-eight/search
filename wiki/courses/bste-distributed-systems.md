---
type: course
title: "BSTE: Distributed Systems"
description: "Course CSE 506 covering fundamental principles, architectures, consensus algorithms, and software engineering for distributed systems."
resource: "https://eduwiki.innopolis.university/index.php/BSTE%3A_Distributed_Systems"
tags: ["distributed-systems", "computer-science", "cse-506", "raft", "paxos"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSTE%3A_Distributed_Systems"
    id: "8055"
    title: "BSTE: Distributed Systems"
    last_modified: "2023-02-08T12:21:06Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T02:06:20+00:00"
status: draft
stale_after: "2025-02-07T12:21:06+00:00"
prerequisites: [{"course": "/courses/bsc-operating-systems.md", "as_written": "CSE105"}, {"as_written": "CSE501"}]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSTE: Distributed Systems

## Distributed Systems
- **Course name**: Distributed Systems
- **Code discipline**: CSE 506
- **Subject area**: Computer Science Fundamentals

### Short Description
This is an introductory course in distributed systems. During the course, students will learn the fundamental principles and techniques that can be applied to design and develop distributed systems and will cover architectures of distributed systems, communication, naming, fault tolerance, consistency replication, virtualization, and security. In addition, we will discuss different aspects of the design and implementation of popular distributed systems programming models and consensus algorithms (Raft and Paxos). The course will not only cover computer science-related topics but will also include a substantial part of software engineering activities.

### Prerequisites

#### Prerequisite subjects
- CSE105
- CSE501

#### Prerequisite topics
- Operating Systems.
- Computer Networks

### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Introduction to distributed systems | # Distributed architectures <br> # Types of distributed systems <br> # Processes & Threads <br> # Multiprocessor and distributed scheduling <br> # Communication in distributed systems <br> # Naming in distributed systems |
| Virtualization and cloud computing | # Foundations of virtualization <br> # OS-level virtualization <br> # System level virtualization <br> # Memory virtualization <br> # Cloud and data centres |
| Canonical Problems and Solutions | # Mutual exclusion <br> # Leader election, <br> # Clock synchronization <br> # Consistency issues <br> # Caching and replication <br> # Fault Tolerance |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
What is the main goal of this course formulated in one sentence?
The main purpose of this course is to enable a student to understand the fundamental principles and techniques that can be applied to design and develop a distributed system.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Key principles involved in designing and implementing distributed systems
- Distributed Architectures and their management
- Canonical problems and solutions for distributed systems
- Resource sharing, replication and consistency algorithms in distributed environments
- Virtualization, Orchestration and cloud management

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Implementation of access and location transparency in distributed systems
- Designing and implementing consensus algorithms for different distributed environments
- Management of concurrent tasks in distributed settings
- Designing fault-tolerant distributed systems

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Implement different components in distributed systems
- Design virtualization-based approaches in distributed systems
- Develop a solution for management and orchestration of resources in distributed systems
- Develop fault tolerant approaches in distributed systems 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 90-100 | - |
| B. Good | 75-89 | - |
| C. Satisfactory | 60-74 | - |
| D. Fail | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Exam | 50 |
| Project Report | 30 |
| Interim Presentation | 5 |
| Final Presentation | 15 |

#### Recommendations for students on how to succeed in the course
Participation is important. Showing up is the key to success in this course.
You will work in teams, so coordinating teamwork will be an important factor for success. This is also reflected in the peer review being a graded item.
Review lecture materials before classes to do well in quizzes.
Reading the recommended literature is optional, and will give you a deeper understanding of the material.

### Resources, literature and reference materials

#### Open access resources
- A.S. Tanenbaum and M. Van Steen. Distributed Systems: Principles and Paradigms
- (3rd Edition). Createspace Independent Pub, 2017.
- Amazon Web Services in Action by Andreas Wittig and Michael Wittig

#### Closed access resources


#### Software and tools used within the course
- Provide at least 3 open/freemium access tools 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Teaching and Learning Methods within each section**

| Teaching Techniques | Section 1 | Section 2 | Section 3 |
| --- | --- | --- | --- |
| Problem-based learning (students learn by solving open-ended problems without a strictly-defined solution) | 1 | 1 | 1 |
| Project-based learning (students work on a project) | 1 | 1 | 1 |
| Differentiated learning (provide tasks and activities at several levels of difficulty to fit students needs and level) | 1 | 1 | 1 |
| развивающего обучения (задания и материал "прокачивают" ещё нераскрытые возможности студентов); | 1 | 1 | 1 |
| концентрированного обучения (занятия по одной большой теме логически объединяются); | 1 | 1 | 1 |
| inquiry-based learning | 1 | 1 | 1 |
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 |
| --- | --- | --- | --- |
| Lectures | 1 | 1 | 1 |
| Interactive Lectures | 1 | 1 | 1 |
| Lab exercises | 1 | 1 | 1 |
| Group projects | 1 | 1 | 1 |
| Peer Review | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 |
| Presentations by students | 1 | 1 | 1 |
| Written reports | 1 | 1 | 1 |
| Oral Reports | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Exam | State advantages of object-based architectures over layer-based architectures in a distributed system? <br> State the advantages of the random walk approach over the flooding approach in unstructured P2P networks for locating the data? <br> Why global variables are not allowed in an RPC? <br> Describe approaches for a server to handle incoming socket connections (at least two). <br> What are the pros and cons of different approaches to sockets? When would you choose which one? | 1 |
| Presentation | Prepare a short 2-minutes pitch for your project idea (2-5 slides). <br> Suggested structure: <br> What problem you are solving: <br> - State the problem clearly in 2-3 short sentences. <br> What are the approaches used to solve it: <br> - State at least three to four research papers which have solved a similar problem like a literature review. | 1 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Exam | What are containers? State at least three benefits of using them? <br> Why memory reclamation approaches are needed for virtual machines? <br> What are “cgroup” and “namespace” subsystems? How can we use the “cgroup” subsystem? <br> Briefly explain the “Ballooning” approach and its work to reclaim VM memory. <br> What is a Unikernel? State at least two benefits and one drawback. | 1 |
| Presentation | Prepare a 15-mins presentation describing your: <br> Literature review <br> SWOT analysis <br> Each team will present in class. The assessment will be based on the presentation delivery, reasoning for decision-making, and answering questions. | 1 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Exam | Why is Anti-Entropy Protocol considered better than the Gossiping protocol for achieving consistency. <br> What is the role of Heartbeats in RAFT? <br> Explain PAXOS to achieve consistency? <br> What is the benefit of three phase commit over two phase commit? Please specify in terms of coordinator failure? <br> How many replicas are required to identify the fault in Byzantine failure scenarios? | 1 |
| Report | Write and submit a project report: <br> Suggested structure: <br> What problem you are solving: <br> - State the problem clearly in 2-3 short sentences. <br> What is your proposed solution to solve that problem: <br> - One sentence description <br> - What main feature(s) will it have? <br> SWOT Analysis | 1 |
#### Final assessment
**Section 1**
1. Can be a final exam, project defense, or some other equivalent of the final exam.
1. For the final assessment, students present the project work they have accomplished during the course. 
**Section 2**

**Section 3**


#### The retake exam
**Section 1**
1. For the retake, students have to implement a project and take the exam if they failed in both components. The complexity of the project can be reduced if it is one person working on it. The grading criteria for each section are the same as for the final project presentation. There has to be a meeting before the retake itself.
1. P7. Activities and Teaching Methods by Sections
1. Mark what techniques and methods are used in each section (1 is used, 0 is not used).
1. Table A1: Teaching and Learning Methods within each section
1. Table A2: Activities within each section
**Section 2**

**Section 3**

<!-- catix:relations -->
## Relations

- Prerequisites: [BSc: Operating Systems](/courses/bsc-operating-systems.md) (CSE105); CSE501
<!-- /catix:relations -->

# Citations

1. [BSTE: Distributed Systems](https://eduwiki.innopolis.university/index.php/BSTE%3A_Distributed_Systems), revision 8055

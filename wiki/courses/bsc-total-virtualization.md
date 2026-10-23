---
type: course
title: "Total virtualization"
description: "BSc course on virtualization technologies, covering IaaS, PaaS, containers, and cloud infrastructure management."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Total_Virtualization"
tags: ["course", "virtualization", "cloud", "containers", "bsc"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Total_Virtualization"
    id: "7803"
    title: "BSc: Total Virtualization"
    last_modified: "2022-11-23T08:24:26Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T02:00:33+00:00"
status: draft
stale_after: "2024-11-22T08:24:26+00:00"
prerequisites: [{"as_written": "CSE101"}, {"as_written": "СSE105"}, {"as_written": "CSE112 or CSE118 or CSE420"}, {"as_written": "CSE130 or CSE512  or CSE128"}, {"as_written": "22 or CSE804 or CSE809 or CSE812"}]
relations_by: "process:catix-wiki-graph/0.1"
---

# Total virtualization

- **Course name**: Total virtualization
- **Code discipline**: ????
- **Subject area**: 

### Short Description


### Prerequisites

#### Prerequisite subjects
- CSE101
- СSE105
- CSE112 or CSE118 or CSE420
- CSE130 or CSE512  or CSE128
- 22 or CSE804 or CSE809 or CSE812

#### Prerequisite topics
- Basic programming skills.
- Software architecture
- Computer architecture
- Basics of Operating systems

### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Section 1 | # The need for virtualization: clouds, IaaS, DaaS, SaaS, PaaS. <br> # A virtualization introduction: basic terms, history <br> # CPU virtualization approaches: emulation, binary recompilation, stabbing, para-virtualization, hardware-assisted technologies <br> # Physical memory virtualization issues: compression, swap files, balloons <br> # Virtual paging, interrupts and devices, virtual video <br> # VM performance <br> # VM migration <br> # Introduction to containers <br> # Dockers |
| Section 2 | # IaaS: Resource distribution (memory, CPU) <br> # IaaS: Dynamic power management <br> # IaaS: Failovers and backups <br> # PaaS: a view from inside <br> # PaaS: a revolution driven by microservices <br> # Migrating to the cloud: cost, risks and deployment models, choice of cloud providers <br> # Security issues of clouds and virtualisation <br> # Cloud storages |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?


#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Differ PaaS from IaaS and SaaS
- Explain the basic principles of virtualization
- Understand difference between containers and virtual machines
- Know criteria of choice between containers and virtual machines for different workloads
- Know memory management strategies and techniques
- Remember diffetent virtualization approaches
- Understand internals of PaaS and argue what is SaaS and what is PaaS

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Create a container based on cgroups interface
- Deploy an application into the cloud infrastructure
- Use PaaS API for debug and monitoring
- Tune performance of a virtual machine
- Estimate cost of public IaaS use vs on-premise deployment

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Make weighted and reasonable architectural choices in virtualization and cloud domain 
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


#### Closed access resources
- Carl Waldspurger, Mendel Rosenblum, “I/O virtualization”, Communications of ACM, 2012

#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Teaching and Learning Methods within each section**

| Teaching Techniques | Section 1 | Section 2 |
| --- | --- | --- |
| Problem-based learning (students learn by solving open-ended problems without a strictly-defined solution) | 1 | 1 |
| Project-based learning (students work on a project) | 1 | 1 |
| Modular learning (facilitated self-study) | 1 | 1 |
| Contextual learning (activities and tasks are connected to the real world to make it easier for students to relate to them); | 1 | 1 |
| Business game (learn by playing a game that incorporates the principles of the material covered within the course). | 1 | 1 |
**Activities within each section**

| Learning Activities | Section 1 | Section 2 |
| --- | --- | --- |
| Lectures | 1 | 1 |
| Interactive Lectures | 1 | 1 |
| Lab exercises | 1 | 1 |
| Discussions | 1 | 1 |
| Written reports | 1 | 1 |
| Cases studies | 0 | 1 |
| Quizzes (written or computer based) | 0 | 1 |
| Simulations and role-plays | 0 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Individual Assignments | A1: Find the response in Linux kernel source code? <br> Find the VT-x virtualization loop. Specify related functions <br> Find the PF handler | 1 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Quiz | 1. Which type of virtualization would you recommend for the following workload? <br> 2. Why SMP workload could be slow in virtual machines? <br> 3. Which type of vulnerability is more “popular” for virtual machines then for containers? | 1 |
#### Final assessment
**Section 1**

**Section 2**


#### The retake exam
**Section 1**

**Section 2**

<!-- catix:relations -->
## Relations

- Prerequisites: CSE101; СSE105; CSE112 or CSE118 or CSE420; CSE130 or CSE512  or CSE128; 22 or CSE804 or CSE809 or CSE812
<!-- /catix:relations -->

# Citations

1. [BSc: Total Virtualization](https://eduwiki.innopolis.university/index.php/BSc%3A_Total_Virtualization), revision 7803

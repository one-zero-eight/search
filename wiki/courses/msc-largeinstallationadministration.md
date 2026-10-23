---
type: course
title: "Large Systems"
description: "Course covering virtualization, large system architecture, automation, and infrastructure management for scalable IT environments."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3ALargeInstallationAdministration"
tags: ["course", "large-systems", "virtualization", "devops", "infrastructure"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3ALargeInstallationAdministration"
    id: "180"
    title: "MSc:LargeInstallationAdministration"
    last_modified: "2021-08-02T06:34:08Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:43:57+00:00"
status: draft
stale_after: "2023-08-02T06:34:08+00:00"
---

# Large Systems

## Large Systems

- **Course name:** Large Systems
- **Course number:** xyz

### Course Characteristics

#### Key concepts of the class

- Virtualization and management of large systems
- Communication, coordination and fault tolerance IT for infrastructure

#### What is the purpose of this course?

In large organizations complex architectures are built where products and protocols of multiple vendors have to inter-operate. The course focuses on understanding the challenges and building a scalable IT infrastructure that is flexible and efficient to manage. Topics covered are: Virtualization and Cloud Computing, Workstation and Server deployment, Data-centers and Infrastructure management methodologies.

#### Course objectives based on Bloom’s taxonomy

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to remember the followings:

- Install and configure large systems
- Automate the installation and the deployment process in large systems
- Usage of virtualized systems.
- Manage scalable infrastructures
- Fault tolerance and solutions in large systems

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to understand the key components of large systems

- Management and control of large systems
- Different components and architectures of large systems
- Role of virtualization and orchestration for managing large systems.
- Continuous integration and continuous deployment approaches

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to develop, manage and implement different large system components

- Implementation of different virtualization techniques over different platforms
- Designing and implementing orchestration schemes for large systems
- Implement Continuous integration and continuous deployment to automate the installation and the deployment.
- Designing fault tolerant systems

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 20 | 35 |
| Interim performance assessment | 30 | 35 |
| Exams | 50 | 30 |

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 | 90-100 |
| B. Good | 75-89 | 75-89 |
| C. Satisfactory | 60-74 | 60-74 |
| D. Poor | 0-59 | 0-59 |

#### Resources and reference material

- 
- 
- 

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Virtualization | 16 |
| 2 | Building blocks for Large systems | 16 |
| 3 | Automation and Management | 16 |

#### Section 1

##### Section title:

Virtualization

#### Topics covered in this section:

- Foundations of virtualization
- OS-level virtualization
- System level virtualization
- Memory virtualization
- Orchestration and Management

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| & **Yes/No**

Development of individual parts of software product code & 1

Homework and group projects & 1

Midterm evaluation & 1

Testing (written or computer based) & 1

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 1

#### Typical questions for ongoing performance evaluation within this section

1. What are containers? State at least three benefits of using them?
1. Why memory reclamation approaches are needed for virtual machines?
1. What are “cgroup” and “namespace” subsystems. How can we use the “cgroup” subsystem?
1. Briefly explain about the “Ballooning” approach and its working to reclaim VM memory?
1. What is a Unikernel? State at least two benefits and one drawback.

#### Typical questions for seminar classes (labs) within this section

1. Validate that when a node goes down a new instance is launched. Show how the redistribution of the instances can happen when the broken node comes back alive?
1. Deploy a simple application (e.g. a simple web page showing the hostname of the host node it is running upon) for each orchestrator and validate that its instances spreads around the container farm.
1. What is the difference between simple load-balancing and HA load-balancing?
1. Install at least 4 different types of guest systems or distributions on the physical host?
1. Create a simple web page (preferably containing some pictures), construct an image with operating system you chose and deploy it via the unikernal.

#### Test questions for final assessment in this section

1. State two benefits of immersion cooling over traditional air cooling in data centers?
1. State one main difference of a container from a System Virtual machine?
1. Briefly explain about Copy-on-write storage.
1. What are the roles of “ISA” and “ABI” in operating systems?
1. What is the biggest drawback of Google File system over CephFS?

#### Section 2

##### Section title:

Building blocks for Large systems

#### Topics covered in this section:

- Storage technologies
- Backup and monitoring technologies
- NoSQL and distributed storage
- Communication and coordination approaches in LS
- Fault tolerance in LS

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| & **Yes/No**

Development of individual parts of software product code & 1

Homework and group projects & 1

Midterm evaluation & 1

Testing (written or computer based) & 1

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 1

#### Typical questions for ongoing performance evaluation within this section

1. What is a schema-less data model?
1. Why do we need NoSQL? What are its benefits over SQL in terms of ACID and BASE properties?
1. Why is Anti-Entropy Protocol considered better than the Gossiping protocol for achieving consistency.
1. What is the role of Heartbeats in RAFT?
1. Explain PAXOS to achieve consistency?
1. How many replicas are required to identify the fault in Byzantine failure scenarios?

#### Typical questions for seminar classes (labs) within this section

1. Create the testing environment to test VM monitoring through a running web page.
1. Deploy zabbix server+agent (server is better to deploy on dedicated VM instance).
1. Use load-testing tool (yandex.tank, siege, k8, etc) and perform 2-3 different load tests. Report by varying the number of threads, number of clients, request body while performing requests.
1. Why do you think it is better to choose networked block device than networked file-systems, in terms of performance?

#### Test questions for final assessment in this section

1. same as above.

#### Section 3

##### Section title:

Automation and Management in LS

##### Topics covered in this section:

- IT management approaches
- DevOps and Agile practices
- Continuous Integration (CI) for automation
- Continuous Deployment (CD) for automation
- Data centres- Hardware technologies
- Blockchain technology

#### What forms of evaluation were used to test students’ performance in this section?

|a|c| & **Yes/No**

Development of individual parts of software product code & 1

Homework and group projects & 1

Midterm evaluation & 1

Testing (written or computer based) & 1

Reports & 0

Essays & 0

Oral polls & 0

Discussions & 1

#### Typical questions for ongoing performance evaluation within this section

1. What are continuous integration and continuous deployment?
1. Why is version control recommended? Name at least two version control systems?
1. State four differences between the Scrum and Kanban models?
1. Briefly explain about the Agile software development approach. How is it different from the waterfall model?

##### Typical questions for seminar classes (labs) within this section

1. Validate cold migration of your four guests.
1. Validate hot migration of your four guests.
1. What kind of general stages are there in the CI/CD pipeline? list them in the correct sequence and then describe them.
1. Select a CI/CD solution/platform and describe the project that you will apply CI/CD to it.
1. Try to automate the deployment of your project if the CI/CD pipeline passes.

##### Test questions for final assessment in this section

1. same as above.

# Citations

1. [MSc:LargeInstallationAdministration](https://eduwiki.innopolis.university/index.php/MSc%3ALargeInstallationAdministration), revision 180

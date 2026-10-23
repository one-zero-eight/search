---
type: course
title: "Data Modeling and Databases 2"
description: "Course page for Data Modeling and Databases 2, covering distributed systems, virtualization, cloud computing, and NoSQL databases with evaluation details."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3ADataModelingAndDatabases2"
tags: ["course", "databases", "distributed-systems", "cloud", "nosql"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3ADataModelingAndDatabases2"
    id: "130"
    title: "MSc:DataModelingAndDatabases2"
    last_modified: "2021-07-30T11:33:10Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:32:06+00:00"
status: draft
stale_after: "2023-07-30T11:33:10+00:00"
---

# Data Modeling and Databases 2

## Data Modeling and Databases 2

- **Course name:** Data Modeling and Databases 2
- **Course number:** XYZ

### Course Characteristics

#### Key concepts of the class

- How to design software for databases conceptually and logically
- Different aspects of internal databases design and implementations, applicable optimization
- NonSQL databases
- Basic functions of database management system

#### What is the purpose of this course?

While the course Data Modelling and Databases (DMD) covered the core concepts behind database design and the relational model, there are further considerations that should be addressed to pursue a career in this field. This course will expand upon what it has been presented in DMD course with focus on both software design, under the form of conceptual and logical DB design, and physical optimization, and will introduce concept such us concurrency and NoSQL databases. More attention will be given to the functioning of Database Management Systems (DBMs), looking at the internal implementation details.

#### Course objectives based on Bloom’s taxonomy

#### - What should a student remember at the end of the course?

- Design, develop and implement a mid-scale relational database for an application domain using a relational DBMS
- Understand physical database design, implementation, and optimization issues
- Devise appropriate ways to store and index data
- Use persistence tools in the context of modern software architectures and the Cloud
- Virtualization, Orchestration and cloud management

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to understand the key components of distributed systems

- Design, develop and implement a mid-scale relational database for an application domain using a relational DBMS
- Understand physical database design, implementation, and optimization issues
- Devise appropriate ways to store and index data
- Use persistence tools in the context of modern software architectures and the Cloud
- Virtualization, Orchestration and cloud management

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to develop and implement different components in a distributed environment

- Design, develop and implement a mid-scale relational database for an application domain using a relational DBMS
- Understand physical database design, implementation, and optimization issues
- Devise appropriate ways to store and index data
- Use persistence tools in the context of modern software architectures and the Cloud
- Virtualization, Orchestration and cloud management

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/seminar classes | 20 | 20 |
| Interim performance assessment | 30 | 25 |
| Exams | 50 | 55 |

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

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Introduction to distributed systems | 16 |
| 2 | Virtualization and cloud computing | 16 |
| 3 | Canonical Problems and Solutions | 24 |

#### Section 1

##### Section title:

Introduction to distributed systems

#### Topics covered in this section:

- Distributed architectures
- Types of distributed systems
- Processes & Threads
- Multiprocessor and distributed scheduling
- Communication in distributed systems
- Naming in distributed systems

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

1. State advantages of object based architectures over layer based architectures in distributed system?
1. State advantages of the random walk approach over the flooding approach in unstructured P2P networks for locating the data?
1. Why global variables are not allowed in a RPC?
1. Describe approaches for a server to handle incoming socket connections (at least two).
1. What are pros and cons of different approaches of sockets? When would you choose which one?

#### Typical questions for seminar classes (labs) within this section

1. Find the process ID (PID) of the running program and list of threads associated to that process?
1. Implementation of new threads
1. Performance analysis of given task
1. Implementation of Process and Global Interpreter Lock (GIL)

#### Test questions for final assessment in this section

1. Explain difference between threads and process
1. Define Global Interpreter Lock (GIL) and its role
1. What are remote method invocation (RMI). Please state the benefits and challenges of RMI.
1. Define the role of Marshaling and Unmarshaling in RPC
1. State at least two benefits of both Iterative and recursive naming resolution schemes.

#### Section 2

##### Section title:

Virtualization and cloud computing

#### Topics covered in this section:

- Foundations of virtualization
- OS-level virtualization
- System level virtualization
- Memory virtualization
- Cloud and data centres

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

1. Hands on Amazon Elastic Compute Cloud (EC2)
1. Set up a public address in Elastic IPs tab and assign it to the web server on which WordPress is hosted.
1. Configure WebServer so that your blog page is accessible only through the public IP address (without specifying the /wordpress path). For example, you specify a public IP address in the address bar of the browser and gain access to the blog.
1. There may be problems with CSS. Search the web for how to fix broken CSS after changing the site URL.

#### Test questions for final assessment in this section

1. State two benefits of immersion cooling over traditional air cooling in data centers?
1. State one main difference of a container from a System Virtual machine?
1. Briefly explain about Copy-on-write storage.
1. What are the roles of “ISA” and “ABI” in operating systems?
1. What is the biggest drawback of Google File system over CephFS?

#### Section 3

##### Section title:

Canonical Problems and Solutions

##### Topics covered in this section:

- Mutual exclusion
- Leader election,
- Clock synchronization
- Consistency issues
- Caching and replication
- Fault Tolerance

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

1. Why is Anti-Entropy Protocol considered better than the Gossiping protocol for achieving consistency.
1. What is the role of Heartbeats in RAFT?
1. Explain PAXOS to achieve consistency?
1. What is the benefit of three phase commit over two phase commit? Please specify in terms of coordinator failure?
1. How many replicas are required to identify the fault in Byzantine failure scenarios?

##### Typical questions for seminar classes (labs) within this section

1. In the replication set of databases, what problem may appear if we have an even number of nodes?
1. ICRUD operations in MongoDB.
1. Create simple chat web-application which uses replica set.
1. Explain the steps to shutdown all VPS instances.

##### Test questions for final assessment in this section

1. What is a schema-less data model
1. Why do we need NoSQL? What are its benefits over SQL in terms of ACID and BASE properties?
1. Why is version control recommended? Name at least two version control systems?
1. Role of recovery line and check pointing in distributed snapshot?
1. Explain the difference between Lamport and vector clocks?
1. How the use of buffers at receivers enhance the QoS in networks for streaming media applications? Briefly explain using an example.

# Citations

1. [MSc:DataModelingAndDatabases2](https://eduwiki.innopolis.university/index.php/MSc%3ADataModelingAndDatabases2), revision 130

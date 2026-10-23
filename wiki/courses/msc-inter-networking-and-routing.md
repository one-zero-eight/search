---
type: course
title: "Inter-Networking and Routing"
description: "Course covering inter-networking, routing protocols (BGP, OSPF, AODV), NAT, QoS, VLAN, and network traffic monitoring with hands-on hardware exercises."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Inter_Networking_and_Routing"
tags: ["networking", "routing", "bgp", "ospf", "vlan", "qos"]
aliases: ["MSc:Inter Networking and Routing"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Inter_Networking_and_Routing"
    id: "7472"
    title: "MSc: Inter Networking and Routing"
    last_modified: "2022-08-29T08:51:42Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:35:23+00:00"
status: draft
stale_after: "2024-08-28T08:51:42+00:00"
prerequisites: [{"course": "/courses/msc-classical-internet-applications.md", "as_written": "Classical Internet applications", "via": "model"}, {"course": "/courses/bsc-networks.md", "as_written": "Computer systems and networks", "via": "model"}, {"course": "/courses/bsc-networks.md", "as_written": "Basics of TCP/IP networks: TCP/IP stack, transport protocols, application layer protocols, IP addressing, OSI -7 layer model", "via": "model"}, {"course": "/courses/bsc-system-and-network-administration.md", "as_written": "Linux OS: networking and administration", "via": "model"}, {"as_written": "Linux for Beginners"}, {"course": "/courses/bste-advanced-linux.md", "as_written": "Linux Administration and Networking", "via": "model"}, {"course": "/courses/bsc-networks.md", "as_written": "Computer Networks", "via": "model"}]
taught_by: ["/people/almaoracevic.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Inter-Networking and Routing

## Inter-Networking and Routing
- **Course name**: Inter-Networking and Routing
- **Code discipline**: 
- **Subject area**: 

### Short Description
This course covers the following concepts: Inter-networking and routing; BGP, OSPF, and AODV; NAT, QoS, VLAN; Monitoring network traffic, traffic mirroring, and packet crafting as well as proxying.

### Prerequisites

#### Prerequisite subjects
- Classical Internet applications
- Computer systems and networks
- Basics of TCP/IP networks: TCP/IP stack, transport protocols, application layer protocols, IP addressing, OSI -7 layer model
- Linux OS: networking and administration
- Linux for Beginners
- Linux Administration and Networking
- Computer Networks

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Networking overview | # Present an overview of the main concepts of networking <br> # Routing Algorithms <br> # Shortest Path <br> # Real-Time Network Routing |
| IP version 6 and Layer 2 Basics | # Data link layer - introduction <br> # Present an overview of the IPv6 <br> # Present the difference between the IPv4 and IPv6 <br> # Error Control Mechanisms <br> # Reed-Solomon (RS) Codes <br> # Flow control |
| Spanning Tree and Routing Basics | # An overview of the spanning tree. <br> # An overview of the routing algorithm. |
| Link state routing protocol (OSPF) | # Shortest path first (SPF) forwarding <br> # Dijkstra’s algorithm <br> # Low Bandwidth Requirements <br> # Broadcast Networks |
| Path vector routing protocol(BGP) | # BGP4: Inter-Domain Routing in the Internet <br> # BGP Messages, Attributes and Features <br> # Inter-domain vs Intra-domain routing <br> # Autonomous Systems and Gateways |
| NAT, Proxying, traffic monitoring, and packet crafting | # Network address translation in the network <br> # Network traffic monitoring and proxying <br> # Packet crafting and tools |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
Inter-Networking and Routing is the course for SNE program that provides the students with fundamental knowledge about inter-networking and routing. The course starts with some introductory material about routing, such as the definition of path cost and the classification of routing algorithms. A networking infrastructure deploys various algorithms for routing packets, classified as those using optimal routes and those using non-optimal routes. This course includes hands-on exercise, and the students will practice their skills on the actual hardware and software. This course includes various interesting topics in the networking domain, which are also related to real-world applications. This course will particularly focus on addressing in detail routing, detailed BGP, OSPF, and AODV. Furthermore, this course also covers Network Address Translation (NAT), Quality of Service (QoS) fundamentals, as well as Virtual LAN (VLAN). It additionally discusses the network traffic, it is monitoring, proxying, and packet crafting in detail. Students will have the opportunity to apply the knowledge learned in class to actual hardware. Furthermore, this course also includes invited talks by experts from industry which will help students to have knowledge of the current state of the art.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- IP version 6 and Layer 2 Basics
- Spanning Tree and Routing Basics
- Link-state routing protocol (OSPF)
- Path vector routing protocol (BGP)
- Ad hoc On-Demand Distance Vector Routing (AODV)
- NAT, QoS, and VLAN
- Network traffic monitoring, proxying, and packet crafting

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Routing Basics
- BGP
- OSPF
- AODV
- NAT
- QoS
- VLAN
- Proxying, packet crafting

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Install, Configure, update, and manage services over a network
- Configure, maintain, and update the routing tables
- Assign network address and maintain forwarding tables
- Operate applications using BGP routing
- Operate applications using AODV routing
- Represent performance analysis of AODV, OSPF, and BGP
- Configure VLAN, NAT, and craft network packets using different tools
- Conduct quality of service experiments in the network (from routing perspective)
- Install and configure proxies in the network 
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
| Labs/seminar classes | 50 |
| Interim performance assessment | 0 |
| Exams | 50 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Radia Perlman, Interconnections: Bridges, Routers, Switches, and Internetworking Protocols, 2nd Edition, Sun Microsystems, Inc.

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 | Section 5 | Section 6 |
| --- | --- | --- | --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 1 | 1 | 1 | 1 | 1 |
| Homework and group projects | 1 | 1 | 1 | 1 | 1 | 1 |
| Midterm evaluation | 1 | 1 | 1 | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Explain an overview of the main concepts of networking | 1 |
| Question | What is the difference between a packet switching and circuit switching? | 1 |
| Question | List and briefly define types of routing. | 1 |
| Question | Briefly define the RTNR. | 1 |
| Question | What is the internetworking? | 1 |
| Question | How can a network can be simulated in a virtual environment? | 0 |
| Question | How to create a simple switched network? What is a subnet? | 0 |
| Question | How to connect a subnet to the Internet using single IP address with basic routing and NAT? | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is the difference between the IPv4 and IPv6? | 1 |
| Question | Types of ARQ Protocols? | 1 |
| Question | Briefly describe Selective Repeat. | 1 |
| Question | What is Stop and Wait algorithm? | 1 |
| Question | What are the TCP and UDP protocols? How can you discover a remote machine and detect its running services? | 0 |
| Question | How can you capture and analize a network traffic? | 0 |
| Question | How can you set-up basic IPv6 network? | 0 |
| Question | How to separate a network using VLAN technology. | 0 |
| Question | How can multiple switches be used together to provide fault tolerance. | 0 |
| Question | How to set-up a link aggregation (bond interface) to provide connection with load balancing and fault tolerance. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is spanning tree protocol? | 1 |
| Question | Explain how spanning tree protocol works? | 1 |
| Question | Hot to configure STP? | 1 |
| Question | How to set-up a link aggregation (bond interface) to provide connection with load balancing and fault tolerance. | 0 |
| Question | How can you capture and analyze a network traffic? | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How to reduce convergence delay? | 1 |
| Question | Dijkstra’s LSR algorithm explain on example! | 1 |
| Question | Give an example of topology change | 1 |
| Question | Explain Broadcast Networks | 1 |
| Question | Which interface you will select as the OSPF router ID and why? | 0 |
| Question | What is the difference between advertising all the networks VS manual advertising (per interface or per subnet)? | 0 |
| Question | Who can you check if you have a full adjacency with your router neighbor? | 0 |
##### Section 5
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How to reduce assign IP address and AS numbers? | 1 |
| Question | I-BGP and E-BGP explain! | 1 |
| Question | Intra-domain vs Inter-domain | 1 |
| Question | Explain RIP, OSPF? | 1 |
| Question | Can your BGP peers reach your internal subnets? And can you reach their internal subnets? | 0 |
| Question | How can the OSPF Internal router know about your peer’s OSPF Internal router? | 0 |
| Question | Is it a good idea to redistribute BGP routes into the OSPF routing table? | 0 |
##### Section 6
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How to configure NAT rules? | 1 |
| Question | How to monitor network traffic and at which level? | 1 |
| Question | How is proxy installed and configured? | 1 |
| Question | What are the tools used for packet crafting and how do they work? | 1 |
| Question | Configure NAT and analyze the traffic in the network? | 0 |
| Question | Monitor the network traffic and look for behaviors as well as pre-defined features? | 0 |
| Question | Pass the network traffic through a proxy by defining rules in the proxy | 0 |
| Question | craft network packets and automate | 0 |
#### Final assessment
**Section 1**
1. What is the difference between static and dynamic routing?
1. What is tunneling?
1. How to connect a subnet to the Internet using single IP address with basic routing and NAT?
**Section 2**
1. How can you set-up basic IPv6 network?
1. What is the Sliding Window algorithm?
1. How are networks connected?
1. How can multiple switches be used together to provide fault tolerance?
**Section 3**
1. How to elect one root bridge?
1. Define designated port!
1. How to configure loopguard?
**Section 4**
1. Explain Dijkstra algorithm.
1. Which interface you will select as the OSPF router ID and why?
1. Why every area has to be connected to area 0?
**Section 5**
1. Path-vector protocol, explain!
1. Multi-Exit Discriminator, explain.
1. Is it a good idea to redistribute BGP routes into the OSPF routing table?
**Section 6**
1. What are the pros and cons of different packet crafting tools?
1. How to configure NAT with different rules?
1. How to automate the packet crafting in network using different tools?
1. How proxying affect the network performance?

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

**Section 5**

**Section 6**

<!-- catix:relations -->
## Relations

- Prerequisites: [Classical Internet Applications](/courses/msc-classical-internet-applications.md) (Classical Internet applications, matched by the model); [BSc: Networks](/courses/bsc-networks.md) (Computer systems and networks, matched by the model); [BSc: Networks](/courses/bsc-networks.md) (Basics of TCP/IP networks: TCP/IP stack, transport protocols, application layer protocols, IP addressing, OSI -7 layer model, matched by the model); [System and Network Administration](/courses/bsc-system-and-network-administration.md) (Linux OS: networking and administration, matched by the model); Linux for Beginners; [BSTE: Advanced Linux](/courses/bste-advanced-linux.md) (Linux Administration and Networking, matched by the model); [BSc: Networks](/courses/bsc-networks.md) (Computer Networks, matched by the model)
- Taught by: [Alma Oracevic](/people/almaoracevic.md)
<!-- /catix:relations -->

# Citations

1. [MSc: Inter Networking and Routing](https://eduwiki.innopolis.university/index.php/MSc%3A_Inter_Networking_and_Routing), revision 7472

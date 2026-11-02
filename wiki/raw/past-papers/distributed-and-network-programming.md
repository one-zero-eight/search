---
type: page
title: "Past exam papers: Distributed and Network Programming"
description: "Past exams and tests of Distributed and Network Programming at Innopolis University (2 papers, 2021–2025), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "distributed-and-network-programming"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "Distributed and Network Programming"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: Distributed and Network Programming

Exams and tests of **Distributed and Network Programming** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2025: Final

Files: [DNP Final Answers 2025.pdf, DNP Final 2025.pdf](https://glebpopov.notion.site/1ebe746cceef80dc86a8c52800ffe7a0)

### DNP Final Answers 2025.pdf
DNP Final Exam with Answers
TOTAL: 3 + 8 + 8 + 3 + 6 + 6 + 6 = 40
1.​ [Graded by Ahmed] Consider a system with two producers and one consumer. Producers
generate random data and put it into the queue at some rate. If the queue is full, they block
until the consumer processes some items. Consumers process items as soon as they
become available in the queue. If the queue is empty, they block until new items are added
by the producers. (3 points)
a) Draw a diagram of the system showing the components and their interactions. (2pts)
-​

A very simple drawing like this one is expected. Missing any component or
misleading arrow directions were penalized.

b) Consider production rate (for one producer) is 2 items/sec and consumption rate (for one
consumer) is 1 item/sec. How many consumers are needed (at least) to have 0 buffering
time in the system? (1pt)
Answer:
-​

For two producers of 2 items/sec production rate, we need at least 4 consumers of
1 item/sec consumption rate.

2.​ [Graded by Egor]
a) Identify and describe the three main types of assumptions made in a distributed system
model. For each type, provide three concrete examples. (6 points)

1.​ Network Behavior: Describes how messages are delivered between nodes. Examples:
○​ Reliable links: messages are guaranteed to arrive.
○​ Fair-loss links: some messages may be lost, but loss is not persistent.
○​ Arbitrary links: messages may be lost, duplicated, or arrive out of order.​
2.​ Node Behavior: Specifies how individual nodes may fail. Examples:
○​ Crash-stop: a node stops working and never recovers.
○​ Crash-recovery: a node may fail and later restart.
○​ Byzantine faults: nodes may behave arbitrarily or maliciously.​
3.​ Timing Behavior: Defines assumptions about how time and message delays are handled.
Examples:
○​ Synchronous: known bounds on processing and message delays.
○​ Asynchronous: no bounds on delays.
○​ Partially synchronous: system eventually behaves synchronously, but not always.​
​
​
​
b) Explain why defining these assumptions is critical before designing a distributed algorithm. (2
points)
-​

Designing a distributed algorithm requires knowing the environment it will run in. These
assumptions determine what kinds of guarantees (like consistency, fault tolerance, or
availability) the algorithm can safely make. If assumptions are incorrect or unclear, the
algorithm might not work as intended or could even fail silently.

3.​ [Graded by Ilya] You are given a Chord overlay with m=5, so the identifier space goes from
0 to 31. The nodes in t1he system are located at identifiers [2, 13, 16, 27]. For each node,
build its finger table (5 entries). For each entry, indicate the node's successor for the
corresponding finger interval. Clearly show how you calculate each entry. Partial credit will
be given for correct logic even if your final answer is not fully accurate. (8 points, 2 points for
each node).

​
Answer: ​
2 = [13, 13, 13, 13, 27]​
13 = [16, 16, 27, 27, 2]​
16 = [27, 27, 27, 27, 2]​
27 = [2, 2, 2, 13, 13]

4.​ [Graded by Ahmed] You are designing a fault-tolerant service using redundancy. Each
individual system has a 3% chance of failing (i.e., 97% uptime), and failures are
independent. You replicate the service across three systems, and the service will remain
available as long as at least one system is working. What is the expected uptime of the
overall system? Explain your calculation. (3 points)

A)​ Compute the probability that all 3 systems fail: (1 point)​
P(all fail) = 0.03 ^ 3 = 0.000027
B)​ The system is available if at least one system is working: (1 point)​
P(available) = 1 − P(all fail) = 1 − 0.000027
C)​ Availability = 99.9973% (1 point)

5. [Graded by Egor] Explain what super-peer networks are in the context of peer-to-peer (P2P)
systems. Compare them with pure P2P architectures. Provide at least one advantage and one
disadvantage of using super-peer networks. (6 points)
Super-peer networks are a hybrid form of peer-to-peer (P2P) systems where some nodes,
called super-peers, take on additional responsibilities such as indexing, routing, or
coordination on behalf of regular peers. These super-peers act similarly to servers in a
client-server model but are themselves peers in the network, selected based on capabilities
such as higher bandwidth, availability, or processing power. (2 points)
Comparison: (2 points)
●​ Pure P2P systems: All nodes are equal, no central coordination. Routing and
resource discovery can be inefficient.
●​ Super-peer networks: Combine the scalability of P2P with some structure of
client-server by delegating certain roles to powerful peers.
Advantages: (2 points)
1.​ Improved scalability and resource discovery compared to pure P2P due to
centralized indexing at super-peers.
2.​ Better performance and query response time as super-peers reduce redundant
messaging.
Disadvantage:
●​ Super-peers can become bottlenecks or points of failure, reducing robustness if they
are overloaded or go offline.

6. [Graded by Karim] Compare Cristian’s algorithm and the Berkeley algorithm for clock
synchronization in distributed systems. Describe the steps for each of them. In what scenarios
would each be preferable? (6 points)
Evaluation: (2 points for the Cristian Algorithm, 2 points for the Berkley algorithm, 2 points
for the scenarios described).
Cristian’s Algorithm:
Cristian’s algorithm is a client-server based synchronization method where a client sends a
time request to a time server. The server responds with its current time, and the client
adjusts its clock by estimating and correcting for the round-trip delay. It assumes the server
has access to a highly accurate time source (e.g., atomic clock or GPS).
●​ Steps:
1.​ Client sends a time request to the server.
2.​ Server replies with current time.
3.​ Client sets its clock to the received time + half of the round-trip time.
Berkeley Algorithm:
The Berkeley algorithm is a decentralized approach to synchronize clocks among a group of
machines without assuming any of them has access to an accurate external clock. One
machine acts as a coordinator and polls all other nodes to collect their times, calculates an
average (excluding outliers), and sends adjustments (not absolute times) to each node.
●​ Steps:
1.​ Coordinator asks each node for its clock value.
2.​ Nodes reply with their local times.
3.​ Coordinator calculates the average time.
4.​ Coordinator sends clock adjustment instructions to each node.
●​ Cristian’s Algorithm: Used when there is a trusted time server. The client
requests time, receives it along with a round-trip estimation, and adjusts its clock.
●​ Berkeley Algorithm: Used in a peer-to-peer system without access to a UTC
server. A master polls other machines, computes an average, and tells everyone
how to adjust.

7. [Graded by Karim] You are observing a RAFT cluster of 5 servers: S1 to S5. The current state
of the system is shown in the table below. Server S3 has started an election and is requesting votes
from the others.
a. Which servers will grant or deny a vote to S3? Justify your reasoning based on the RAFT voting
rules. (4 points)
RAFT Voting Rule: (2 points): A server grants its vote to a candidate if:
●​ The candidate's term is ≥ the server’s term
●​ AND the candidate’s log is at least as up-to-date
Server-by-server analysis: (2 points)
●​
●​
●​
●​
●​

S1: Term 5 > 4 → Candidate's term is outdated → Deny
S2: Term 5 > 4 → Deny
S3: Always votes for itself → Grant
S4: Term 5 > 4 → Deny
S5: Term 6 > 4 → Deny

b. Can S3 become the leader in this election round? Show your vote count and explain. - 2 points
●​ No, S3 has only 1 vote (its own) (1 point)
●​ It needs a majority of 3 votes in a 5-server cluster (1 point)

Server

Current Term

Last Log
Index

Last Log
Term

State

S1

5

10

5

Follower

S2

5

10

5

Follower

S3

4

9

4

Candidate

S4

5

10

5

Follower

S5

6

11

6

Follower

Voted For

### DNP Final 2025.pdf
Name: ____________________________
Group number: ____________________​

[S25] Distributed and Network Programming
Final Exam
1

2

3

4

5

6

7

Total

3

8

8

3

6

6

6

40

1.​ Consider a system with two producers and one consumer. Producers generate
random data and put it into the queue at some rate. If the queue is full, they
block until the consumer processes some items. Consumers process items as
soon as they become available in the queue. If the queue is empty, they block
until new items are added by the producers. (3 points)​
a.​ Draw a diagram of the system showing the components and their
interactions (2 pts)​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
b.​ Consider production rate (for one producer) is 2 items/sec and consumption
rate (for one consumer) is 1 item/sec. How many consumers are needed (at
least) to have 0 buffering time in the system? (1pt)

Name: ____________________________
Group number: ____________________​

2.​ Identify and describe the three main types of assumptions made in a
distributed system model. For each type, provide three concrete examples.​
a.​ Three main assumptions with examples (6 pts)​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
b.​ Explain why defining these assumptions is critical before designing a
distributed algorithm (2 pts)

Name: ____________________________
Group number: ____________________​

3.​ You are given a Chord overlay with m=5, so the identifier space goes from 0 to
31. The nodes in t1he system are located at identifiers [2, 13, 16, 27]. For each
node, build its finger table (5 entries). For each entry, indicate the node's
successor for the corresponding finger interval. Clearly show how you calculate
each entry. Partial credit will be given for correct logic even if your final answer
is not fully accurate.

Name: ____________________________
Group number: ____________________​

4.​ You are designing a fault-tolerant service using redundancy. Each individual
system has a 3% chance of failing (i.e., 97% uptime), and failures are
independent. You replicate the service across three systems, and the service
will remain available as long as at least one system is working. What is the
expected uptime of the overall system? Explain your calculation.

Name: ____________________________
Group number: ____________________​

5.​ Explain what super-peer networks are in the context of peer-to-peer (P2P)
systems. Compare them with pure P2P architectures. Provide at least one
advantage and one disadvantage of using super-peer networks.

Name: ____________________________
Group number: ____________________​

6.​ Compare Cristian’s algorithm and the Berkeley algorithm for clock
synchronization in distributed systems. Describe the steps for each of them. In
what scenarios would each be preferable?

Name: ____________________________
Group number: ____________________​

7.​ You are observing a RAFT cluster of 5 servers: S1 to S5. The current state of the
system is shown in the table below. Server S3 has started an election and is
requesting votes from the others.
Server

Term

Last Log Index

Last Log Term

Status

S1

5

10

5

Follower

S2

5

10

5

Follower

S3

4

9

4

Candidate

S4

5

10

5

Follower

S5

6

11

6

Follower

Votes for

a.​ Which servers will grant or deny a vote to S3? Justify your reasoning based
on the RAFT voting rules (4 pts)​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
​
b.​ Can S3 become the leader in this election round? Show your vote count and
explain (2 pts)

## 2021: Final

Files: [DNP Final 1 2021.pdf](https://glebpopov.notion.site/14ee746cceef8059a413f5b454981f59)


Distributed and Network Programming – Final Review Questions
1. What are the two major reasons to make the system distributed? Explain each reason (L1, S10)
▪
▪

They are inherently distributed since they utilize network (a distributed system) for
communication.
For better performance (nodes collaborate on solving tasks), reliability (if one node is down,
system is still functional), and for solving big tasks.

2. Discuss UDP and TCP protocols, their pros and cons, and when using one is preferred over the
other (L3, S5)
▪
▪
▪

TCP: connection-oriented, reliable, ordered, slower than UDP, easier application development.
UDP: connection-less, unreliable (reliability implemented in app), unordered, faster than TCP.
TCP is preferred for systems where information loss is not tolerated (e.g., file transfer), while UDP
for systems where speed is more important (e.g., video streaming)

3. Given the chord overlay with 𝒎 = 𝟓 and nodes [𝟐, 𝟕, 𝟏𝟏, 𝟏𝟕, 𝟐𝟐, 𝟐𝟕], build the finger table for
each of the nodes for 𝒔 = 𝒎

for id in [2,7,11,17,22,27]:
for i in [1..s]:
ft[id] ∪= succ((id+2**(i-1)) % 2**m)

4. Given the chord overlay and the finger tables (as above), find how
the following lookup requests are routed?
a. lookup(20) at node 2: 2 → 11 → 17 → 22
b. lookup(5) at node 27: 27 → 2 → 7
*if not me then if not succ then forward request to lower_bound

5. Explain what is the problem of mutual exclusion in distributed systems and name the two basic
solutions with their brief descriptions. (L7, S16)
•
•
•

A number of processes in a distributed system want exclusive access to some resource.
Permission-based algorithms: a process is responsible for controlling access (by giving
permissions) to the resource.
Token-based algorithms: a token is passed between processes, the one holding the token can access
the resource, or pass if it doesn’t need.

6. Describe the centralized permission-based algorithm for mutual exclusion and name one
advantage and one disadvantage. (L8, S3-4)
•
•
•

Resources require coordinator permission whenever they access the resource.
Pros: simple, guaranteed correctness, fair (first to request gets), no starvation.
Cons: single point of failure, silent failure of coordinator, performance bottleneck.

7. Describe the Bully algorithm for election. (L8, S17-18)
•
•

•

Assign ids to processes, the available process with the highest 𝑖𝑑 is the coordinator.
Whenever 𝑃𝑖 detects that the coordinator is down, it sends ELECTION to all processes with
higher-ids.
o If any replied, it becomes the coordinator and informs all others.
o Otherwise, 𝑃𝑖 becomes the coordinator.
Whenever a process recovers, it holds an election.

8. Explain the three approaches of update propagation in replica management. (L10, S11)
•
•
•

Propagate an update notification (low bandwidth usage, used when ratio updates/reads is high)
Propagate the actual data (high bandwidth usage, used when ratio updates/reads is low)
Propagate update operation (efficient bandwidth usage, used when update is not complex)

9. Describe Primary-backup protocol, its one advantage and disadvantage. (L10, S18-19)
•
•
•

All writes are sent to a primary server to update its version, propagate changes for read-only in all
replicas, then return to the initiator process.
Pros: highly fault-tolerant, writes are globally ordered.
Cons: updates are blocking (long delays before returning)

10. Describe Primary-backup protocol with local writes, and its advantage over Primary-backup
protocol. (L10, S21)
•
•

When writing to a data item 𝑥 at one server, that server becomes the primary location for 𝑥 and
informs all others, in other words, it moves the primary copy to its own location.
Pros: good for successive writes to one location.

11. Describe three redundancy techniques for failure masking (L11, S12)
•
•
•

Information redundancy: adding extra bits of information used for error recovery.
Time redundancy: design systems that retry on failure.
Physical redundancy: keeping redundant servers for failure recovery.

12. Describe the general model for failure detection? (L12, S7)
•

Each process has a failure detection module, it probes other processes, it they react, they are alive,
otherwise, a failure is suspected.

13. Explain basic reliable multicasting (L13, S7)
•

Each message has a sequence number, if a process received a message with a sequence number it
was not expecting, it requests retransmission.

14. Explain the authentication and authorization and the difference between them (L14, S8)
•
•
•

Identification: user claims an identity.
Authentication: user proves their identity through some mechanism (password, fingerprint, etc).
Authorization: user gets certain privileges or access to a specific set of resources/services based
on their proven identity.

15. Explain three properties of good cryptography algorithm (just one sentence for each) (L14, S11)
•
•
•

Ciphertext should look random.
Impossible to get plaintext from ciphertext without key.
Key has to be long enough to make brute-forcing infeasible.

16. Describe the token-ring algorithm, it’s advantages and disadvantages (L8, S8-9)
•
•
•
•

Organize processes in a logical ring, and let a token be passed between them.
Each process knows its successor. The one holding the token is allowed to enter the critical region
(use the resource if it wants to).
After it has finished, it passes the token along the ring.
It is not permitted to immediately enter the resource again using the same token.

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)

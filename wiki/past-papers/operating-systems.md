---
type: page
title: "Past exam papers: Operating Systems"
description: "Past exams and tests of Operating Systems at Innopolis University (8 papers, 2016–2020), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "operating-systems"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "Operating Systems"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: Operating Systems

Exams and tests of **Operating Systems** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2020: Pre Final

Files: [the row](https://glebpopov.notion.site/14ae746cceef8073801ade819f8dd583)

## 2019: Final

Files: [the row](https://glebpopov.notion.site/14ae746cceef8089aec2c748701d7e03)

## 2018: Final

Files: [the row](https://glebpopov.notion.site/14ee746cceef8083aa51d662939d2a88)

## 2017: Final

Files: [OS Final 2017.pdf](https://glebpopov.notion.site/cf931ade286a47b9b4e91936541ccfc1)


Innopolis University, Academic Year 2017/2018
Written Exam of Operating Systems
6th December 2017
Questions and Solutions
Max 20 points + 6 points (30%) extra credit – Total time: 90 minutes
1. (3 points) Is there any reason why you might want to mount a file system on a nonempty
directory? If so, what is it??
Mounting a file system makes any files already in the mount-point directory inaccessible, so
mount points are normally empty. Howev er, a system administrator might want to copy some of
the most important files normally located in the mounted directory to the mount point so they
could be found in their normal path in an emergency when the mounted device was being
repaired.
2. (3 points) Multiple jobs can run in parallel and finish faster than if they had run
sequentially. Suppose that two jobs, each needing 20 minutes of CPU time, start
simultaneously. How long will the last one take to complete if they run sequentially? How long
if they run in parallel? Assume 50% I/O wait.
If each job has 50% I/O wait, then it will take 40 minutes to complete in the absence of
competition. If run sequentially, the second one will finish 80 minutes after the first one starts.
With two jobs, the approximate CPU utilization is 1 − 0. 52. Thus, each one gets 0.375 CPU
minute per minute of real time. To accumulate 20 minutes of CPU time, a job must run for
20/0.375 minutes, or about 53.33 minutes. Thus running sequentially the jobs finish after 80
minutes, but running in parallel they finish after 53.33 minutes.
3. (3 points) What is the biggest advantage of implementing threads in user space? What is
the biggest disadvantage?
The biggest advantage is the efficiency. No traps to the kernel are needed to switch threads. The
biggest disadvantage is that if one thread blocks, the entire process blocks..
4. (3 points) A machine has a 32-bit address space and an 8-KB page. The page table is
entirely in hardware, with one 32-bit word per entry. When a process starts, the page table is
copied to the hardware from memory, at one word every 100 nsec. If each process runs for
100 msec (including the time to load the page table), what fraction of the CPU time is devoted
to loading the page tables?.
The page table contains 232/213 entries, which is 524,288. Loading the page table takes 52 msec.
If a process gets 100 msec, this consists of 52 msec for loading the page table and 48 msec for
running. Thus 52% of the time is spent loading page tables.
5. (3 points) Suppose that a machine has 48-bit virtual addresses and 32-bit physical
addresses.
(a) If pages are 4 KB, how many entries are in the page table if it has only a single level?
Explain.
(b) Suppose this same system has a TLB (Translation Lookaside Buffer) with 32 entries.
Furthermore, suppose that a program contains instructions that fit into one page and it
sequentially reads long integer elements from an array that spans thousands of pages.
How effective will the TLB be for this case?

OS Exam

Page 1 of 2

Under these circumstances:
(a) We need one entry for each page, or 224 = 16 × 1024 × 1024 entries, since there are 36 =
48 − 12 bits in the page number field.
(b) Instruction addresses will hit 100% in the TLB. The data pages will have a 100 hit rate
until the program has moved onto the next data page. Since a 4-KB page contains 1,024
long integers, there will be one TLB miss and one extra memory access for every 1,024
data references..
6. (3 points) Suppose that there is a resource deadlock in a system. Give an example to show
that the set of processes deadlocked can include processes that are not in the circular chain in
the corresponding resource allocation graph.?
Consider three processes, A, B and C and two resources R and S. Suppose A is waiting for I that is
held by B, B is waiting for S held by A, and C is waiting for R held by A. All three processes, A, B
and C are deadlocked. However, only A and B belong to the circular chain..
7. (30% extra credit)
The banker’s algorithm is being run in a system with m resource classes and n processes. In
the limit of large m and n , the number of operations that must be performed to check a state
for safety is proportional to manb . What are the values of a and b ?
Comparing a row in the matrix to the vector of available resources takes m operations. This step
must be repeated on the order of n times to find a process that can finish and be marked as done.
Thus, marking a process as done takes on the order of mn steps. Repeating the algorithm for all
n processes means that the number of steps is then mn2. Thus, a = 1 and b = 2.
This is the end of the questions and solutions of the exam.

OS Exam

Page 2 of 2

## 2017: Retake 1

Files: [OS Retake 1 2017.pdf](https://glebpopov.notion.site/e0d56d1b720b40feaf25ae7e0f00d9fa)


Innopolis University, Academic Year 2017/2018
First Retake of Operating Systems – 18th December 2017
Max 20 points + 6 points (~30%) extra credit – Total time: 90 minutes
1. (3 points) Why is the process table needed in a timesharing system? Is it also needed in personal
computer systems running UNIX or Windows with a single user?
The process table is needed to store the state of a process that is currently suspended, either ready or
blocked. Modern personal computer systems have dozens of processes running even when the user is
doing nothing and no programs are open. They are checking for updates, loading email, and many
other things, On a UNIX system, use the ps -a command to see them. On a Windows system, use the task
manager.
2. (4 points) Measurements of a certain system have shown that the average process runs for a
time T before blocking on I/O. A process switch requires a time S , which is effectively wasted
(overhead). For round-robin scheduling with quantum Q , give a formula for the CPU efficiency for
each of the following: (a) Q = ∞, (b) Q > T, (c) S < Q < T, (d) Q = S, (e) Q nearly 0
The CPU efficiency is the useful CPU time divided by the total CPU time. When Q ≥ T, the basic cycle is
for the process to run for T and undergo a process switch for S. Thus, (a) and (b) have an efficiency of
T/(S + T). When the quantum is shorter than T, each run of T will require T/Q process switches,
wasting a time ST/Q. The efficiency here is then
T / (T + ST/Q)
which reduces to Q/(Q + S), which is the answer to (c). For (d), we just substitute Q for S and find that
the efficiency is 50%. Finally, for (e), as Q → 0 the efficiency goes to 0.
3. (4 points) The readers and writers problem can be formulated in several ways with regard to
which category of processes can be started when. Carefully describe three different variations of
the problem, each one favoring (or not favoring) some category of processes. For each variation,
specify what happens when a reader or a writer becomes ready to access the database, and what
happens when a process is finished.?
Variation 1: readers have priority. No writer may start when a reader is active. When a new reader
appears, it may start immediately unless a writer is currently active. When a writer finishes, if readers
are waiting, they are all started, regardless of the presence of waiting writers.
Variation 2: Writers have priority. No reader may start when a writer is waiting. When the last active
process finishes, a writer is started, if there is one; otherwise, all the readers (if any) are started.
Variation 3: symmetric version. When a reader is active, new readers may start immediately. When a
writer finishes, a new writer has priority, if one is waiting. In other words, once we have started
reading, we keep reading until there are no readers left. Similarly, once we have started writing, all
pending writers are allowed to run.
4. (3 points) We consider a program which has the two segments shown below consisting of
instructions in segment 0, and read/write data in segment 1. Segment 0 has read/execute
protection, and segment 1 has just read/write protection. The memory system is a demand paged
virtual memory system with virtual addresses that have a 4-bit page number, and a 10-bit offset.
The page tables and protection are as follows (all numbers in the table are in decimal):

OS First Retake – 18th December 2017

Page 1 of 2

For each of the following cases, either give the real (actual) memory address which results from
dynamic address translation or
identify the type of fault which
occurs (either page or protection
fault):
(a) Fetch from segment 1, page 1,
offset 3,
(b) Store into segment 0, page 0,
offset 16,
(c) Fetch from segment 1, page 4,
offset 28,
(d) Jump to location in segment 1,
page 3, offset 32
Results:

5. (3 points) Consider a file whose size varies between 4 KB and 4 MB during its lifetime. Which of
the three allocation schemes (contiguous, linked and table/indexed) will be most appropriate?
Since the file size changes a lot, contiguous allocation will be inefficient requiring reallocation of disk
space as the file grows in size and compaction of free blocks as the file shrinks in size. Both linked and
table/indexed allocation will be efficient; between the two, table/indexed allocation will be more
efficient for random-access scenarios.
6. (3 points) The performance of a file system depends upon the cache hit rate (fraction of blocks
found in the cache). If it takes 1 msec to satisfy a request from the cache, but 40 msec to satisfy a
request if a disk read is needed, give a formula for the mean time required to satisfy a request if the
hit rate is h . Plot this function for values of h varying from 0 to 1.
The time needed is h + 40 x (1 − h). The plot is just a straight line.
7. (30% extra credit) A typical printed page of text contains 50 lines of 80 characters each. Imagine
that a certain printer can print 6 pages per minute and that the time to write a character to the
printer’s output register is so short it can be ignored. Does it make sense to run this printer using
interrupt-driven I/O if each character printed requires an interrupt that takes 50 μ sec all-in to
service?
The printer prints 50 x 80 x 6 = 24, 000 characters/min, which is 400 characters/sec. Each character
uses 50 μ sec of CPU time for the interrupt, so collectively in each second the interrupt overhead is 20
msec. Using interrupt-driven I/O, the remaining 980 msec of time is available for other work. In other
words, the interrupt overhead costs only 2% of the CPU, which will hardly affect the running program
at all.
This is the end of the questions and solutions of the exam.

OS First Retake – 18th December 2017

Page 2 of 2

## 2017: Retake 2

Files: [OS Retake 2 2017.pdf](https://glebpopov.notion.site/3624a5c370b74ba4867d0ab99a69bd34)


Innopolis University, Academic Year 2017/2018
Second Retake of Operating Systems – 19th January 2018
Max 20 points + 6 points (~30%) extra credit – Total time: 90 minutes
1. (4 points) A 255-GB disk has 65,536 cylinders with 255 sectors per track and 512 bytes per
sector. How many platters and heads does this disk have? Assuming an average cylinder seek time
of 11 ms, average rotational delay of 7 msec and reading rate of 100 MB/sec, calculate the average
time it will take to read 400 KB from one sector.
Number of heads = 255 GB / (65536*255*512) = 16
Number of platters = 16/2 = 8
The time for a read operation to complete is seek time + rotational latency +transfer time. The seek
time is 11 ms, the rotational latency is 7 ms and the transfer time is 4 ms, so the average transfer takes
22 msec.
2. (3 points) When a user program makes a system call to read or write a disk file, it provides an
indication of which file it wants, a pointer to the data buffer, and the count. Control is then
transferred to the operating system, which calls the appropriate driver. Suppose that the driver
starts the disk and terminates until an interrupt occurs. In the case of reading from the disk,
obviously the caller will have to be blocked (because there are no data for it). What about the case
of writing to the disk? Need the caller be blocked awaiting completion of the disk transfer?
Maybe. If the caller gets control back and immediately overwrites the data, when the write finally
occurs, the wrong data will be written. However, if the driver first copies the data to a private buffer
before returning, then the caller can be allowed to continue immediately. Another possibility is to
allow the caller to continue and give it a signal when the buffer may be reused, but this is tricky and
error prone.
3. (4 points) Consider a system in which threads are implemented entirely in user space, with the
run-time system getting a clock interrupt once a second. Suppose that a clock interrupt
occurs while some thread is executing in the run-time system. What problem might occur?
Can you suggest a way to solve it?
It could happen that the runtime system is precisely at the point of blocking or unblocking a thread,
and is busy manipulating the scheduling queues. This would be a very inopportune moment for the
clock interrupt handler to begin inspecting those queues to see if it was time to do thread switching,
since they might be in an inconsistent state. One solution is to set a flag when the runtime system is
entered. The clock handler would see this and set its own flag, then return. When the runtime system
finished, it would check the clock flag, see that a clock interrupt occurred, and now run the clock
handler.
4. (3 points) Synchronization within monitors uses condition variables and two special operations,
wait and signal . A more general form of synchronization would be to have a single primitive,
waituntil , that had an arbitrary Boolean predicate as parameter. Thus, one could say, for example,
waituntil x < 0 or y + z < n
The signal primitive would no longer be needed. This scheme is clearly more general than that of
Hoare or Brinch Hansen, but it is not used. Why not? (Hint : Think about the implementation.)
It is very expensive to implement. Each time any variable that appears in a predicate on which some
process is waiting changes, the run-time system must re-evaluate the predicate to see if the process
can be unblocked. With the Hoare and Brinch Hansen monitors, processes can only be awakened on a
signal primitive.
5. (3 points) You are given the following data about a virtual memory system:
1. The TLB can hold 1024 entries and can be accessed in 1 clock cycle (1 nsec).
2. A page table entry can be found in 100 clock cycles or 100 nsec.
3. The average page replacement time is 6 msec.
If page references are handled by the TLB 99% of the time, and only 0.01% lead to a page fault,
what is the effective address-translation time?
OS Second Retake – 19th January 2019

Page 1 of 2

The chance of a hit is 0.99 for the TLB, 0.0099 for the page table, and 0.0001 for a page fault (i.e., only
1 in 10,000 references will cause a page fault). The effective address translation time in nsec is then:
0. 99 × 1 + 0. 0099 × 100 + 0. 0001 × 6 × 106 ≈ 602 clock cycles.
Note that the effective address translation time is quite high because it is dominated by the page
replacement time even when page faults only occur once in 10,000 references..
6. (3 points) Free disk space can be kept track of using a free list or a bitmap. Disk addresses
require D bits. For a disk with B blocks, F of which are free, state the condition under which the
free list uses less space than the bitmap. For D having the value 16 bits, express your answer as a
percentage of the disk space that must be free.
The bitmap requires B bits. The free list requires DF bits. The free list requires fewer bits if DF < B.
Alternatively, the free list is shorter if F/B < 1/D, where F/B is the fraction of blocks free. For 16-bit
disk addresses, the free list is shorter if 6% or less of the disk is free.
7. (30% extra credit) Consider a magnetic disk consisting of 16 heads and 400 cylinders. This disk
has four 100-cylinder zones with the cylinders in different zones containing 160, 200, 240. And 280
sectors, respectively. Assume that each sector contains 512 bytes, average seek time between
adjacent cylinders is 1 msec, and the disk rotates at 7200 RPM. Calculate the (a) disk capacity, (b)
optimal track skew, and (c) maximum data transfer rate.
Consider,
(a) The capacity of a zone is tracks × cylinders × sectors/cylinder × bytes/sect.
Capacity of zone 1: 16 × 100 × 160 × 512 = 131072000 bytes
Capacity of zone 2: 16 × 100 × 200 × 512 = 163840000 bytes
Capacity of zone 3: 16 × 100 × 240 × 512 = 196608000 bytes
Capacity of zone 4: 16 × 100 × 280 × 512 = 229376000 bytes
Sum = 131072000 + 163840000 + 196608000 + 229376000 = 720896000
(b) A rotation rate of 7200 means there are 120 rotations/sec. In the 1 msec track-to-track seek time,
0.120 of the sectors are covered. In zone 1, the disk head will pass over 0.120 × 160 sectors in 1 msec,
so, optimal track skew for zone 1 is 19.2 sectors. In zone 2, the disk head will pass over 0.120 × 200
sectors in 1 msec, so, optimal track skew for zone 2 is 24 sectors. In zone 3, the disk head will pass over
0.120 × 240 sectors in 1 msec, so, optimal track skew for zone 3 is 28.8 sectors. In zone 4, the disk head
will pass over 0.120 × 280 sectors in 1 msec, so, optimal track skew for zone 3 is 33.6 sectors.
(c) The maximum data transfer rate will be when the cylinders in the outermost zone (zone 4) are
being read/written. In that zone, in one second, 280 sectors are read 120 times. Thus the data rate is
280 × 120 × 512 = 17,203,200 bytes/sec.
This is the end of the questions and solutions of the exam.

OS Second Retake – 19th January 2019

Page 2 of 2

## 2016: Retake 1

Files: [OS Retake 1 2016.pdf](https://glebpopov.notion.site/556bdcf87cf543058acd8bc52f85997c)


Innopolis University, Academic Year 2016/2017
Written Exam of Operating Systems – Retake 1
18th January 2017
Questions and Solutions
Max 20 points + 6 points (30%) extra credit – Total time: 90 minutes
1. (3 points) For each of the following system calls, give a condition that causes it to fail: fork,
exec, and unlink.
Fork can fail if there are no free slots left in the process table (and possibly if there is no memory
or swap space left). Exec can fail if the file name given does not exist or is not a valid executable
file. Unlink can fail if the file to be unlinked does not exist or the calling process does not have the
authority to unlink it.
2. (3 points) A computer has 4 GB of RAM of which the operating system occupies 512 MB.
The processes are all 256 MB (for simplicity) and have the same characteristics. If the goal is
99% CPU utilization, what is the maximum I/O wait that can be tolerated?
There is enough room for 14 processes in memory. If a process has an I/O of p, then the
probability that they are all waiting for I/O is p14. By equating this to 0.01, we get the equation
p14 = 0.01. Solving this, we get p = 0.72, so we can tolerate processes with up to 72% I/O wait.
3. (3 points) Suppose that we have a message-passing system using mailboxes. When sending
to a full mailbox or trying to receive from an empty one, a process does not block. Instead, it
gets an error code back. The process responds to the error code by just trying again, over and
over, until it succeeds. Does this scheme lead to race conditions? Explain.
It does not lead to race conditions (nothing is ever lost), but it is effectively busy waiting.
4. (3 points) Suppose that a machine has 48-bit virtual addresses and 32-bit physical
addresses.
a) If pages are 4 KB, how many entries are in the page table if it has only a single level?
Explain.
b) Suppose this same system has a TLB (Translation Lookaside Buffer) with 32 entries.
Furthermore, suppose that a program contains instructions that fit into one page and it
sequentially reads long integer elements from an array that spans thousands of pages.
How effective will the TLB be for this case?
Under these circumstances:
a) We need one entry for each page, or 224 = 16 × 1024 × 1024 entries, since there are 36 =
48 − 12 bits in the page number field.
b) Instruction addresses will hit 100% in the TLB. The data pages will have a 100 hit rate
until the program has moved onto the next data page. Since a 4-KB page contains 1,024
long integers, there will be one TLB miss and one extra memory access for every 1,024
data references..
5. (3 points) Given a disk-block size of 4 KB and block-pointer address value of 4 bytes, what
is the largest file size (in bytes) that can be accessed using 10 direct addresses and one
indirect block?
The indirect block can hold 1024 addresses. Added to the 10 direct addresses, there are 1034
addresses in all. Since each one points to a 4-KB disk block, the largest file is 4,235,264 bytes.

OS Exam

Page 1 of 2

6. (3 points) In order to control traffic, a network router, A periodically sends a message to its
neighbor, B, telling it to increase or decrease the number of packets that it can handle. At
some point in time, Router A is flooded with traffic and sends B a message telling it to cease
sending traffic. It does this by specifying that the number of bytes B may send (A’s window
size) is 0. As traffic surges decrease, A sends a new message, telling B to restart transmission.
It does this by increasing the window size from 0 to a positive number. That message is lost.
As described, neither side will ever transmit. What type of deadlock is this?
This is clearly a communication deadlock, and can be controlled by having A time out and
retransmit its enabling message (the one that increases the window size) after some period of
time (a heuristic). It is possible, however, that B has received both the original and the duplicate
message. No harm will occur if the update on the window size is given as an absolute value and
not as a differential. Sequence numbers on such messages are also effective to detect duplicates..
7. (30% extra credit)
A bitmap terminal contains 1600 by 1200 pixels. To scroll a window, the CPU (or controller)
must move all the lines of text upward by copying their bits from one part of the video RAM to
another. If a particular window is 80 lines high by 80 characters wide (6400 characters, total),
and a character’s box is 8 pixels wide by 16 pixels high, how long does it take to scroll the
whole window at a copying rate of 50 nsec per byte? If all lines are 80 characters long, what is
the equivalent baud rate of the terminal? Putting a character on the screen takes 5 μsec. How
many lines per second can be dis- played?
Scrolling the window requires copying 79 lines of 80 characters or 6320 characters. Copying 1
character (16 bytes) takes 800 nsec, so the whole window takes 5.056 msec. Writing 80
characters to the screen takes 400 nsec, so scrolling and displaying a new line take 5.456 msec.
This gives about 183.2 lines/sec.
This is the end of the questions and solutions of the exam.

OS Exam

Page 2 of 2

## 2016: Retake 2

Files: [OS Retake 2.2 2016.pdf, OS Retake 2.1 2016.pdf](https://glebpopov.notion.site/ead26fb60794436a975bf35a0c0acb94)

### OS Retake 2.2 2016.pdf
Innopolis University, Academic Year 2016/2017
Written Exam of Operating Systems – Retake 2
7th February 2017
Questions and Solutions
Max 20 points + 6 points (30%) extra credit – Total time: 90 minutes
1. (3 points) Is there any reason why you might want to mount a file system on a nonempty
direc- tory? If so, what is it??
Mounting a file system makes any files already in the mount-point directory inaccessible, so
mount points are normally empty. However, a system administrator might want to copy some of
the most important files normally located in the mounted directory to the mount point so they
could be found in their nor- mal path in an emergency when the mounted device was being
repaired.
2. (3 points) Consider a real-time system with two voice calls of periodicity 5 msec each with
CPU time per call of 1 msec, and one video stream of periodicity 33 ms with CPU time per call
of 11 msec. Is this system schedulable?
Each voice call needs 200 samples of 1 msec or 200 msec. Together they use 400 msec of CPU
time. The video needs 11 msec 33 1/3 times a second for a total of about 367 msec. The sum is
767 msec per second of real time so the system is schedulable.
3. (3 points) Measurements of a certain system have shown that the average process runs for
a time T before blocking on I/O. A process switch requires a time S, which is effectively
wasted (overhead). For round-robin scheduling with quantum Q, give a formula for the CPU
efficiency for each of the following:
(a) Q = ∞
(b) Q > T
(c) S < Q < T (d) Q = S
(e) Q nearly 0
The CPU efficiency is the useful CPU time divided by the total CPU time. When Q ≥ T , the basic
cycle is for the process to run for T and undergo a process switch for S. Thus, (a) and (b) have an
efficiency of T /(S + T ). When the quantum is shorter than T, each run of T will require T /Q
process switches, wasting a time ST /Q. The efficiency here is then(T/(T + ST/Q))
4. (3 points) Consider the following C program:
int X[N];
int step = M; /* M is some predefined constant */
for (int i = 0; i < N; i += step) X[i] = X[i] + 1;
(a) If this program is run on a machine with a 4-KB page size and 64-entry TLB, what values of
M and N will cause a TLB miss for every execution of the inner loop?
(b) Would your answer in part (a) be different if the loop were repeated many times?
Explain.
For these sizes:
(a) M has to be at least 4096 to ensure a TLB miss for every access to an element of X. Since N
affects only how many times X is accessed, any value of N will do.
(b) M should still be at least 4,096 to ensure a TLB miss for every access to an element of X. But
now N should be greater than 64K to thrash the TLB, that is, X should exceed 256 KB.

OS Exam

Page 1 of 2

5. (3 points) A certain file system uses 4-KB disk blocks. The median file size is 1 KB. If all files
were exactly 1 KB, what fraction of the disk space would be wasted? Do you think the wastage
for a real file system will be higher than this number or lower than it? Explain your answer.
If all files were 1 KB, then each 4-KB block would contain one file and 3 KB of wasted space.
Trying to put two files in a block is not allowed because the unit used to keep track of data is the
block, not the semiblock. This leads to 75% wasted space. In practice, every file system has large
files as well as many small ones, and these files use the disk much more efficiently. For ex- ample,
a 32,769-byte file would use 9 disk blocks for storage, given a space efficiency of 32,769/36,864,
which is about 89%.
6. (3 points) A distributed system using mailboxes has two IPC primitives, send and receive.
The latter primitive specifies a process to receive from and blocks if no message from that
process is available, even though messages may be waiting from other processes. There are
no shared resources, but processes need to communicate frequently about other matters. Is
deadlock possible? Discuss.
Yes. Suppose that all the mailboxes are empty. Now A sends to B and waits for a reply, B sends to
C and waits for a reply, and C sends to A and waits for a reply. All the conditions for a
communications deadlock are now fulfilled.
7. (30% extra credit)
(a) Describe a situation in which balloon drivers do not work.
(b) A thin-client terminal is used to display a Web page containing an animated cartoon of size
400 pixels × 160 pixels running at 10 frames/sec. What fraction of a 100-Mbps Fast Ethernet
is consumed by displaying the cartoon?
(a) Balloon drivers do not work if the hypervisor does not know anything about the guest
operating systems running on its virtual machines. It also does not work if there is no way to
include a balloon driver in them, for example, if they do not support loadable drivers and the
source code is not available so they cannot be recompiled to include the balloon driver..
(b) The display size is 400 × 160 × 3 bytes, which is 192,000 bytes. At 10 fps this is 1,920,000
bytes/sec or 15,360,000 bits/sec. This consumes 15% of the Fast Ethernet.
This is the end of the questions and solutions of the exam.

OS Exam

Page 2 of 2

### OS Retake 2.1 2016.pdf
Innopolis University, Academic Year 2016/2017
Written Exam of Operating Systems – Retake 2
27th January 2017
Questions and Solutions
Max 20 points + 6 points (30%) extra credit – Total time: 90 minutes
1. (3 points) What type of multiplexing (time, space, or both) can be used for sharing the
following resources: CPU, memory, disk, network card, printer, keyboard, and display?
Time multiplexing: CPU, network card, printer, keyboard. Space multiplexing: memory, disk.
Both: display.
2. (3 points) Multiple jobs can run in parallel and finish faster than if they had run
sequentially. Suppose that two jobs, each needing 20 minutes of CPU time, start
simultaneously. How long will the last one take to complete if they run sequentially? How long
if they run in parallel? Assume 50% I/O wait.
If each job has 50% I/O wait, then it will take 40 minutes to complete in the absence of
competition. If run sequentially, the second one will finish 80 minutes after the first one starts.
With two jobs, the approximate CPU utilization is 1 − 0. 52. Thus, each one gets 0.375 CPU
minute per minute of real time. To accumulate 20 minutes of CPU time, a job must run for
20/0.375 minutes, or about 53.33 minutes. Thus running sequentially the jobs finish after 80
minutes, but running in parallel they finish after 53.33 minutes.
3. (3 points) Five batch jobs. A through E, arrive at a computer center at almost the same time.
They have estimated running times of 10, 6, 2, 4, and 8 minutes. Their (externally determined)
priorities are 3, 5, 2, 1, and 4, respectively, with 5 being the highest priority. For each of the
following scheduling algorithms, determine the mean process turnaround time. Ignore
process switching overhead.
(a) Round robin.
(b) Priority scheduling.
(c) First-come, first-served (run in order 10, 6, 2, 4, 8).
(d) Shortest job first.
For (a), assume that the system is multi-programmed, and that each job gets its fair share of
the CPU. For (b) through (d), assume that only one job at a time runs, until it finishes. All jobs
are completely CPU bound.
For round robin, during the first 10 minutes each job gets 1/5 of the CPU. At the end of 10
minutes, C finishes. During the next 8 minutes, each job gets 1/4 of the CPU, after which time D
finishes. Then each of the three remaining jobs gets 1/3 of the CPU for 6 minutes, until B finishes,
and so on. The finishing times for the five jobs are 10, 18, 24, 28, and 30, for an average of 22
minutes. For priority scheduling, B is run first. After 6 minutes it is finished. The other jobs finish
at 14, 24, 26, and 30, for an average of 18.8 minutes. If the jobs run in the order A through E, they
finish at 10, 16, 18, 22, and 30, for an average of 19.2 minutes. Finally, shortest job first yields
finishing times of 2, 6, 12, 20, and 30, for an average of 14 minutes.
4. (3 points) A computer provides each process with 65,536 bytes of address space divided
into pages of 4096 bytes each. A particular program has a text size of 32,768 bytes, a data size
of 16,386 bytes, and a stack size of 15,870 bytes. Will this program fit in the machine’s
address space? Suppose that instead of 4096 bytes, the page size were 512 bytes, would it
then fit? Each page must contain either text, data, or stack, not a mixture of two or three of
them.
OS Exam

Page 1 of 2

The text is eight pages, the data are five pages, and the stack is four pages. The program does not
fit because it needs 17 4096-byte pages. With a 512-byte page, the situation is different. Here the
text is 64 pages, the data are 33 pages, and the stack is 31 pages, for a total of 128 512-byte
pages, which fits. With the small page size it is OK, but not with the large one.
5. (3 points) Consider a 4-TB disk that uses 4-KB blocks and the free-list method. How many
block addresses can be stored in one block?
The number of blocks on the disk = 4 TB / 4 KB = 230. Thus, each block address can be 32 bits (4
bytes), the nearest power of 2. Thus, each block can store 4 KB / 4 = 1024 addresses.
6. (3 points) The banker’s algorithm is being run in a system with m resource classes and n
processes. In the limit of large m and n, the number of operations that must be performed to
check a state for safety is proportional to manb. What are the values of a and b?
Comparing a row in the matrix to the vector of available resources takes m operations. This step
must be repeated on the order of n times to find a process that can finish and be marked as done.
Thus, marking a process as done takes on the order of mn steps. Repeating the algorithm for all
n processes means that the number of steps is then mn2. Thus, a = 1 and b = 2.
7. (30% extra credit) Suppose that a system uses DMA for data transfer from disk controller
to main memo- ry. Further assume that it takes t1 nsec on average to acquire the bus and t2
nsec to transfer one word over the bus (t1 >> t2). After the CPU has programmed the DMA
controller, how long will it take to transfer 1000 words from the disk controller to main
memory, if (a) word-at-a-time mode is used, (b) burst mode is used? Assume that commanding the disk controller requires acquiring the bus to send one word and acknowl- edging
a transfer also requires acquiring the bus to send one word.
(a) Word-at-a-time mode: 1000 × [(t1 + t2) + (t1 + t2) + (t1 + t2)]
Where the first term is for acquiring the bus and sending the command to the disk controller, the
second term is for transferring the word, and the third term is for the acknowledgement. All in
all, a total of 3000 × (t1 + t2) nsec.
(b) Burst mode: (t1 + t2) + t1 + 1000 times t2 + (t1 + t2)
where the first term is for acquiring the bus and sending the command to the disk controller, the
second term is for the disk controller to acquire the bus, the third term is for the burst transfer,
and the fourth term is for acquiring the bus and doing the acknowledgement. All in all, a total of
3t1 + 1002t2.
This is the end of the questions and solutions of the exam.

OS Exam

Page 2 of 2

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)

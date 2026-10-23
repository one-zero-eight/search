---
type: course
title: "BSTE: Advanced Linux"
description: "Course covering Linux kernel principles, booting, device drivers, memory management, and system programming."
resource: "https://eduwiki.innopolis.university/index.php/BSTE%3A_Advanced_Linux"
tags: ["linux", "kernel", "course", "programming", "operating-systems"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSTE%3A_Advanced_Linux"
    id: "7906"
    title: "BSTE: Advanced Linux"
    last_modified: "2022-11-25T12:17:34Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T02:01:21+00:00"
status: draft
stale_after: "2024-11-24T12:17:34+00:00"
prerequisite_of: ["/courses/msc-classical-internet-applications.md", "/courses/msc-inter-networking-and-routing.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSTE: Advanced Linux

## Advanced Linux: Understanding and programming
- **Course name**: Advanced Linux: Understanding and programming
- **Code discipline**: xxxxx
- **Subject area**: 

### Short Description
This course covers the following concepts: • The fundamental principles for `booting`; • Linux Kernel: understanding, programming, debugging, contributing; • Device drivers; • Power management; • Graphical stack overview; • Userspace: understating and interaction with Kernel.

### Prerequisites

#### Prerequisite subjects


#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| X86/Arm assembler introduction | # • Basic assembler: registers, operations <br> # • x86 ABI reference <br> # • Context switching <br> # • CPU security rings |
| Linux Kernel introduction | # • Kernel usage <br> # • Supported HW <br> # • Building the kernel |
| Booting the Kernel | # • Boot Sequence <br> # • Device Tree <br> # • U-boot <br> # • initrd/initramfs |
| Kernel Modules | # • Linux device and driver m​odel <br> # • Virtual Filesystems |
| Memory management | # • Physical Memory <br> # • Virtual Memory <br> # • Memory Allocation |
| Threads, processes and scheduling | # • Thread <br> # • Processes <br> # • Timers |
| Concurrent access to resources | # • Mutexes <br> # • Spin locks <br> # • RW-locks |
| Kernel debugging | # • Debugging techniques <br> # • DebugFS <br> # • Other methods overview (J-Tag etc). |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The main purpose of this course is to give the students advanced knowledge of how Linux operation system boots, works and what parts it is consists of.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- • Principles of Operating Systems.
- • Principles of bootloaders (first- /second- stage).
- • Linux booting principles.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- • Memory management in Kernel and userspace.
- • Linux kernel subsustems.
- • Concurrent access to resources.
- • HW devices interaction in Linux.
- • Interrupt and multithreading execution.
- • Real- and virtual- filesystems interaction.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- • Kernel drivers design skills.
- • Linux Kernel contribution and advanced GIT knowledge.
- • C language low-level Kernel programming.
- • C/C++ language system programming.
- • POSIX API usage.
- • Kernel and userspace debugging (including KGDB/GDB).
- • x86/ARM assembly programming. 
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
| Labs/seminar classes | 40 |
| Interim performance assessment | 10 |
| Exams | 50 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- • Writing Kernel Module: i2c -
- • Fundamental Linux Kernel programming by Krishenko V.A., Rayzanova N.U. -  /
- • Linux Operating System by Kuryachiy G.V., Malinskiy K.A. -
- • Systemd after 10 years, historical and techical review, -
- • Evolution of Linux Kernel by Novikov E.M., -
- • Online resources shared by instructor

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 | Section 5 | Section 6 | Section 7 | Section 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Homework and group projects | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 |
| Midterm evaluation | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | 1. ARM architecture is faster than x86, itn’s it? | 1 |
| Question | 2. Why does antivirus software works in RING0? | 1 |
| Question | 3. What is the main purpose of having interrupts? | 1 |
| Question | 4. How-to debug anything inside interrupt context? | 1 |
| Question | 1. Show the difference in x86 and ARM CPU registers. | 0 |
| Question | 2. Create `basic` atomic operations for ARM in x86 (and vice versa). | 0 |
| Question | 3. Implement simple context switching without threads. | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | 1. Monolithic kernel vs Micro-kernel. What is faster and why? | 1 |
| Question | 2. How Linux works on HW without IOMMU? | 1 |
| Question | 3. Tools required for building Linux Kernel. | 1 |
| Question | 4. Name few operations systems bases on Linux and name the difference. | 1 |
| Question | 1. Contributing to Open Source software and Kernel. What is the difference? | 0 |
| Question | 2. Git usage: commits, email-patches. | 0 |
| Question | 3. Git usage: rewriting history. | 0 |
| Question | 4. Building Linux Kernel for your own PC. | 0 |
| Question | 5. Running new Kernel on your machine. | 0 |
| Question | 6. Kernel config file location and editing. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | 1. What is the difference between BIOS and UEFI? What we prefer in nowadays? | 1 |
| Question | 2. What is the usage for secure boot? What requirements should be met for this? | 1 |
| Question | 3. Why in x86 we do not have device tree? And why is it required for ARM platforms? | 1 |
| Question | 4. What is the purpose of having initramfs? Can we skip that stage? | 1 |
| Question | 1. Build U-boot | 0 |
| Question | 2. Rebuilding initramfs | 0 |
| Question | 3. Changing boot order of your PC. Creating simple systemd service. | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | 1. How kernel module can be compiled and used inside or outside Linux Kernel Image? | 1 |
| Question | 2. What is the purpose of System.map file for correct Linux Kernel functionality? | 1 |
| Question | 3. What is the real requirement to have virtual filesystems in Linux Kernel? | 1 |
| Question | 4. Name few real and virtual filesystems. Briefly describe usage in real life. | 1 |
| Question | 1. Develop and deploy simple Kernel Module outside kernel image. Dynamic Loading. | 0 |
| Question | 2. Develop and deploy simple Kernel Module inside kernel image. | 0 |
| Question | 3. SysFS/ DebugFS / ProcFS/ TmpFS usage | 0 |
##### Section 5
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | 1. Why do we need virtual memory? | 1 |
| Question | 2. Why does Linux Kernel maps itself to every process address space? | 1 |
| Question | 3. How does page fault handler work? | 1 |
| Question | 4. What is segmentation fault and how it handles in Linux Kernel? | 1 |
| Question | 1. Create simple allocator (myalloc/myfree). | 0 |
| Question | 2. Create benchmark for simple allocator. | 0 |
##### Section 6
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | 1. What is the difference between thread and process? | 1 |
| Question | 2. Can process exist without any threads? | 1 |
| Question | 3. What scheduling methods does Linux Kernel has? | 1 |
| Question | 4. What make `realtime` OS really realtime? | 1 |
| Question | 5. What is the difference between cooperative and preemptive multitasking? | 1 |
| Question | 1. Implement your own threads inside app. | 0 |
| Question | 2. Implement simple scheduler for your threading app. | 0 |
| Question | 3. Implement timer for your app without using `real` timers. | 0 |
##### Section 7
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | 1. Why do we need locking structures? | 1 |
| Question | 2. Where is mutex preferred on spinlock? | 1 |
| Question | 3. Where is spinlock preferred on mutex? | 1 |
| Question | 4. Can we just write locking-free code? | 1 |
| Question | 5. What is deadlock and how it could be handled? | 1 |
| Question | 1. Implement simple locking structures. | 0 |
| Question | 2. Implement Wait-die lock. | 0 |
##### Section 8
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | 1. Name and briefly describe kernel-debugging techniques. | 1 |
| Question | 2. What debug levels for printk do you know and what is their usage? | 1 |
| Question | 3. What other methods of Kernel debugging techniques do you know? | 1 |
| Question | 4. Why can’t we use regular GDB to debug Linux Kernel? | 1 |
| Question | 1. Usage of DebugFS for basic debugging | 0 |
| Question | 2. Usage of printk and debug levels. | 0 |
| Question | 3. KGDB usage for Kernel debugging. | 0 |
#### Final assessment
**Section 1**
1. 1. Describe basic CPU registers and their purpose.
1. 2. Describe x86 ABI.
1. 3. What is context switching and how does it work?
1. 4. Name all CPU security rings and describe security levels.
1. 5. Interrupts. Interrupt handler.
**Section 2**
1. 1. Briefly describe modern OS architecture. (for ex. Linux)
1. 2. Describe supported HW by Linux Kernel.
1. 3. Describe contribution process to Linux Kernel.
**Section 3**
1. 1. Name popular bootloaders and briefly describe the difference.
1. 2. Describe all boot sequence starting from pushing START button.
1. 3. Describe in details the role of initrd/initramfs in booting process.
1. 4. First userspace process. Describe how it works and why do we need SystemV/system?
**Section 4**
1. 1. Describe Linux device and driver model
1. 2. Real- and Virtual- filesystems. Describe in details.
1. 3. Name other Linux Kernel subsystems and their usage.
**Section 5**
1. 1. Describe how virtual memory maps on physical memory.
1. 2. Describe in details how TLB works. How TLB increases memory operations?
1. 3. Describe structure of page table, its location and management from OS.
1. 4. Describe memory allocation techniques. Describe one of them in details.
**Section 6**
1. 1. Describe how threading works.
1. 2. Describe pthread API usage.
1. 3. Describe difference between monotomic and realtime clocks.
1. 4. Describe scheduling strategies. Make a suggestion, which one is preferred for different situations.
1. 5. Describe difference in memory management between threads and processes.
**Section 7**
1. 1. Describe mutex internals.
1. 2. Describe spin lock internals.
1. 3. Describe deadlock problem and how it could be handled.
1. 4. Compare different locking methods and make conclusion of which is faster and why.
1. 5. Deeply describe wait-die locks.
**Section 8**
1. 1. Explain usage of debugFS in modern kernels.
1. 2. Describe main kernel debugging techniques.

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

**Section 5**

**Section 6**

**Section 7**

**Section 8**

<!-- catix:relations -->
## Relations

- Required for: [Classical Internet Applications](/courses/msc-classical-internet-applications.md), [Inter-Networking and Routing](/courses/msc-inter-networking-and-routing.md)
<!-- /catix:relations -->

# Citations

1. [BSTE: Advanced Linux](https://eduwiki.innopolis.university/index.php/BSTE%3A_Advanced_Linux), revision 7906

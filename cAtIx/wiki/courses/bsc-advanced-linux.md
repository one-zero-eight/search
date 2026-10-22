---
type: course
title: "Advanced Linux"
description: "A course covering Linux kernel internals, booting, device drivers, debugging, and system programming for advanced students."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Advanced_Linux"
tags: ["linux", "kernel", "systems-programming", "driver-development", "debugging"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Advanced_Linux"
    id: "7575"
    title: "BSc: Advanced Linux"
    last_modified: "2022-09-20T08:25:03Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T02:00:06+00:00"
status: draft
stale_after: "2024-09-19T08:25:03+00:00"
duplicate_of: ["/courses/bste-advanced-linux.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Advanced Linux

## Advanced Linux
- **Course name**: Advanced Linux
- **Code discipline**: xxxxx
- **Subject area**: 

### Short Description
This course covers the following concepts: The fundamental principles for `booting`; Linux Kernel: understanding, programming, debugging, contributing; Device drivers; Power management; Graphical stack overview; Userspace: understating and interaction with Kernel, debugging userspace application and libraries.

### Prerequisites

#### Prerequisite subjects


#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| X86/Arm assembler introduction | # Basic assembler: registers, operations <br> # x86 ABI reference <br> # Context switching <br> # CPU security rings |
| Userspace | # Executable files overview <br> # ELF format <br> # SO format <br> # POSIX API |
| Userspace debugging (GDB) | # Debugging techniques overview <br> # GDB (Gnu debugger) usage <br> # Stack trace <br> # Watchpoints/breakpoints |
| Linux Kernel introduction | # Kernel usage <br> # Supported HW <br> # Building the kernel |
| Booting the Kernel | # Boot Sequence <br> # Device Tree <br> # U-boot <br> # initrd/initramfs |
| Kernel Modules | # Linux device and driver m​odel <br> # Virtual Filesystems |
| Memory management | # Physical Memory <br> # Virtual Memory <br> # Memory Allocation |
| Threads, processes and scheduling | # Thread <br> # Processes <br> # Timers |
| Concurrent access to resources | # Mutexes <br> # Spin locks <br> # RW-locks |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The main purpose of this course is to give the students advanced knowledge of how Linux operation system boots, works and what parts it is consists of.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Principles of Operating Systems.
- Principles of bootloaders (first- /second- stage).
- Linux booting principles.
- Linux Kernel and apps debugging principles.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Memory management in Kernel and userspace.
- Linux kernel subsustems.
- Concurrent access to resources.
- HW devices interaction in Linux.
- Interrupt and multithreading execution.
- Real- and virtual- filesystems interaction.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Kernel drivers design skills.
- Linux Kernel contribution and advanced GIT knowledge.
- C language low-level Kernel programming.
- C/C++ language system programming.
- POSIX API usage.
- Kernel and userspace debugging (including KGDB/GDB).
- x86/ARM assembly programming. 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 100-150 | - |
| B. Good | 80-100 | - |
| C. Satisfactory | 60-79 | - |
| D. Poor | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 100 |
| Interim performance assessment | 0 |
| Exams | 50 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Writing Kernel Module: i2c -
- Fundamental Linux Kernel programming by Krishenko V.A., Rayzanova N.U. -  /
- Linux Operating System by Kuryachiy G.V., Malinskiy K.A. -
- Systemd after 10 years, historical and techical review, -
- Evolution of Linux Kernel by Novikov E.M., -
- Online resources shared by instructor

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 | Section 5 | Section 6 | Section 7 | Section 8 | Section 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Homework and group projects | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| Midterm evaluation | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | ARM architecture is faster than x86, itn’s it? | 1 |
| Question | Why does antivirus software works in RING0? | 1 |
| Question | What is the main purpose of having interrupts? | 1 |
| Question | How-to debug anything inside interrupt context? | 1 |
| Question | Show the difference in x86 and ARM CPU registers. | 0 |
| Question | Create `basic` atomic operations for ARM in x86 (and vice versa). | 0 |
| Question | Implement simple context switching without threads. | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Why can’t we just use .EXE and .DLL files on Linux? | 1 |
| Question | Do .SO files actually share same memory physical addresses? | 1 |
| Question | POSIX vs WinAPI? Which is better from portability point of view? | 1 |
| Question | What is the most secure method for interprocess communication? | 1 |
| Question | What is the fastest method for interprocess communication? | 1 |
| Question | Create simple app for ELF format parsing. | 0 |
| Question | Create app that shows dependencies between .so and executable file. | 0 |
| Question | Create two apps communicating with each other. At least 2 methods. Compare the speed. | 0 |
| Question | Create app with joinable and detachable threads. Check the difference. | 0 |
| Question | Create app that uses fork() and execve() with controlling child process. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is GDB? What platforms can be debugged using GDB? | 1 |
| Question | Do we have any alternatives for GDB? | 1 |
| Question | What should we have related to the app to debug it in GDB? | 1 |
| Question | Name popular GDB front-ends. Check what front-ends for GDB you already use. | 1 |
| Question | What alternatives to GHIDRA do we have for different platforms? | 1 |
| Question | Debug simple app using GDB with symbols in runtime. Use breakpoints and watchpoints and step by step debugging. | 0 |
| Question | Load coredump and debug it in GDB. | 0 |
| Question | Fix few variables in binary file using GHIDRA without source code. | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Monolithic kernel vs Micro-kernel. What is faster and why? | 1 |
| Question | How Linux works on HW without IOMMU? | 1 |
| Question | Tools required for building Linux Kernel. | 1 |
| Question | Name few operations systems bases on Linux and name the difference. | 1 |
| Question | Contributing to Open Source software and Kernel. What is the difference? | 0 |
| Question | Git usage: commits, email-patches. | 0 |
| Question | Git usage: rewriting history. | 0 |
| Question | Building Linux Kernel for your own PC. | 0 |
| Question | Running new Kernel on your machine. | 0 |
| Question | Kernel config file location and editing. | 0 |
##### Section 5
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is the difference between BIOS and UEFI? What we prefer in nowadays? | 1 |
| Question | What is the usage for secure boot? What requirements should be met for this? | 1 |
| Question | Why in x86 we do not have device tree? And why is it required for ARM platforms? | 1 |
| Question | What is the purpose of having initramfs? Can we skip that stage? | 1 |
| Question | Build U-boot | 0 |
| Question | Rebuilding initramfs | 0 |
| Question | Changing boot order of your PC. Creating simple systemd service. | 0 |
##### Section 6
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How kernel module can be compiled and used inside or outside Linux Kernel Image? | 1 |
| Question | What is the purpose of System.map file for correct Linux Kernel functionality? | 1 |
| Question | What is the real requirement to have virtual filesystems in Linux Kernel? | 1 |
| Question | Name few real and virtual filesystems. Briefly describe usage in real life. | 1 |
| Question | Develop and deploy simple Kernel Module outside kernel image. Dynamic Loading. | 0 |
| Question | Develop and deploy simple Kernel Module inside kernel image. | 0 |
| Question | SysFS/ DebugFS / ProcFS/ TmpFS usage | 0 |
##### Section 7
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Why do we need virtual memory? | 1 |
| Question | Why does Linux Kernel maps itself to every process address space? | 1 |
| Question | How does page fault handler work? | 1 |
| Question | What is segmentation fault and how it handles in Linux Kernel? | 1 |
| Question | Create simple allocator (myalloc/myfree). | 0 |
| Question | Create benchmark for simple allocator. | 0 |
##### Section 8
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is the difference between thread and process? | 1 |
| Question | Can process exist without any threads? | 1 |
| Question | What scheduling methods does Linux Kernel has? | 1 |
| Question | What make `realtime` OS really realtime? | 1 |
| Question | What is the difference between cooperative and preemptive multitasking? | 1 |
| Question | Implement your own threads inside app. | 0 |
| Question | Implement simple scheduler for your threading app. | 0 |
| Question | Implement timer for your app without using `real` timers. | 0 |
##### Section 9
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Why do we need locking structures? | 1 |
| Question | Where is mutex preferred on spinlock? | 1 |
| Question | Where is spinlock preferred on mutex? | 1 |
| Question | Can we just write locking-free code? | 1 |
| Question | What is deadlock and how it could be handled? | 1 |
| Question | Implement simple locking structures. | 0 |
| Question | Implement Wait-die lock. | 0 |
#### Final assessment
**Section 1**
1. Describe basic CPU registers and their purpose.
1. Describe x86 ABI.
1. What is context switching and how does it work?
1. Name all CPU security rings and describe security levels.
1. Interrupts. Interrupt handler.
**Section 2**
1. Describe ELF executable format.
1. Describe how Linux processes could be load from ELF file.
1. Describe .SO library loading and their layout in memory.
1. Describe methods of interprocess communication (at least 2).
1. POSIX. Describe network operations.
1. POSIX. Describe pthread library.
1. POSIX. Describe time operations.
1. Describe select(), poll() methods. Name the difference.
1. POSIX. Describe filesystem operations.
**Section 3**
1. GDB. Why do we need to have symbols? Can we debug without them?
1. GDB. Describe debugging techniques only using coredump.
1. GDB. Describe usage or breakpoints and watchpoints.
1. GDB/GDB Server. Remote debugging. Describe how to do that.
1. GDB. Describe multiarch debugging.
1. GDB. Describe how to debug multithreaded application.
1. GDB. Stack trace. Describe usage and how-to.
1. GHIDRA. Describe usage flow.
**Section 4**
1. Briefly describe modern OS architecture. (for ex. Linux)
1. Describe supported HW by Linux Kernel.
1. Describe contribution process to Linux Kernel.
**Section 5**
1. Name popular bootloaders and briefly describe the difference.
1. Describe all boot sequence starting from pushing START button.
1. Describe in details the role of initrd/initramfs in booting process.
1. First userspace process. Describe how it works and why do we need SystemV/system?
**Section 6**
1. Describe Linux device and driver model
1. Real- and Virtual- filesystems. Describe in details.
1. Name other Linux Kernel subsystems and their usage.
**Section 7**
1. Describe how virtual memory maps on physical memory.
1. Describe in details how TLB works. How TLB increases memory operations?
1. Describe structure of page table, its location and management from OS.
1. Describe memory allocation techniques. Describe one of them in details.
**Section 8**
1. Describe how threading works.
1. Describe pthread API usage.
1. Describe difference between monotomic and realtime clocks.
1. Describe scheduling strategies. Make a suggestion, which one is preferred for different situations.
1. Describe difference in memory management between threads and processes.
**Section 9**
1. Describe mutex internals.
1. Describe spin lock internals.
1. Describe deadlock problem and how it could be handled.
1. Compare different locking methods and make conclusion of which is faster and why.
1. Deeply describe wait-die locks.
1. P.1.2.10 Section 10
1. Section title: Kernel debugging
1. Topics covered in this section:
1. Debugging techniques
1. DebugFS
1. Other methods overview (J-Tag etc).
1. KGDB
1. What forms of evaluation were used to test students’ performance in this section?
1. Typical questions for ongoing performance evaluation within this section
1. Name and briefly describe kernel-debugging techniques.
1. What debug levels for printk do you know and what is their usage?
1. What other methods of Kernel debugging techniques do you know?
1. Why can’t we use regular GDB to debug Linux Kernel?
1. Typical questions for seminar classes (labs) within this section
1. Usage of DebugFS for basic debugging
1. Usage of printk and debug levels.
1. KGDB usage for Kernel debugging.
1. Test questions for final assessment in this section
1. Explain usage of debugFS in modern kernels.
1. Describe main kernel debugging techniques.
1. P.1.2.11 Section 11
1. Section title: HW busses
1. Topics covered in this section:
1. GPIO
1. UART
1. i2c
1. spi
1. pin muxing
1. DMA
1. What forms of evaluation were used to test students’ performance in this section?
1. Typical questions for ongoing performance evaluation within this section
1. What HW bus type should we prefer for flash memory?
1. What bus is the fastest?
1. What should we do if we don’t have enough available pins for our needs?
1. Can spi devices be connected in parallel? How can we do that?
1. DMA – overkill technique or our current basic needs? Briefly review advantages and disadvantages of DMA.
1. Typical questions for seminar classes (labs) within this section
1. Implement connection to other device using UART. Exchange data.
1. Note: additional tasks will be given depends on current HW availability.
1. Test questions for final assessment in this section
1. Describe i2c bus. Usage of i2c bus.
1. Describe spi bus. Usage of spi bus.
1. Describe GPIO subsystem. Usage of GPIO.
1. Describe pin muxing.
1. Describe usage of DMA and consider exchange speed with and without DMA.
1. P.1.2.12 Section 12
1. Section title: PCI
1. Topics covered in this section:
1. PCI Physical parameters
1. PCI Electrical parameters
1. PCI Logical model
1. PCI Configuration
1. What forms of evaluation were used to test students’ performance in this section?
1. Typical questions for ongoing performance evaluation within this section
1. Briefly describe PCI specification.
1. What is difference between PCI and PCIe?
1. Name devices that could be connected to PC using PCI bus.
1. Device tree and PCI. Briefly describe how we can configure them.
1. Typical questions for seminar classes (labs) within this section
1. Measure PCI Ex bus speed with different connection types: x1, x2, x4 and x16.
1. Test questions for final assessment in this section
1. Describe parameters of PCI bus interface.
1. Describe usage of PCI bus in modern PC/laptop.
1. Describe configuration and enumeration of devices on PCI bus.
1. P.1.2.13 Section 13
1. Section title: USB
1. Topics covered in this section:
1. USB Physical parameters
1. USB Electrical parameters
1. USB Logical model
1. USB Configuration and enumeration
1. What forms of evaluation were used to test students’ performance in this section?
1. Typical questions for ongoing performance evaluation within this section
1. Briefly describe USB specification.

1. USB/A/B – type C. Describe difference.
1. What devices could be connected using USB bus?
1. Why we do not reboot after USB device connection to discover it?
1. Can we add USB devices to device tree for faster enumeration?
1. Typical questions for seminar classes (labs) within this section
1. Implement simple USB device driver for keyboard/flash card/mouse etc.
1. Test questions for final assessment in this section
1. Describe parameters of USB interface.
1. Describe usage of USB in modern PC/laptop.
1. Describe configuration and enumeration of devices on USB.
1. P.1.2.14 Section 14
1. Section title: Graphical Stack overview
1. Topics covered in this section:
1. Framebuffer
1. X11
1. Wayland
1. UI interfaces: GTK/Qt
1. What forms of evaluation were used to test students’ performance in this section?
1. Typical questions for ongoing performance evaluation within this section
1. Linux- and Windows- comparison of graphical stack.
1. Can we access framebuffer when it is double- or triple- buffered?
1. What part of OS owns framebuffer?
1. How X11 knows when to redraw on screen info?
1. Can we use X11 and Wayland together?
1. Typical questions for seminar classes (labs) within this section
1. Create app with direct access to framebuffer.
1. Use X11 forwarding using SSH tunnel.
1. Create simple GTK/Qt application.
1. Test questions for final assessment in this section
1. Describe the usage of framebuffer.
1. Describe the purpose of X11 system.
1. Describe the purpose and advantages of Wayland framework.

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

**Section 5**

**Section 6**

**Section 7**

**Section 8**

**Section 9**

<!-- catix:relations -->
## Relations

- Duplicate of (the page edited last): [BSTE: Advanced Linux](/courses/bste-advanced-linux.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Advanced Linux](https://eduwiki.innopolis.university/index.php/BSc%3A_Advanced_Linux), revision 7575

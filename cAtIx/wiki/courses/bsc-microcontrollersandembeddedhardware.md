---
type: course
title: "Microcontrollers and Embedded Hardware"
description: "A course covering microcontroller architecture, embedded C programming, and real-time applications using 8051 and PIC18F families."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3AMicrocontrollersandEmbeddedHardware"
tags: ["microcontrollers", "embedded systems", "hardware", "course", "8051", "pic18f"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3AMicrocontrollersandEmbeddedHardware"
    id: "70"
    title: "BSc:MicrocontrollersandEmbeddedHardware"
    last_modified: "2021-07-30T10:45:41Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:36:33+00:00"
status: draft
stale_after: "2023-07-30T10:45:41+00:00"
prerequisite_of: ["/courses/bsc-robotic-systems.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Microcontrollers and Embedded Hardware

## Microcontrollers and Embedded Hardware

- **Course name:** Microcontrollers and Embedded Hardware
- **Course number:**

### Course Characteristics

### What subject area does your course (discipline) belong to?

Logic circuits; Timing analysis; Robotic components; Real-time operating systems; Process management; Embedded software.

#### Key concepts of the class

- Microcontroller and its peripherals function
- Program an embedded system
- Real-time applications

#### What is the purpose of this course?

This subject focuses on the study of advanced microcontroller along with various applications using microcontrollers. It also briefs the students about interfacing of memory and various I/O devices like A to D converter, D to A converter LED, LCD to advanced microcontrollers. The students learn the Programming language (Embedded C) used for microcontrollers. They will be able to use the advanced fast microcontroller.

#### Course objectives based on Bloom’s taxonomy

#### - What should a student remember at the end of the course?

By the end of the course, the students should be able to remember and recognize

- The difference between Microprocessor and Microcontroller based system.
- Differences between: (i) Von-Neuman vs Harvard architecture (ii) RISC vs CISC architecture
- List of the special features of PIC18F452.
- The bit pattern of IPR1 & PIE1 registers of PIC18F452
- Arithmetic operation in PIC18F Family

#### - What should a student be able to understand at the end of the course?

By the end of the course, the students should be able to describe and explain

- How microcontroller and its peripherals function and interface to external peripherals
- The various challenges faced in embedded system design
- The Branching instructions of PIC18F microcontroller
- The Multiply and divide operations in PIC18F Family with example.
- The timers of PIC18F microcontroller and explain any one in brief.

#### - What should a student be able to apply at the end of the course?

By the end of the course, the students should be able to

- Program an embedded system in assembly and C language
- Design, implement and test a single-processor embedded systems for real-time applications in engineering automation
- Optimize embedded software for speed and size for industrial applications

#### Course evaluation

**Course grade breakdown**

|  |  | **Proposed points** |
| --- | --- | --- |
| Labs/assignments | 25 | 45 |
| Interim project report | 25 | 15 |
| Final project report | 50 | 40 |

The course grades are given according to the following rules: Labs/assignments = 45 pts, Interim project report = 15 pts, Final project report = 40 pts.

#### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 90-100 | 80-100 |
| B. Good | 75-89 | 65-79 |
| C. Satisfactory | 60-74 | 40-64 |
| D. Poor | 0-59 | 0-39 |

#### Resources and reference material

Main textbook:

- "Fundamentals of Microcontrollers and Applications in Embedded Systems" Ramesh Gaonkar.

Other reference material:

- “The 8051 Microcontroller and Embedded Systems Using Assembly and C,” Muhammad Ali Mazidi, Janice G Mazidi & Rolin McKinlay.
- “The 8051 Microcontrollers: Architecture, Programming and Applications” K Uma Rao,Andhe Pallavi.
- “Embedded systems architecture, programming and design, second edition” Raj Kamal.

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Teaching Hours** |
| --- | --- | --- |
| 1 | Microcontroller and its peripherals function | 7 |
| 2 | Programming an embedded Systems | 8 |
| 3 | Real-time applications | 7 |

#### Section 1

##### Section title:

Microcontroller and its peripherals function

#### Topics covered in this section:

- Basics of embedded System design
- Microcontroller based systems
- Historical perspective
- von Neumann versus Harvard Architecture
- CISC versus RISC Processors
- Interfacing real world devices with 8051 microcontroller

#### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 0 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 1 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

#### Typical questions for ongoing performance evaluation within this section

1. Define Embedded systems. Give examples
1. Explain the logic operators in embedded C with examples.
1. Describe the hardware units of a generalized Embedded system.
1. Discuss the difference between Microprocessor and Microcontroller based system.

#### Typical questions for seminar classes (labs) within this section

1. Write a short note on Matrix Keyboard interfacing with 8051 microcontroller.
1. Explain serial data transmission and reception in 8051 microcontroller
1. Draw an interfacing diagram of DC motor with 8051 and explain in detail.
1. Define baud rate

#### Test questions for final assessment in this section

1. Differentiate between external hardware interrupts and serial communication interrupts
1. Explain the stack operations in 8051 microcontroller
1. Discuss De-bouncing problem of key and its solution

#### Section 2

##### Section title:

Programming an embedded Systems

#### Topics covered in this section:

- C programming basics and time delay in 8051 C
- I/O programming in8051 C, Logic operations in 8051 C
- Accessing code ROM space in 8051 C
- Programming 8051 timers/Counter in C
- Basics of serial communication, 8051 connection to RS232
- 8051 interrupts programming in C
- DC motor interfacing and PWM using 8051.

#### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 1 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 0 |

#### Typical questions for ongoing performance evaluation within this section

1. How can we interface 8051 with RS-232? Explain the importance of RI & TI flags.
1. Explain bit configuration of PIR1 of PIC18F452.
1. Discuss polling vs interrupts & enlist the various interrupts found in 8051.

#### Typical questions for seminar classes (labs) within this section

1. Draw & explain working of H-bridge circuit for DC motor interfacing with 8051.
1. WAP in C to toggle bit P2.7 every 20ms using Timer0.
1. Explain the stack operation in PIC18f with an example.

#### Test questions for final assessment in this section

1. Explain the interfacing of Relay with microcontroller.
1. Draw the internal structure of PORTA of 8051 microcontroller.
1. Write an Embedded C program for 8051 to find number of positive and negative data among ten byte of array. Send number of positive data to Port P3 and negative data to Port P2.

#### Section 3

##### Section title:

Real-time applications

##### Topics covered in this section:

- Microcontroller Architecture – PIC18F Family
- PIC18F Family Programming model , Introduction to PIC18F Family instruction Set
- Data copy operations, Arithmetic operations, branching operations
- Stack and Subroutines and Illustrative Programs.
- Basics concepts of Input/output ports and Interfacing input/output Peripherals
- PIC18F Interrupts, PIC18F Timers, Illustration programs.

#### What forms of evaluation were used to test students’ performance in this section?

|  | **Yes/No** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 1 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 0 |
| Discussions | 1 |

#### Typical questions for ongoing performance evaluation within this section

1. Describe how to handle an external interrupt give to a port pin in PIC18f series microcontroller. Discuss how you will write an Interrupt Service Routine in C language.
1. Explain the concept of current sinking in case of LED interfacing.
1. Explain the different branch instructions of PIC18F with examples

##### Typical questions for seminar classes (labs) within this section

1. Explain following instructions of 51 family microcontroller [1] MOV A,55h [2] MOV A,#55h [3] MOV @R0,#44h.
1. Write an ALP to clear 10 RAM locations starting at location 60H.
1. Draw & explain the memory organization in PiC18F4xx

##### Test questions for final assessment in this section

1. Write 8051 C programs to send temperature range of -4 to +4 to port P1.
1. List out the timers of PIC18F microcontroller and explain any one in brief
1. Write an 8051 C program to toggle all the bits of P0 and P2 continuously with a 200ms delay

<!-- catix:relations -->
## Relations

- Required for: [BSc: Robotic Systems](/courses/bsc-robotic-systems.md)
<!-- /catix:relations -->

# Citations

1. [BSc:MicrocontrollersandEmbeddedHardware](https://eduwiki.innopolis.university/index.php/BSc%3AMicrocontrollersandEmbeddedHardware), revision 70

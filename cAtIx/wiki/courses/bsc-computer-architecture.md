---
type: course
title: "Fundamentals of Computer Architecture"
description: "A course covering fundamental principles of modern computer systems, hardware/software interaction, instruction execution, and computer arithmetics using MIPS and Verilog."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Computer_Architecture"
tags: ["computer-architecture", "hardware", "mips", "verilog", "computer-science"]
aliases: ["BSc:ComputerArchitecture"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Computer_Architecture"
    id: "9662"
    title: "BSc: Computer Architecture"
    last_modified: "2024-09-15T00:10:07Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:44:20+00:00"
status: draft
stale_after: "2026-09-15T00:10:07+00:00"
prerequisite_of: ["/courses/bsc-capstone-project.md"]
prerequisites: [{"as_written": "Informatics"}, {"course": "/courses/bsc-introduction-to-programming.md", "as_written": "Basic programming skills", "via": "model"}, {"course": "/courses/bsc-b1-v-dv-03-02-mfai-2024-mathematical-logic-for-ai.md", "as_written": "The basics of Boolean logic", "via": "model"}]
taught_by: ["/people/alexandertormasov.md", "/people/artemburmyakov.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Fundamentals of Computer Architecture

## Fundamentals of Computer Architecture
- **Course name**: Fundamentals of Computer Architecture
- **Code discipline**: XXX
- **Subject area**: Computer Science Fundamentals

### Short Description
This course covers the fundamental principles of modern computer systems and software/hardware interaction, the representation and execution of computer instructions, computer arithmetics.

### Prerequisites

#### Prerequisite subjects
- Informatics
- Basic programming skills
- The basics of Boolean logic


#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Introduction to the Fundamental Concepts of Computer Architecture | # Key Components of a Computer System <br> # Fundamental Ideas of Computer Architecture <br> # Translation Hierarchy of a High-Level Program into Machine Code <br> # Performance Metrics of a Computer System |
| Computational Logic Implementation in a Computer System | # Logic Gates and Boolean Algebra <br> # Logic Circuits <br> # Combinational and Sequential Logic <br> # Number Systems <br> # The Basics of Verilog Hardware Description Language (HDL) Programming |
| Instruction Representation and Execution in a Computer System | # Instruction Set Architecture (ISA) <br> # The Overview of MIPS ISA <br> # Types of MIPS Instructions and Their Representation in a Binary Format <br> # Sample MIPS Assembly Programs |
| Computer Arithmetics | # Basic Arithmetic Operations (Bitwise, Shifts, Multiplication, Division, and Others) <br> # Overflow and Underflow Problems for Arithmetic Operations <br> # Arithmetic Operations with Floation Point Numbers <br> # Problems Related to Precision and Conversion for Floating Point Numbers |
| Processor Architecture | # Key Components of a Processor: Control and Arithmetic Logic Unit, Registers <br> # Processor Datapath and Control Signals <br> # The Notion of a Pipelined Execution, Pipeline Hazards, and Their Solutions <br> # A Simple and Pipelined Implementation Schemes of a Processor |
| Advanced Topics | # Computer Security and Vulnerabilities <br> # Graphics Processing Unit (GPU) and General-Purpose GPU Programming <br> # Modern Approaches for Memory Hierarchy Design |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The main purpose of this course is to cover the fundamental theoretical principles of computer systems design. We first overview the key hardware components of a modern computer system, available performance metrics, and the general principles of computer architecture. We then discuss the representation and execution of computer instructions, instruction set architecture, the translation hierarchy of a high-level program into machine code. We also cover the elements of computer arithmetics, logic circuits, including combinational and sequential logic circuits. These theoretical principles are illustrated by using MIPS instruction set architecture, FPGA, and Verilog HDL programming language during the labs. We then study in details simple and pipelined implementation schemes of a processor, the idea of a pipelined execution, related hazards and their solutions. We complete the course by introducing several advanced topics, including computer security and vulnerabilities, GPU programming, and modern principles for memory hierarchy design.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Key components of a modern computer system
- Available performance metrics for computer systems
- Computer arithmetics operations, including floating point numbers
- Number systems and conversion between them
- Representation formats for computer instructions

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Fundamental principles of computer architecture (Moore’s law, memory hierarchy, multiprocessing, speculative execution, and others)
- The design scheme of a modern processor
- The interaction principles between software and hardware
- Program representation and execution by a computer system

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- The design skills of logic circuits by using Verilog HDL programming language
- FPGA programming by using Quartus Prime software
- MIPS assembly programming (including MARS simulator) 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 90-100 | - |
| B. Good | 70-89 | - |
| C. Satisfactory | 60-69 | - |
| D. Poor | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar Classes | 15 |
| Regular quizzes during tutorials | 5 |
| Midterm Exam | 20 |
| Final Exam | 60 |
| Bonus points for optional FPGA projects | 2 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Handouts supplied by the instructor
- Online resources shared by instructor

#### Closed access resources


#### Software and tools used within the course

## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 | Section 5 | Section 6 |
| --- | --- | --- | --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 1 | 1 | 1 | 1 | 1 |
| Homework and group projects | 1 | 1 | 1 | 1 | 1 | 1 |
| Midterm evaluation | 1 | 1 | 1 | 0 | 0 | 0 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 | 1 | 1 |
| Oral polls | 1 | 1 | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content                                                                                                                                                                                                                                                                                                                                                            | Is Graded? |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| Question      | Do you agree that main memory (RAM) is a non-volatile memory?                                                                                                                                                                                                                                                                                                      | 1          |
| Question      | There are several types of memory available for computers, such as CPU cache, main memory (RAM), SSD, etc. What are the key differences between them?                                                                                                                                                                                                              | 1          |
| Question      | What is the key principle behind the Von Neumann Architecture?                                                                                                                                                                                                                                                                                                     | 1          |
| Question      | Specify a correct order for tools used during high-level program translation and execution: Compiler, Assebler, Linker, Loader;                                                                                                                                                                                                                                    | 1          |
| Question      | Let a program run on a computer comprised of one processor only. Let us now increase the number of processors up to m>1, so that multiple instructions of that program can be executed in parallel. Assume that all processor speeds are the same. Do you agree that a program can never execute slower on m processors, as compared to the case of one processor? | 1          |
| Question      | Demonstration and description of key elements of an FPGA board (memory unit, PCI slot, clock generator, etc.);                                                                                                                                                                                                                                                     | 0          |
| Question      | Description of specific features of FPGA as compared to other integrated circuit devices;                                                                                                                                                                                                                                                                          | 0          |
| Question      | Writing basic code for FPGA board;                                                                                                                                                                                                                                                                                                                                 | 0          |
| Question      | Configuration and usage of the basic functionality in Quartus Prime software                                                                                                                                                                                                                                                                                       | 0          |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Convert decimal number 123 into base-5 format; | 1 |
| Question | Do you agree that a S/R latch and a D flip-flop have different storage capacities? | 1 |
| Question | Choose the key differences between SRAM and DRAM memory types: cost, power consumption, volatility, access speed, storage capacity, etc.; | 1 |
| Question | Do you agree that one of the key differences between sequential and combinational logic circuits is the presence of memory elements? | 1 |
| Question | Questions regarding the basic logic gates; | 0 |
| Question | Assignments to design simple logic circuits with 2-3 logic gates on a white board; | 0 |
| Question | Programming assignments in Quartus Prime software, to design and compile simple logic circuits; | 0 |
| Question | Programming an FPGA board by using Verilog HDL in Quartus Prime environment, such as turning on or off leds based on a switch position; | 0 |
| Question | Questions regarding the difference between combinational and sequential logic circuits; | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How many bits are in one MIPS word? | 1 |
| Question | Which MIPS directive would you use to create a string data? | 1 |
| Question | For MIPS instruction set architecture (ISA), each register is reserved for a specific purpose. Describe the purpose of registers listed below: <math>v0, </math>s0-<math>s7, </math>t0-$t7; | 1 |
| Question | In MARS simulator for MIPS programming, all register values, that are displayed in the register viewer, start with prefix "0x". What is the meaning of this prefix? | 1 |
| Question | Print a "Hello, World!" message in a console; | 0 |
| Question | Computation of a simple arithmetic expression for integer parameters; | 0 |
| Question | Computation of the first 10 Fibonacci numbers; | 0 |
| Question | Implementation of more advanced program structures, such as conditional loops | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Assume that two MIPS registers, <math>s0 and </math>s1, contain the following binary data: <math>s0: 00100000; </math>s1: 01010101 (For simplicity, we assume 8-bit registers, rather that 32) What is the value of <math>s1 after the execution of the following instruction?: sll </math>s1, $s0, 4 | 1 |
| Question | What is a "register spilling" in the context of MIPS instruction set architecture? | 1 |
| Question | Do you agree with the following statement? In some cases, MIPS logical shift operations, sll and srl, can be used as an efficient alternative to multiplication and division operations, mul and div. | 1 |
| Question | Do you agree that overflow and underflow exceptions correspond to cases, when the result of an arithmetic operation surpasses and subceeds, respectively, the maximum and the minimum value for an appropriate data type returned by that arithmetic operation? | 1 |
| Question | Division of two floating-point numbers; | 0 |
| Question | Conversion of Fahrenheit into Celsius temperature, and vice versa; | 0 |
| Question | Computation of a sphere surphase area; | 0 |
| Question | Questions regarding the execution of arithmetic operations with interger and floating-point values | 0 |
##### Section 5
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Do you agree that the key motivation for the CPU pipelining is to speed-up the execution of a program by exploring multiple CPU cores? | 1 |
| Question | Which CPU block(s) is/are accessed during the execution of the following instruction? lw <math>1, 5(</math>2) | 1 |
| Question | What are 5 major stages of a pipelined instruction execution? | 1 |
| Question | Do you agree that, for a processor with 5 pipelined stages, the number of concurrently executed instructions is up to 4? | 1 |
| Question | There are several types of processors available, including single-cycle and multicycle.The major advantage of a single-cycle processor is the simplicity of its design. But what is its key drawback? | 1 |
| Question | Design of a testbench in ModelSim for Quartus Prime programming environment; | 0 |
| Question | The design of Half-Adder, Full-Adder, Ripple Carry Adder by using Verilog HDL in Quartus Prime | 0 |
| Question | Testing the correctness of Verilog HDL design by using ModelSim | 0 |
##### Section 6
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Cold boot attack explores vulnerabilities in a memory dump mechanism. What is a memory dump? | 1 |
| Question | Below is a list of possible vulnerability attacks. Choose the one(s) that explore(s) vulnerabilities in a speculative execution of modern processors: Meltdown, Foreshadow, Cold boot attack, Spectre, No choice is correct; | 1 |
| Question | Choose the most precise definition for a side-channel attack: An attack that explores vulnerabilities in the hardware implementation of a computer system, An attack that explores vulnerabilities in the software components of a computer system; | 1 |
| Question | Do you agree that Meltdown and Spectre vulnerabilities both explore race conditions in existing memory circuits? | 1 |
| Question | Programming assignment to implement Multiplexor using Verilog HDL in Quartus Prime; | 0 |
| Question | Performance optimization of a Verilog HDL design; | 0 |
| Question | The design of a simple Arithmetic-Logic Unit (ALU); | 0 |
| Question | Revision questions | 0 |
#### Final assessment
**Section 1**
1. Briefly describe the principles of Von Neumann architecture. Illustrate with a diagram.
1. Describe the steps that transform a program written in a high-level language such as C into a representation that is directly executed by a computer processor. Illustrate with a diagram; provide a brief description for each step.
1. Consider three different processors P1, P2, and P3 executing the same instruction set. P1 has a 3 GHz clock rate and a CPI of 1.5. P2 has a 2.5 GHz clock rate and a CPI of 1.0. P3 has a 4.0 GHz clock rate and has a CPI of 2.2. Answer the following questions: a) Which processor has the highest performance expressed in instructions per second? b) If the processors each execute a program in 10 seconds, find the number of cycles and the number of instructions. c) We are trying to reduce the execution time by 30% but this leads to an increase of 20% in the CPI. What clock rate should we have to get this time reduction?
**Section 2**
1. Prove that the AND and NOT logic gates can be implemented by using only the NOR logic gate.
1. What are the S/R latch and D latch? Draw the respective logic circuits. Describe the differences between them.
1. Briefly describe the key difference(s) between combinational and sequential logic circuits.
1. Define what a multiplexor logic circuit is (with an arbitrary number of inputs). Provide a truth table for a 2-to-1 multiplexor. Provide a logic circuit implementing a 2-to-1 multiplexor, that uses AND, NOT, and OR logic gates. Describe a Verilog module implementing such a logic circuit of a 2-to-1 multiplexor.
**Section 3**
1. Translate the following MIPS code to C (or pseudocode). Assume that variables f, g, h, and i are assigned to registers <math>s0, </math>s1, <math>s2, and </math>s3, respectively. Code to translate: sub <math>t0, </math>s1, <math>s2; addi <math>t0, </math>t0, 3; add <math>s0, </math>s3, </math>t0
1. Assume that two MIPS registers, <math>{\textstyle s0and}</math> s1, contain the following binary data (for simplicity, we assume 8-bit registers, rather that 32): <math>s0: 00100000; </math>s1: 01010101. What is the value of register <math>s1 after the execution of the following MIPS instruction?: sll </math>s1, $s0, 4.
1. List and describe the purpose of general-purpose MIPS registers.
**Section 4**
1. Briefly describe the overflow and underflow problems for arithmetic operations.
1. Describe the difference between executing arithmetic operations with integers and floating-point values for a MIPS processor.
1. What is a precision problem for a floating-point operation?
**Section 5**
1. What is a Program Counter (PC) register of a processor?
1. Describe the principle of a pipelined CPU execution. Provide a diagram illustrating the concept. Briefly describe the 5 key stages of a classical pipeline.
1. What are the key differences between Control Unit (CU) and Arithmetic Logic Unit (ALU) of a processor? Which purposes do they serve?
1. What is a CPU datapath?
**Section 6**
1. What is an out-of-order execution? What hardware features of CPU implementation, in addition to an out-of-order execution, are exploited by Meltdown vulnerability? How serious is Meltdown vulnerability?
1. What is an instruction-level parallelism?
1. Describe the idea of a general-purpose GPU programming.
1. Briefly explain the working principles of a CPU cache.
1. Discuss advantages and drawbacks of a hierarchical memory model for computer systems.

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

**Section 5**

**Section 6**

<!-- catix:relations -->
## Relations

- Prerequisites: Informatics; [BSc: Introduction To Programming](/courses/bsc-introduction-to-programming.md) (Basic programming skills, matched by the model); [Mathematical logic for AI](/courses/bsc-b1-v-dv-03-02-mfai-2024-mathematical-logic-for-ai.md) (The basics of Boolean logic, matched by the model)
- Required for: [BSc: Capstone Project](/courses/bsc-capstone-project.md)
- Taught by: [Alexander Tormasov](/people/alexandertormasov.md), [Artem Burmyakov](/people/artemburmyakov.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Computer Architecture](https://eduwiki.innopolis.university/index.php/BSc%3A_Computer_Architecture), revision 9662

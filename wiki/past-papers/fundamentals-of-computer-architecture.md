---
type: page
title: "Past exam papers: Fundamentals of Computer Architecture"
description: "Past exams and tests of Fundamentals of Computer Architecture at Innopolis University (17 papers, 2019–2025), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "fundamentals-of-computer-architecture"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "Fundamentals of Computer Architecture"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: Fundamentals of Computer Architecture

Exams and tests of **Fundamentals of Computer Architecture** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2025: Final

Files: [Fundamentals of CompArch Final 2025.pdf](https://glebpopov.notion.site/356e746cceef805ba157c68e27b5c32a)


Innopolis University
Academic Year 2025/2026
Final Exam of Computer Architecture
22nd December 2025
ANSWERS
Duration: 60 minutes

Student Full Name:
Student Group:
Exam Room:
Telegram Alias:
Midterm missed (underline): No / Yes
Missed the course beginning due to Visa issues: No / Yes

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Total

Grade Summary (for instructors fill)
Grade

Maximum score: 12 points

Please write clearly your name and your solutions. What will not be understood will be
considered wrong. All answers must be provided in English.
This is a closed-book exam. You are not allowed to use any reference materials or electronic
equipment, apart from this booklet and pens. You are not allowed to consult any person,
otherwise you will be disqualified from this exam at the very first attempt.
Good Luck!
Signature:

Computer Architecture – Final 2025

Student Surname:

Successfully passed the Course: 219 out of 269 students

Question 1. (1 point) Do you agree that a USB drive typically provides a higher access speed
compared to a System Memory of a computer device?
a) Agree

b) Disagree (correct)

Grading: 0/1

Question 2. (1 point) What is the key idea of Moore’s law?
Brief Answer: Every 18-24 months the number of transistors on a CPU chip increases / CPU
speed doubles, or similar.
Grading criteria:
(+0.5) – a correct time interval;
(+0.5) – a correct increase of the number of transistors / speed-up

Computer Architecture – Final 2025

Page 2 of 7

Student Surname:
Question 3. (2 points) Draw a logic circuit of a 1-to-2 decoder by using any required logic gates
out of AND, OR, and NOT types. Write the SystemVerilog design for such a circuit.
Answer:
1-to-2 Decoder Circuit

SystemVerilog Design
(one out of multiple possible)
module decoder(
input i1,
);

output o1, o2

assign o1 = i1;
assign o2 = ~i1;
endmodule
Grading criteria:
(+1) – a correct circuit representation;
(+1) – a correct SystemVerilog design;
(-0.5) – a single syntax-related error in the SystemVerilog design

Question 4. (2 points) Briefly explain the general purpose of a communication bus in a
computer. Support your answer with an illustration. Then, provide an example of a
communication bus (formally, a communication bus protocol) and the purpose it is used for.
Answer:
General Communication Bus Purpose (1 point)

Illustration (0.5 point)

To provide data communication between
different computer components (including
peripheral devices)

Example of a communication bus (name only, 0.25 point):
PCI (Peripheral Component Interconnect),
and its specific usage purpose (0.25 point):
To connect Southbridge chipset to the I/O peripheral devices.
Computer Architecture – Final 2025

Page 3 of 7

Student Surname:
Grading criteria:
(+1) – a correct definition of a general communication bus purpose;
(-0.5) – for a specific instead of a general communication bus purpose specified;
(+0.5) – for a correct illustration (a specific case of two components with a communication bus
explicitly pointed out);
(+0.25) – a correct protocol name;
(+0.25) – a correct purpose of a protocol description
Question 5. (2 points) What is the key reason for DRAM memory units to be slower than SRAM
memory units? Graphically illustrate an internal physical organization of a single memory cell.
Based on this illustration, describe the key process steps of storing data into this memory cell.
Answer:
a) The key reason for DRAM to be slower than SRAM (1.5 points, (+0.25) – for partially correct):
Unlike SRAM memory, DRAM relies on capacitors, which take more time for
charge/discharge.
b) Cell physical organization and data storage procedure:
DRAM cell physical organization (0.25 point)

Steps of data storage procedure (0.25 point)
Step 1: Wordline is activated, to activate the
base pin of a cell transistor
Step 2: Bitline is activated or deactivated,
depending on data to be stored into a
capacitor
(continue in the same format)

Step 3: Bitline and wordlines are disactivated,
after a certain timeout required for a cell
capacitor charge/discharge

Grading criteria:
See in the “Answers” field above.

Computer Architecture – Final 2025

Page 4 of 7

Student Surname:
Question 6. (2 points) Below is a schematic representation of the System Memory content:
“Addr.” column corresponds to a memory cell address (of 4 bits), and
“Data” – to the data stored into that memory cell (of 1 byte).
Considering that System Memory data given in the table at the left, fill-in the System Memory
data in the table at the bottom, which results after executing the RISC-V program at the right.
Note that, for your convenience:
a) Constant values in the RISC-V program are provided in a decimal format;
a) “la” instruction takes an input address as an immediate value
System Memory: Before
Addr.
0000
0001
0010
0011
0100

Data

00010001
00001000
00000001
00001010
00000101

Addr.

0101
0110
0111
1000
1001

Data

00001010
00000110
00010001
00000011
00001010

RISC-V Program
li
la
sw
lw
addi
sw

t3, 2
t1, 4
t3, 2(t1)
t3, 1(t1)
t3, t3, 1
t3, 0(t1)

Answer:
Case 1:
System Memory: Resulted (to be filled-in)
Addr. Data
0000
0001
0010
0011
0100

00010001
00001000
00000001
00001010
00001011

Addr. Data

0101
0110
0111
1000
1001

00000010
00000000
00000000
00000000
00000000

Case 2 (If a 1 byte data portion is erroneously
considered instead of one “word” = 4 bytes for
“sw” and “lw” instructions ):

System Memory: Resulted (to be filled-in)
Addr. Data
0000
0001
0010
0011
0100

00010001
00001000
00000001
00001010
00001011

Addr. Data

0101
0110
0111
1000
1001

00001010
00000010
00010001
00000011
00001010

Grading criteria:
(-0.5) – for every incorrectly filled cell in the system memory table;
Case 2 is equality considered correct to Case 1, despite being erroneous;

Computer Architecture – Final 2025

Page 5 of 7

Student Surname:
Question 7. (2 points) Consider the following RISC-V machine language program:
0
0
0
0

0
0
0
0

0
0
0
0

0
0
0
0

1
0
0
1

1
0
0
1

1
0
0
1

1
0
0
0

0
1
0
0

0
0
0
1

0
0
0
0

0
1
1
1

1
1
0
1

0
0
0
0

0
1
1
0

1
0
0
1

0
1
1
0

0
0
0
0

1
0
0
1

1
0
0
1

0
0
0
1

0
0
0
0

1
1
1
0

0
0
0
0

1
1
1
0

0
0
0
0

0
1
0
1

0
1
1
0

0
0
0
0

0
0
0
0

1
1
1
1

1
1
1
1

Restore a RISC-V assembly language program, which corresponds to a RISC-V machine code
above. To support your answer, provide comments above every instruction with comments,
which illustrate your reasoning, near every binary instruction representation. All necessary
reference material to be used is provided below.

Answer:
Binary 1

0 0 0 0 1 1 1 1 0 0 0 0 1 0 0 1 0 0 1 1 0 0 1 0 1 0 0 0 0 0 1 1

Assembly

ld x5, 240(x18) or ld t0, 240(s2)

Binary 2

0 0 0 0 0 0 0 0 1 0 0 1 1 0 1 0 1 0 0 0 0 0 1 0 1 0 1 1 0 0 1 1

Assembly

add x5, x21, x9 or add t0, s5, s1

Binary 3

0 0 0 0 0 0 0 0 0 0 0 1 0 0 1 0 1 0 0 0 0 0 1 0 1 0 0 1 0 0 1 1

Assembly

addi x5, x5, 1 or addi t0, t0, 1

Binary 4

0 0 0 0 1 1 1 0 0 1 0 1 1 0 0 1 0 0 1 1 1 0 0 0 0 0 1 0 0 0 1 1

Assembly

sd x5, 240(x18) or sd t0, 240(s2)

Reasoning/
Comment

Reasoning/
Comment

Reasoning/
Comment

Reasoning/
Comment

Grading criteria:
(+0.5) – for every correct instruction with arguments;
(+0.1) – for every correct instruction name, but incorrect arguments;
Misplaced names for source registers are not penalized;
Computer Architecture – Final 2025

Page 6 of 7

Student Surname:
Additional note:
(+0.5) – To all works, “Christmas” points to compensate a typo in Lecture Week 13, Part
III, Slide 63 for a binary representation for the second RISC-V instruction

Computer Architecture – Final 2025

Page 7 of 7

## 2025: Midterm

Files: [Fundamentals of CompArch Midterm 2025.pdf](https://glebpopov.notion.site/356e746cceef8047a68aea345d658845)


Innopolis University
Academic Year 2025/2026
Computer Architecture Course
Midterm Exam

ANSWERS

24th October 2025
Duration: 60 mins

Student Full Name:
Student Telegram:
Exam Room:
Started education late (due to Visa delay): NO / YES

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Question 8
Total (max. 15 points)

Summary (for instructors fill)
Grade

Please write clearly your name and your solutions. Write your name at every page.
What will not be understood will be considered wrong. All answers must be provided in
English, everything written in Russian will be ignored.
This is a closed-book exam. You are not allowed to use any reference materials or electronic
equipment, apart from this booklet and pens. You are not allowed to consult any person,
otherwise you will be disqualified from this exam at the very first attempt.
Student Signature:

Student Name:

Question 1 (1 point). Choose non-volatile memory units of a computer
(circle or underline correct options):
1)
2)
3)
4)
5)
6)

USB stick - correct, but no penalty if not chosen
System Memory
L1 and L2 Caches
Solid-State Drive (SSD) – correct
Hardware Disk Drive (HDD) - correct
None of the above

Grading notes:
(+0.5) – for any correct option chosen, but at most 1;
(-0.5) – for any incorrect option chosen, except option 6;
(-1) – for option 6.

Question 2 (1 point). Name the CPU component responsible for performing Instructions Fetch
(IF) from memory.
Answer:
Control Unit (CU)
(answer “registers” is also considered, due to a possible lecture slides misinterpretation)
Grading notes:
(+1) – for a fully correct answer, otherwise 0.

Midterm Exam of Computer Architecture 2025

Page 2 of 7

Student Name:
Question 3 (2 points). The photo below depicts the fragment of a computer laptop hardware.
Specify in the empty rectangles names of pointed components. What is the major difference
between components “a” and “b”?
Answer:
Component names:
Some possible differences between “a” and “b”
components:
- GPU has more cores than CPU;
- GPU has more ALUs than CPU;
- GPU supports SIMD parallelism model;
- GPU is used to process graphics, unlike CPU;
- Unlike CPU, GPU has a limited Instruction Set
- Other

Grading notes:
(+0.5) – for every correctly named component in the diagram;
(+0.5) – for a correctly described difference between CPU and GPU

Question 4 (3 points). The diagram below depicts well-known logic circuits used in computer
components. Do the following:
1) (1 point) For each circuit specify its corresponding name in an empty rectangle;
2) (2 points) For circuits “b”, “d”, “e”, “f” fill-in their truth tables.

Midterm Exam of Computer Architecture 2025

Page 3 of 7

Student Name:

Grading notes:
(+0.2) – for each correctly specified circuit name, but at most 1 point in total;
(+0.5) – for each fully correctly filled truth table;

Midterm Exam of Computer Architecture 2025

Page 4 of 7

Student Name:
Question 5 (2 points). What is the key idea of Amdahl’s law? Plot Amdahl’s law for a program
with 90% of parallelizable instructions.
Answer:
One of possible formulations for Amdahl’s law idea (equation is not needed):
The increase of the number of cores speeds-up the execution of a program proportionally to the
fraction of parallelizable instructions.
Amdahl’s law plot for a program with 90% of parallelizable instructions:
Purple line among the ones below:

Grading notes:
(+1) – Correctly described idea of Amdahl’s law;
(+0.5) – Correctly labeled axes;
(+0.5) – Correct plot line (with precise numeric values), but a totally correct equation was also
considered.
Question 6 (2 points). Answer the following questions regarding a CPU clock generator:
a) (0.5 points) What is the main purpose of a CPU clock?
A possible brief answer: To synchronize inputs/instructions execution by CPU.
b) (0.5 points) Draw a clock wave and name its key parts by using standard terminology:

Midterm Exam of Computer Architecture 2025

Page 5 of 7

Student Name:
c) (0.5 points) What is the relation between a CPU speed and its clock wave period?
A possible brief answer: Higher the CPU clock period, slower the execution speed of CPU
d) (0.5 points) What is the difference between level-triggered and edge-triggered clock
methodology? Brief answer: See note on the diagram above.
Grading notes:
(+0.5) – for every fully correctly answered sub-question
Question 7 (2 points). The diagram below represents a northbridge/southbridge computer
layout. Fill-in the missing component names into empty rectangles.
Answer:

Grading notes:
(+0.4) – for every correctly specified option (CPU, Clock, Memory slots, Northbridge and
Southbridge chipsets)

Question 8 (2 points). Draw the circuit of a flip-flop, which updates its output value at the rising
clock edge. Describe the necessary change to make this circuit update its output value at the
falling clock edge instead.
Answer:

Midterm Exam of Computer Architecture 2025

Page 6 of 7

Student Name:

Description of changes to make output value to be updated at a falling clock edge:
See instructions provided in the diagram above.
Grading notes:
(+0.5) – correctly specified master and slave latches;
(+0.5) – correctly connected clock signal;
(+0.5) – correctly placed NOT gates;
(+0.5) – for a correct transformation description into updating Qfinal at a falling edge.

This is the end of the student book
Draft Paper

Midterm Exam of Computer Architecture 2025

Page 7 of 7

## 2025: Pre Final

Files: [Fundamentals of CompArch Pre Final 2025.pdf](https://glebpopov.notion.site/356e746cceef80fe918bc7cf073c5e63)


Innopolis University
Academic Year 2025/2026
Pre-Final Exam of Computer Architecture
ANSWERS
th
12 December 2025
Duration: 60 minutes

Student Full Name:
Student Group:
Exam Room:
Telegram Alias:
Midterm missed (underline): No / Yes
Missed the course beginning due to Visa issues: No / Yes

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Question 8 [Optional]
Total

Grade Summary (for instructors fill)
Grade

Maximum score: 12 points

Please write clearly your name and your solutions. What will not be understood will be
considered wrong. All answers must be provided in English.
This is a closed-book exam. You are not allowed to use any reference materials or electronic
equipment, apart from this booklet and pens. You are not allowed to consult any person,
otherwise you will be disqualified from this exam at the very first attempt.
Good Luck!
Signature:

Computer Architecture – Pre-Final 2025

Student Surname:

Page 2 of 4
Computer Architecture – Pre-Final 2025

Student Surname:
Question 1. (1 point) Do you agree that, unlike an S/R latch, a flip-flop does not synchronize
the update of its output with a clock signal?
a) Agree;
b) Disagree (correct)
Grading: 0/1
Question 2. (1 point) The SystemVerilog design below describes one of the standard hardware
building blocks, which is extensively used in electrical computer components. Name this
corresponding hardware building block circuit, together with its graphical diagram.
Answer (circuit name): 2-to-1 Multiplexer
Circuit diagram:

Grading:
(+0.5) – correct circuit name;
(+0.5) – circuit implementation
Question 3. (2 points) Data in a processor cache is organized by means of cache lines,
comprised of several fields, as schematically depicted below. Fill-in the missing field names,
and also briefly describe the purpose of the “validity flag” field.
Names of cache line fields:

A “validity flag” field purpose (brief):
To indicate that data in a specific cache line is actual, that is initialized and updated according to
a program execution.
Grading:
(-0.5) – for every incorrect field name (the specified order does not matter, similar names are
considered as correct);
(-0.5) – in “purpose” description only data initialization is mentioned, but “actual/recently
updated / etc.” is not mentioned
(+1) – for a fully correct “purpose” description
Page 3 of 4
Computer Architecture – Pre-Final 2025

Student Surname:
Question 4. (2 points) The ALU unit of a RISC-V processor has a so-called “Zero” output pin.
What is its purpose? Provide the name of any RISC-V instruction, that uses this “Zero” output
pin during its execution.
The purpose of the “Zero” output pin (brief, at most 2 sentences):
Indicates either two inputs for ALU are equal (“Zero pin” is set to 1 in this case, otherwise to 0).
This “Zero” pin is used when executing “branch if equal” and “branch if not equal” like instructions.
The name of any RISC-V instruction using the “Zero” output pin: beq, bne (among others)
Grading:
0.5 (for entire question) – no correct RISC-V instruction name is provided, but “branch” key word
is present; the “purpose” description in this case is not checked and graded by 0; “less than” and
“greater than” like instructions are incorrect answers;
(+1) – for a correct RISC-V instruction name;
(+1) – for a fully correct “purpose” description;
(-0.5) – for mentioning “jump”-type instructions in the “purpose” description, what is incorrect,
but the RISC-V instruction name is correct

Question 5. (2 points) Flynn’s taxonomy identifies four computational models for computer
systems. List these four models in the table at the left. Then, for each processing unit type listed
in the table at the right, specify the corresponding Flynn’s taxonomy model.
Computation Model
1

SISD: Single Instruction Single Data

2

MISD: Multiple Instruction Single Data

3

SIMD: Single Instruction Multiple Data

4

MIMD: Multiple Instruction Multiple Data

Processing Unit

Flynn’s Taxonomy

GPU

SIMD

Multi-Core CPU MIMD
Single-Core
CPU

SISD

Grading:
(+0.25) – for every correct “Computation Model”;
(-0.5) – for every incorrect “Flynn’s Taxonomy” name specified in the column at the right

Page 4 of 4
Computer Architecture – Pre-Final 2025

Student Surname:
Question 6. (2 points) Parallel and speculative executions of processor instructions are two
widely used efficient techniques for optimizing computers performance. Describe the key
principle behind each of these techniques, together with examples, from the perspective of a
single computer program execution (do not consider a simultaneous execution of multiple
independent programs in your answer).

Grading:
(+0.5) – for every correctly filled table cell
Question 7. (2 points) Graphically describe the multiplicator circuit taking two input
arguments of two bits each. To simplify your design, reuse Half- and Full-adder circuits as
“black boxes” without describing their internal organization. In addition, use any other logic
gates required for your multiplicator design.
Answer:

Grading:
(+1) – 4 input pins, 4 output pins, 4 ANDs, 2 Half-Adders are all present;
(+1) – all wires are correctly connected
Page 4 of 4
Computer Architecture – Pre-Final 2025

Student Surname:
[Optional] Question 8. (1 point) Below is the fragment of a schematic design for a multi-cycle
RISC-V processor. Fill-in the missing part of the design, which implements the execution of R
and I types of RISC-V processor instructions.

Grading:
0 – in case of no pipeline registers are present (that is single-cycle CPU is depicted);
(+0.5) – 3 pipeline registers, register file, ALU, multiplexer for the 2d ALU input pin are all present
(+0.5) – wires are correctly connected

This is the end of the student book

Page 4 of 4
Computer Architecture – Pre-Final 2025

## 2024: Final

Files: [Fundamentals of CompArch Final 2024.pdf](https://glebpopov.notion.site/15ae746cceef8058a85aeec5c54cfa84)


Innopolis University
Academic Year 2024/2025
Final Exam of Computer Architecture
12th December 2024
Duration: 60 minutes

Student Full Name:
Student Group:
Exam Room:
Telegram Alias:
Midterm missed (underline): No / Yes

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Question 8
Question 9
Question 10
Total

Grade Summary (for instructors fill)
Grade

Maximum score: 14 points

Please write clearly your name and your solutions. What will not be understood will be
considered wrong. All answers must be provided in English.
This is a closed-book exam. You are not allowed to use any reference materials or
electronic equipment, apart from this booklet and pens. You are not allowed to consult
any person, otherwise you will be disqualified from this exam at the very first attempt.
Good Luck!
Signature:
Computer Architecture – Final Exam Answers 2024

1

Course Grade Statistics

Computer Architecture – Final Exam Answers 2024

2

Computer Architecture – Final Exam Answers 2024

3

Question 1. (1 point) Choose a RISC-V processor register used for specifying a system
call (“syscall”) code:
a) a7 (correct)

b) f7

c) s7

d) t7

e) zero

f) No choice is correct

Grading: (1 point) – for (a); (0 points) – for an incorrect option, or more than one option

Question 2. (1 point) Choose valid characteristic(s) for RISC-V processor architecture:
1) The size of R-type instructions is 32 bits, while the size of I- and J-types are 64 bits;
2) (correct) The default storage capacity of a RISC-V general-purpose register
is 64 bits;
3) Unlike other existing processor architectures, RISC-V uses no clock generator
Grading: (1 point) – for (2); (0 points) – for an incorrect option, or more than one option

Question 3. (1 point) Below is a high-level classification for RISC-V processor registers.
Provide examples of RISC-V register names for each category in empty rectangles.

RISC-V Registers
Directly addressable

Not directly addressable,
Special-purpose

PC (or HI, LO from MIPS)
General-purpose

Floating-point

Grading:
(1 point) – all cases are correct;
(+0.3) – for every correct option otherwise

Computer Architecture – Final Exam Answers 2024

4

Question 4. (1 point) Which hardware building block corresponds to the SystemVerilog
design provided below?
Answer: __(1-to-4) demultiplexer__
Grading:
(1 point) – for the “demultiplexer” key word;
(0 points) - otherwise

module HwBuildingBlock (
input
d,
input [1:0] s,
output logic q0,
output logic q1,
output logic q2,
output logic q3
);
always_comb
case (s)
2'b00:
begin
q0 = d;
q1 = 0;
q2 = 0;
q3 = 0;
end
2'b01:
begin
q0 = 0;
q1 = d;
q2 = 0;
q3 = 0;
end

==(continuation)==
2'b10:
begin
q0 = 0;
q1 = 0;
q2 = d;
q3 = 0;
end
2'b11:
begin
q0 = 0;
q1 = 0;
q2 = 0;
q3 = d;
end
endcase
endmodule

Question 5. (1 points) RISC-V registers s0 and s1 contain the following binary data (for
simplicity, we assume 8-bit registers, rather that 64):
s0:
s1:
s2:

00100000
01010101
00000100

What is the value of register s1 after executing the following RISC-V instruction?:
sll s1, s0, s2
Answer: ____00000000______
The answer is obtained by shifting the value of s0 register by 4 positions to the left;
decimal value 4 corresponds to a binary value in s2 register
Grading: (1 point) – for fully correct answer; (0 points) – otherwise

Computer Architecture – Final Exam Answers 2024

5

Question 6. (1 point) The “performance via speculation” principle provides the
mechanism for speeding-up program execution. Briefly describe its key idea.
Answer (at most 3 sentences):
Its idea is to speedup a program execution by predicting the result of a program
flow/control flow instruction execution, such as “case”, “if”, “while”, and other
instructions.

Grading note:
(1 point) - All key words similar to the prediction of “program flow/control flow/branch
instruction result”, “faster execution”, “prediction/speculation” present;
(0 point) - Otherwise
Question 7. (2 points) Describe any four key differences between SRAM and DRAM
memory types by filling-in the table below:
Possible answers:

Grading note:
(+0.5) – For every correct difference (a correct table row); at most 2 points
Computer Architecture – Final Exam Answers 2024

6

Question 8. (2 points) What is the key purpose of a CPU clock? Describe any of its
characteristic metrics with a graphical illustration.
CPU clock purpose (1-2 sentences):
To synchronize instructions execution, or inputs provision, or similar
Grading: (1 point) – if the key word “synchronize” is present
CPU clock characteristic metric (1-2 sentences with a graphical illustration):
CPU clock cycle length, or clock cycle, or clock rate, or period, or frequency

Grading: (+0.5 point) – for correct clock characteristic; (+0.5 points) – for correct
graphical illustration
Question 9. (2 points) What is the key idea of the Amdahl’s law? Provide the key
equation with its variables description. Illustrate the Amdahl’s law with a plot, for the
case of 90% of parallelizable program instructions.
The Amdahl’s law idea (1-2 sentences):
Defines a theoretical upper bound on the execution speedup thanks to an
increased number of processors/cores, for a given % of parallelizable (or
unparallizable/sequential instructions)
Grading: (0.5 points) – for correct formulation; (0 points) otherwise
The Amdahl’s law equation with the description of variables meaning:
Program given:
1) 𝒙% of instructions depend on execution results of previous instructions;
2) (𝟏𝟎𝟎 − 𝒙)% of instructions do not depend on previous ones;
Solution:
1) (𝟏𝟎𝟎 − 𝒙)% can execute in parallel upon 𝒎 cores;
2) These (𝟏𝟎𝟎 − 𝒙)% execute in parallel 𝒎 times faster;
3) According to Amdahl’s law, the runtime of such a program reduces according to:
𝒕𝟏 𝒑𝒓𝒐𝒄

𝒔𝒑𝒆𝒆𝒅𝒖𝒑 = 𝒕𝒎 𝒑𝒓𝒐𝒄𝒔 =

𝟏
𝒙$

𝟏)𝒙
𝒎

Grading:
(1 point) – if the equation and variables meaning is described correctly;
(0 points) - otherwise
The Amdahl’s law graphical plot: (specify axis labels, at least 3 data points, and plot line)
Computer Architecture – Final Exam Answers 2024

7

Grading: (+0.5 points) – the plot line is correct (for the 90% case), with all axis labels and
at least 3 data points specified
Question 10. (2 points) Below is the template of a Finite State Transition graph for a
S/R latch with its state labels and transition conditions missing. Fill-in the gaps for the
state labels and empty rectangles for transition conditions.

Grading:
(1 point) – if “S” and “R” variables are not specified for transition conditions;
(-0.25) – for every mistake in the transition condition or the state label otherwise

Computer Architecture – Final Exam Answers 2024

8

## 2024: Midterm

Files: [Fundamentals of CompArch Midterm 2024.pdf](https://glebpopov.notion.site/14ae746cceef804b8e6ad81910825cc7)


Innopolis University
Academic Year 2024/2025
Computer Architecture Course
Midterm Exam
Answers
th
25 October 2024
Duration: 60 mins

Student Full Name:
Student Telegram:
Student Group:
Exam Room:

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Optional Question 8
Total

Summary (for instructors fill)
Grade

Please write clearly your name and your solutions. What will not be understood will be
considered wrong. All answers must be provided in English, everything written in Russian
will be ignored.
This is a closed-book exam. You are not allowed to use any reference materials or electronic
equipment, apart from this booklet and pens. You are not allowed to consult any person,
otherwise you will be disqualified from this exam at the very first attempt.
Student Signature:

Midterm Exam of Computer Architecture 2024

Page 1 of 6

Question 1 (1 point). What is the key idea of Moore’s law? Provide ONE sentence answer.
Answer:
The number of transistors on a CPU chip doubles every 18-24 months, and thus a CPU speed
doubles as well.
Grading notes:
(+1) – for a fully correct answer, which includes words “doubles” or “increases twice”, as well as
“CPU” or “processor chip”.
0 – for an incorrect answer, or for an answer with some key details missing.

Question 2 (1 point). Provide any two key differences between FPGA and CPU chips:

Grading notes:
(+0.5) – for every row with correct comparison and relevant criteria;
1 point at most for this question
Midterm Exam of Computer Architecture 2024

Page 2 of 6

Na
me

Circuit

Question 3 (2 points). Below are the diagrams of standard hardware building blocks for
computer components. Specify commonly used names under the corresponding circuits:

1-to-2
Demultiplexer

2-to-4 Decoder

4-to-2 Encoder

4-to-1 Multiplexer

Grading notes:
(+0.5) – for every correctly named circuit;
(0) – for an incorrect circuit name or misspelled term.
Question 4 (2 points). What is the key difference between Harvard and Von-Neumann
computer architectures? Illustrate your answer with diagrams. Which one is used by typical
modern computers?
Answer:

Key difference (0.5 point):
Unlike Harvard, Von Neumann architecture stores program instructions and associated data
in the same system memory unit
Underline the architecture type of modern computers (0.5 point): Harvard / Von Neumann
Grading notes:
(+0.5) – for each correct diagram of considered architectures;
(+0.5) – for a correct key difference;
(+0.5) – for a correct option.
Midterm Exam of Computer Architecture 2024

Page 3 of 6

Question 5 (2 points). Choose typical ranges of performance metrics for an average
laptop/desktop computer below:
CPU
Frequency
16-32 MHz
2-4 KB
2.0-4.0 GHz

Cores Number

L1 Cache Storage

4-8
32-64
1000-2000

32 bits
32-128 KB
16 bits

System Memory
Access Speed
18-36 GB/sec
1-2 bits/sec
1-2 bytes/sec

Storage Capacity
8-32 GB
1024 MHz
16-32 bytes/sec

Volatility
Volatile
Non-volatile

Storage Device (e.g. SSD)
Access Speed
1024 MHz
0.5-2 GB/sec
0.5-2 bits/sec

Storage Capacity
250-500 GB
500-2000 TB
8-12 GB

Volatility
Volatile
Non-volatile
Can be both

Grading notes:
(+2) – if absolutely all options are correct, otherwise
(+0.65) – for every correct row, and
(0) – for every row with at least one incorrect choice.
Question 6 (2 points). Below each graphical representation, choose the corresponding
computer hardware component or peripheral device name:

CPU
CPU cooler
System memory
Solid-state drive
Communication bus
USB stick

CPU
CPU cooler
System memory
Solid-state drive
Communication bus
USB stick

CPU
CPU cooler
System memory
Solid-state drive
Communication bus
USB stick

CPU
CPU cooler
System memory
Solid-state drive
Communication bus
USB stick

CPU
CPU cooler
System memory
Solid-state drive
Communication bus
USB stick

CPU
CPU cooler
System memory
Solid-state drive
Communication bus
USB stick

Midterm Exam of Computer Architecture 2024

Page 4 of 6

Grading notes:
(+2) – if absolutely all options are correct, otherwise
(+0.1) – for every correct option.
Question 7 (2 points). Answer the following questions regarding flip-flops and S/R latches
by filling-in the following table and the time diagram below:
Question

Answer

(0.25 point) What is a flip-flop?

Flip-flop is a synchronous (sequential) logic circuit to store
one bit of data, with its output update synchronized with a
clock signal

(0.25 point) What is the key
difference of a flip-flop from a S/R
latch?

Unlike a flip-flop, the update of an output value for a S/R
latch is not synchronized with a clock signal, but updates
immediately after the change of its input signals

(1 point) Draw the flip-flop
circuit by using S/R latches and
other needed logic gates.
S/R latches can be represented
by simply rectangles with “S/R
Latch” labels.

(0.5 point) Fill-in the timing diagram below for QFinal, assuming the following pin meaning:
a) S, R, and QFinal are flip-flop input pins and the output pin, respectively;
b) CLK is a input clock signal;
c) 𝑆′, 𝑅′, and 𝑆’’, 𝑅” are the inputs of the master and slave S/R latches, respectively

Grading notes:
(+0.25) – for the correct definition of a flip-flop, which mentions that it is a memory unit for 1
bit of data, synchronous/has clock, otherwise (+0.15) – if the only one key detail is missed;
(+0.25) – for a correct key difference, that is referring to synchrononicity/clock or similar;
(+1) – for a correct flip-flop circuit, otherwise (-0.5 penalty) – for every not conceptual mistake;
(+0.5) – for a fully correct time diagram.
====================================

The end of the mandatory tasks

Midterm Exam of Computer Architecture 2024

======================================

Page 5 of 6

Question 8 OPTIONAL (1 point). Express the 2-inputs NAND logic gate through the 2-inputs
NOR gates. Support your answer with a truth table.
Grading policy:
Fill-in the answer field below only if you confirm the circuit correctness (use draft paper), otherwise:
(+ 1 point) – for a fully correct answer, if the total grade for Questions 1-7 is less than 12;
(0 point) – for an answer field left empty;
(- 1 point) – the penalty for an answer with any mistake (independently of the total grade for Questions 1-7)

Answer:
One of the possible circuit implementations:

+ Truth table corresponding to your specific implementation
Grading notes:
(+1) – for a fully correct answer, if the total grade for Questions 1-7 is less than 12;
(+0) - for an answer field left empty or answer without truth table;
(-1) – the penalty for an answer with any mistake (independently of the total grade for
Questions 1-7).

This is the end of the student book
Midterm Exam of Computer Architecture 2024

Page 6 of 6

## 2024: Pre Final

Files: [Fundamentals of CompArch Pre Final 2024.pdf](https://glebpopov.notion.site/156e746cceef80839132ef51109a29cd)


Innopolis University
Academic Year 2024/2025
Prefinal Exam of Computer Architecture
6th December 2024
Duration: 60 minutes

Student Full Name:
Student Group:
Exam Room:
Telegram Alias:
Midterm missed (underline): No / Yes

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Question 8
Total

Grade Summary (for instructors fill)
Grade

Maximum score: 12 points

Please write clearly your name and your solutions. What will not be understood will be
considered wrong. All answers must be provided in English.
This is a closed-book exam. You are not allowed to use any reference materials or electronic
equipment, apart from this booklet and pens. You are not allowed to consult any person,
otherwise you will be disqualified from this exam at the very first attempt.
Good Luck!
Signature:

Computer Architecture – Prefinal 2024

Student Full Name:

Question 1. (1 point) Choose RISC-V branch-type instruction(s) below:
a) lw

b) ld

c) sb

d) bne

e) jal

f) No choice is correct

Grading notes:
(d) – (+1) point, (e) – (+0.5), but at most 1 point;
Other options – 0 for the entire question, independently of (d), (e) options chosen
Question 2. (1 point) Choose valid characteristic(s) for RISC-V processor architecture:
1) RISC-V is a stack-based processor architecture;
2) The length of the binary representation of RISC-V processor instructions is 64 bits;
3) RISC-V processor has 64 floating-point registers;
4) The default RISC-V register storage capacity is 14 bits;
5) No choice is correct (correct)
Grading notes:
(5) – 1 point, otherwise 0 points

Computer Architecture – Prefinal 2024

Page 2 of 4

Student Full Name:
Question 3. (1 point) What logic circuit is depicted below?
Answer: Subtractor (for 2 arguments of 4 bits each)

Grading notes:
(1 point) - Correct circuit name, otherwise 0 points (a single minor grammar mistake is not
penalized)
Question 4. (1 point) Computer memory units are classified by different criteria, including
SRAM and DRAM, volatile and non-volatile, among other. For each memory type listed below,
fill-in the table by placing a cross (X) into the corresponding column with memory types.
Memory Type
CPU register
L1 Cache
L2 Cache
System Memory
SSD Storage
USB Flash Drive

SRAM DRAM Neither SRAM nor DRAM
X
X
X
X
X
X

Volatile
X
X
X
X

Non-Volatile

X
X

Grading notes: (+0.2) for every entirely correct column (not row)

Computer Architecture – Prefinal 2024

Page 3 of 4

Student Full Name:
Question 5. (2 points) The Flynn’s taxonomy identifies four computational models for
computer systems, including SISD (Single Instruction Single Data). List the remaining three
models according to the Flynn’s taxonomy in the table at the left. Then, for each processing unit
type listed, specify its corresponding Flynn’s taxonomy model in the column at the right.

1
2
3
4

Computation Model

Processing Unit
Type

Flynn’s Taxonomy
Model

SISD: Single Instruction Single Data

Single-Core CPU

SISD

SIMD: Single Instruction Multiple
Data
MISD: Multiple Instructions Single
Data
MIMD: Multiple Instructions Multiple
Data

Multi-Core CPU

MIMD

GPU

SIMD

Grading notes:
(+1) – for entirely correctly filled table at the left, otherwise (+0.3) per correct row; only
abbreviations are sufficient;
(+1) – for entirely correctly filled table at the right, otherwise (+0.3) per correct row
Question 6. (2 points) Provide the logic circuit of a 2-to-1 encoder by using AND, OR, and NOT
logic gates. Implement this logic circuit in the Verilog HDL.
Answer: One of the possible solutions:
2-to-1 Encoder Circuit

Its SystemVerilog Implementation

module (i1, i2, q)
input i1, i2;
output q;
assign q = i2;
endmodule
Grading notes: (+1) – for an entirely correct circuit; (+1) – for an entirely correct Verilog
Question 7. (2 points) RISC-V architecture identifies several types of instructions, including
R (register), I (immediate), J (jump)
For each instruction in the table below, indicate its type by placing a cross (X) into the
corresponding column:
Instruction
add
addi
ld
jal
sd

R (Register)
X

Instruction Type
I (Immediate) J (Jump)

Other (not listed)

X
X
X
X

Grading notes: (+0.4) for every correctly filled row (not column)
Computer Architecture – Prefinal 2024

Page 4 of 4

Student Full Name:
Question 8. (2 points) Below is a schematic design of a single-cycle RISC-V processor. On this
diagram, some component names are missing. Write down the following names on/near the
corresponding design components:
a) Data Memory
b) Instructions Memory
c) ALU (Arithmetic-Logic Unit)
d) Register File
e) CU (Control Unit)
f) Program Counter (PC) register
g) CPU Clock
h) “Opcode” pin (for ALU instructions
i) “Zero” pin (the one used with conditional branch instructions)
j) Branch/jump indication pin/wire (indicates the execution of a branch instruction)

Grading notes:
(+0.2) for every correctly matched name, except:
If a name is written down for several components, including an incorrect
component, then it is not counted
This is the end of the student book
Draft (will NOT be checked)

Computer Architecture – Prefinal 2024

Page 4 of 4

## 2023: Final

Files: [Fundamentals of CompArch Final 2023.pdf](https://glebpopov.notion.site/4bca0ac5d38c4ffbb576b942e9ac6c9b)


Innopolis University
Academic Year 2023/2024
Final Exam of Computer Architecture
14th December 2023
Exam Duration: 60 minutes
Student Full Name:
Student Group:
Telegram Alias:
Midterm missed (underline): No / Yes

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Question 8
Question 9
Question 10
Total

Grade Summary (for instructors fill)
Grade

Maximum score: 14 points

Please write clearly your name and your solutions. What will not be understood will be
considered wrong. All answers must be provided in English.
This is a closed-book exam. You are not allowed to use any reference materials or electronic
equipment, apart from this booklet and pens. You are not allowed to consult any person,
otherwise you will be disqualified from this exam at the very first attempt.
Good Luck!
Signature:

Computer Architecture – Final 2023

Student Full Name:

Question 1. (1 point) How many bits in one word for RISC-V processor architecture?
1 word = 32 bits
Question 2. (1 point) Choose valid characteristic(s) for RISC-V processor architecture:
a) RISC-V is an accumulator-based processor architecture;
b) The length of the binary representation of RISC-V processor instructions varies
depending on their types (such as R, I, J, etc.);
c) RISC-V processor has 16 general-purpose integer registers and 16 floating-point
registers;
d) No choice is correct – the only correct option
Note on grading:
Option “d” is chosen – (+1) point
Any other option is chosen – 0

Computer Architecture – Final 2023

Page 2 of 8

Student Full Name:
Question 3. (1 point) Briefly describe the relation between logical shift instructions, such as
“sll” and “srl” in RISC-V instruction set, to the arithmetic instructions for integer values.
Answer:
“sll” – a fast way for multiplication;
“srl” – a fast way for arithmetic division;

Notes on grading:
“sll” is for multiplication – (+0.5)
“srl” is for division – (+0.5)
(incorrect) “sll” is for division and “srl” is for multiplication – (+0.5) in total
Question 4. (1 point) Do you agree that, unlike modern desktop computers, a current
generation of smartphones typically has one processor with a single core?
a) Agree
b) Disagree – the correct option
Notes on grading:
Option “b” is chosen – 1point;
Otherwise - 0

Computer Architecture – Final 2023

Page 3 of 8

Student Full Name:
Question 5. (1 point) Instruction “mv” is an example of a RISC-V pseudo-instruction. During
the assembling stage, such instructions are replaced with so called basic RISC-V instruction(s).
Express “mv” pseudo-instruction through any other basic RISC-V instruction(s):
A possible answer:
Pseudo-instruction:
mv s1, s0

Expression in RISC-V basic instruction(s):
add s1, s0, zero

Notes on grading:
“addi” instead of “add” is not penalized;
“0” instead of “zero” is not penalized;
Other logically correct options are also accepted

Question 6. (1 points) There are two logic circuits below, Circuit 1 and Circuit 2, which are
implemented by using NAND and NOR universal logic gates, respectively. Do you agree that
these logic circuits are equivalent?
a) Agree
b) Disagree – the correct option (1 point)
Circuit 1:

Computer Architecture – Final 2023

Circuit 2:

Page 4 of 8

Student Full Name:
Question 7. (2 points) The diagram below represents a high-level organization of a RISC-V
processor. With respect to this diagram, briefly describe the key execution steps of “sub”
RISC-V instruction in the table below this diagram. On the diagram itself indicate (that is
highlight or draw) the data path corresponding to the execution of “sub” instruction of RISC-V
instruction set.

The key execution steps for “sub” instruction*:
Step
Brief Description
Number
Instruction is loaded from the Instruction Memory
1
2

Instruction data is decoded into a register file

3

Two input arguments for “sub” instruction are provided as inputs to the ALU
unit (in addition to the opther data, such as operation code). “sub” is not an
immediate-type instruction, and thus, both input arguments are taken from the
register file.
4
The execution result is loaded back into the register file bypassing the Data
Memory unit, as “sub” instruction, unlike “lw” and “sw” and related, does not use
Data Memory unit.
* It is not necessary to fill in all table rows
Notes on grading:
“sub” uses the Data Memory unit – (-0.5);
Missing register write-back link – (-0.5);
Only one input argument is provided to the ALU unit – (-0.25) if no other mistakes, otherwise
not it is not penalized;
Other mistakes – (-0.5)
Computer Architecture – Final 2023

Page 5 of 8

Student Full Name:
Question 8. (2 points) Provide four major differences between CPU and GPU processing chips:
Possible answers:

Computer Architecture – Final 2023

Page 6 of 8

Student Full Name:
Question 9. (2 points) The diagram below represents the organization of a simple memory
system comprised of a processor cache with 4 blocks and a word-addressable system memory,
with 𝑊address representing one data word stored at a certain address. System memory
addresses are five bit long.
Consider the following program, where “LW <address>” instruction loads data from a specified
system memory address into a corresponding cache block:
LW 01010
LW 01100
LW 01010
LW 11010
LW 01010
Fill in the cache table below with all data corresponding to the end of the execution of such a
program.

Notes on grading:
Every correctly filled cell – (+0.25), including a correctly chosen block;
Incorrect cell filled – (-0.25)
Computer Architecture – Final 2023

Page 7 of 8

Student Full Name:
Question 10. (2 points) The following RISC-V program counts the number of words in an input
string. Fill in the underlined gaps in the program code with appropriate labels, registers and
instructions.
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38

.data
input_msg: .asciz "Enter your string: \n"
output_msg: .asciz "Number of words: "
.text
li t0, 10
\# Load ASCII code for newline ("\n") into t0
li t1, 32
\# Load ASCII code for space (" ") into t1
li t2, 0
li a7, 4
la a0, input_msg
ecall

\# System call code for PrintString

space_loop:
li a7, 12
\# System call code for ReadChar
ecall
beq a0, t0, exit
bne a0, t1, __incr_
\# Fill in the gap
j space_loop
word_loop:
li a7, 12
\# System call code for ReadChar
__ecall__
\# Fill in the gap
beq
a0, t0, exit
__beq__ a0, t1, space_loop # Fill in the gap
j word_loop
incr:
__addi t2, t2, 1__
\# Fill in the gap
j word_loop
exit:
li __a7__, 4
\# Fill in the gap
la a0, output_msg
ecall
li a7, 1
mv a0, t2
ecall

\# System call code for PrintInt

li a7, 10
ecall

\# System call code for Exit

Notes on grading:

Every correctly filled gap — (+0.4);
Minor mistake in the assembly instruction is — (-0.2)

Computer Architecture – Final 2023

Page 8 of 8

## 2023: Midterm

Files: [Fundamentals of CompArch Midterm 2023.pdf](https://glebpopov.notion.site/0b436a42a26e49698c115a322c01dac7)


Innopolis University
Academic Year 2023/2024
Midterm Exam of Computer Architecture
2nd November 2023

Student Full Name:
Student Group:

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Question 8
Total

Grade Summary (for instructors fill)
Grade

Maximum score: 12 points

Please write clearly your name and your solutions. What will not be understood will be
considered wrong. All answers must be provided in English.
This is a closed-book exam. You are not allowed to use any reference materials or electronic
equipment, apart from this booklet and pens. You are not allowed to consult any person,
otherwise you will be disqualified from this exam at the very first attempt.
Good Luck!
Signature:

Computer Architecture – Midterm 2023

Student Full Name:
Grades Distribution:

Question 1. (1 point) Processor A has 4 cores of 2.3 GHz frequency each, processor B has 2
cores of 2.1 GHz each, and processor C has 4 cores of 2.2 GHz each. Which processor has an
“overall better performance” from a theoretical perspective?
a) Processor A (correct)
b) Processor B
c) Processor C
Note on grading:
The only correct option chosen – 1 point, otherwise 0
Question 2. (1 point) What is the major objective of a pipelined execution for processor
instructions?
a) To increase reliability through redundancy
b) To facilitate performance by speculative execution
c) To resolve underflow exceptions
d) To speed-up an overall program execution (correct)
e) To increase the energy consumption
f) To facilitate the use of two’s complement notation for signed numbers
g) No choice is correct
Note on grading:
Correct option “d” chosen – 1 point, and for every incorrect option, except “g”, penalty (-0.2)
points. If option “g” chosen – 0.
Computer Architecture – Midterm 2023

Page 2 of 6

Student Full Name:
Question 3. (1 point) Fill-in the following comparison table for S/R latch and D flip-flop
circuits:
Criteria
Storage capacity (in bits)
Output synchronization with
clock (write “yes” or “no”)
Power consumption
(write “higher” or “lower”)

S/R latch

D flip-flop
1 bit

1 bit

NO

YES

LOWER

HIGHER

Note on grading:
Mistakes in “Output synchronization…” or “Power consumption…” rows – penalty of (-0.5) for
each row. Mistakes in “Storage capacity…” – penalty of (-0.5) for each cell with incorrect value.
Question 4. (1 point) Convert decimal value "-14" into 8-bit two's complement notation for
representing signed numbers. It is mandatory to illustrate the key computation steps in the
“solution” field.
Answer:
1

1

1

1

0

0

1

0

Note on grading: ALL cells of the “Answer” field (the question requires to provide the answer
in 8-bit format) are filled with correct values (8 bits in total) and the solution is provided – 1
point, in any other case – 0.
Solution (mandatory):
a) Find the binary representation of 14: 00001110
b) Invert the bits (Change 0s to 1s and 1s to 0s): 11110001
c) Add 1 to the result: 11110010
Question 5. (2 point) What is the key difference between Von Neumann and Harvard
computer architectures? Illustrate with diagrams.
Answer:
The key difference is the following: Harvard architecture assumes two separate memory
units: one – for program instructions, and one – for program data, while Von Neumann
architecture assumes the same memory unit to be used for program instructions and data.

Note on grading:
For both architectures correct diagrams with comprehensive labeling is provided – 2 points;
No diagrams are provided, but the difference is described correctly in words – 1 point;
Mistake of any type – penalty of (-1) point;
Otherwise 0 points
Computer Architecture – Midterm 2023

Page 3 of 6

Student Full Name:
Question 6. (2 points) Name at least 4 key differences between CPU and FPGA chips.
Some possible answers are the following:

Notes on grading:
Every correct (out of 4) comparison is 0.5 points, and partially incorrect formulation is 0.25
points
Question 7. (2 points) Consider the following logic circuit:

Draw the signal curve in the timing diagram below for 𝑄!"#$% output pin:
Answer:

Computer Architecture – Midterm 2023

Page 4 of 6

Student Full Name:
Notes on grading:
A fully correct diagram – 2 points;
As well as these only two diagrams are considered as partially correct and graded with 1
point:

Question 8. (2 points) Provide the logic circuit of 2-to-4 decoder by using AND and NOT logic
gates. Describe such a logic circuit design in Verilog HDL
Logic circuit design

Verilog HDL implementation
module decoder2x4 (
input wire [1:0] in
output reg [3:0] out
);
always @ (*) begin
case (in)
2'b00: out = 4'b0001;
2'b01: out = 4'b0010;
2'b10: out = 4'b0100;
2'b11: out = 4'b1000;
endcase
end
endmodule

Computer Architecture – Midterm 2023

Page 5 of 6

Student Full Name:
Notes on grading:
Both correct: Logic circuit + Verilog design = 1 + 1 points = 2 points in total;
A fully correct logic circuit – 1 point, any mistake (even minor) in logic circuit is penalized
with (-1) point;
A fully correct Verilog HDL design – 1 point, otherwise Verilog errors are penalized as follows:
No proper module declaration – (-0.5 points);
Minor mistakes related to module declaration – (-0.2 points);
Misuse of always, case, assign, if statements – (-0.4 points);
Misuse of “begin/end” constructs – (-0.2 points);
Misuse of logic gates declarations, missing declarations of wires and related – (-0.2
points);
Other minor syntax mistakes – (-0.2 points)
Misuse or lack of “reg” keyword, missing “;” in the line ends – not penalized

This is the end of the student book
Draft (will NOT be checked)

Computer Architecture – Midterm 2023

Page 6 of 6

## 2023: Pre Final

Files: [Fundamentals of CompArch Pre Final 2023.pdf](https://glebpopov.notion.site/5e4fe4cd4dfe43439d6470c9c3aecf15)


Innopolis University
Academic Year 2023/2024
Prefinal Exam of Computer Architecture
7th December 2023
Exam Duration: 75 minutes

Student Full Name:
Student Group:
Telegram Alias:
Midterm missed (underline): No / Yes

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Question 8
Question 9
Total

Grade Summary (for instructors fill)
Grade

Maximum score: 14 points

Please write clearly your name and your solutions. What will not be understood will be
considered wrong. All answers must be provided in English.
This is a closed-book exam. You are not allowed to use any reference materials or electronic
equipment, apart from this booklet and pens. You are not allowed to consult any person,
otherwise you will be disqualified from this exam at the very first attempt.
Good Luck!
Signature:

Computer Architecture – Prefinal 2023

Student Full Name:
Distribution of grades:

Question 1. (1 point) Briefly describe the purpose of the PC special-purpose processor
register in RISC-V architecture.
Answer:
PC (Program Counter) special purpose register is used to store the address of the next
instruction to be executed by a CPU (or the address of a currently executing instruction by a
CPU).
Note on grading:
Partially correct answer – (+0.5)

Question 2. (1 point) Choose valid characteristic(s) for RISC-V processor architecture:
1) RISC-V is a stack-based processor architecture;
2) The length of the binary representation of RISC-V processor instructions is 32 bits;
3) RISC-V processor has 32 floating-point registers
Answer: Choices 2 and 3 are correct.
Notes on grading:
Every correct option – (+0.5)
An incorrect option “1” – (-0.5)
Computer Architecture – Prefinal 2023

Page 2 of 6

Student Full Name:
Question 3. (1 point) Do you agree that in all modern computer architectures the same L1
cache is shared by multiple CPU chips?
1) Agree
2) Disagree
Answer: Option “2” is correct.

Question 4. (1 point) In the list below, choose pseudo instruction(s) for RISC-V processor
architecture:
1) addi
2) mv
3) lw
4) sb
5) No choice is correct
Answer: Option “2” is correct.
Notes on grading:
Option “2” – (+1)
Options “1”,”3”,”4” – (-0.2) each
Option “5” – (-1)

Question 5. (1 point) A classical data path representation for RISC-V processors typically
contains PC register, instruction memory, register file, ALU, and data memory. In the list below,
choose instruction(s), which do not use data memory:
1) add
2) sub
3) lw
4) beq
5) No choice is correct
Answer: Options “1”, “2”, and “4” are correct.
Notes on grading:
Options “1”, “2”, “4” – (+0.33) each;
Option “3” – (-0.33);
Option “5” – (-1)

Computer Architecture – Prefinal 2023

Page 3 of 6

Student Full Name:
Question 6. (2 points) Flynn’s taxonomy identifies four major types for computer
architectures. List all these types together with the corresponding examples for each type.
A possible answer:

Notes on grading:
Correct Flynn’s type name – (+0.25) each;
Correct example per type – (+0.25) each;
A partially correct example – (+0.125)
Question 7. The diagram below represents the organization of a simple processor cache.
Assume that such a cache contains eight cache blocks, with each block corresponding to a single
data word from the system memory. Answer the following questions:
(1 point) Fill in the missing names of the cache block fields in the grey cells below.
(2 points) Let one word of data denoted by 𝑊 having system memory address 11110101 be
loaded from the system memory into such a cache. Fill in all values in the corresponding cache
block entry/entries of the diagram below with 𝑊 denoting the data loaded from the system
memory.
Block
Index
000
001
010
011
100
101
110
111

Validity
Flag

Y

Address Tag

11110

Computer Architecture – Prefinal 2023

Data Words

W

Page 4 of 6

Student Full Name:

Notes on grading:
Correct field name – (+0.33) each;
Partially correct field name – (+0.2);
Incorrect field name – (0)
Incorrect block entry filled – (-0.5);
Incorrect field value – (-0.5) each
Question 8. (1+1 points) Draw a high-level conceptual diagram illustrating the key aspects of
a CPU-GPU heterogeneous computer architecture with a focus on the memories system
organization (do not draw the details regarding the internal organization of GPU processor chip
itself).
Then, by relying on such a diagram, describe the data flow details corresponding to the
following scenario. First, there is some program data loaded into the main system memory. This
program data must be processed by the GPU processor chip (and not by CPU). Briefly describe
the data flow steps for such a GPU execution case, including the stage of storing the computation
result.
Answer:

Notes on grading:
CPU, GPU, System Memory, GPU Memory units drawn with correct connections – (+0.25)
each;
Description of the key data flow steps – (+1);
Data flow arrows without descriptions – (+0.5)

Computer Architecture – Prefinal 2023

Page 5 of 6

Student Full Name:
Question 9. (2 points) Write a RISC-V assembly language program for computing the factorial
of a given positive value n. Assume that an input value n is already loaded into register s0, as
well as the computation result should be stored into register s1. Fill in the missing code.
A possible answer:

Notes on grading:
Minor incorrections are not penalized;
Minor logic mistakes – (-0.5) each;
Major logic mistake – (-1) each;
Incorrect instructions, instructions misuse, misuse of registers – (-0.5) each
This is the end of the student book
Draft (will NOT be checked)

Computer Architecture – Prefinal 2023

Page 6 of 6

## 2022: Final

Files: [Fundamentals of CompArch Final 2022.pdf](https://glebpopov.notion.site/e645811e3f734b8d9ccf6dc571a9d6d5)


Innopolis University
Academic Year 2022/2023
Final Exam of Computer Architecture
15th December 2022
Exam Duration: 60 minutes

Student Name:
Student Email:
Student Group:

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Total (max: 12 points)

For Instructors Use: Grade Summary
Grade

Please write very clearly your names and your solution. What will not be understood
will be considered wrong.
You need to perform this exam alone and without the use of any equipment or book, apart
from this booklet and pens. Please do not consult any person or use any equipment, otherwise
you will be disqualified from this exam at the very first attempt.
Student’s signature:

Student Name:

Computer Architecture – Final Exam 2022

Page 2 of 8

Student Name:
Question 1. (1 point) For each memory unit listed below, identify its type – “SRAM” or
“DRAM”:
a) Main System Memory: _____DRAM______
b) CPU Cache: _____SRAM_____

Question 2. (1 point) There are several types of RISC-V processor instructions available,
including “R”, “I”, “J”, and others. What is the type of “addi” RISC-V processor instruction?
Answer: ___I___

Question 3. (1 point) Do you agree that the storage capacity of L1 cache for modern CPUs
typically significantly exceeds 8 GB?
Answer:
a) Agree
b) Disagree - Correct

Question 4. (1+1 points) Briefly describe the major difference between Von Neumann and
Harvard computer architectures. Provide conceptual diagrams illustrating such a difference.
Answer:
The major difference: Unlike Harvard architecture, Von Neumann architecture assumes that
both program instructions and data are stored in the same memory unit.

Computer Architecture – Final Exam 2022

Page 3 of 8

Student Name:
Question 5. (1+1 points) Briefly describe the major difference between Half Adder and Full
Adder computation circuits. Provide implementations for each of these circuits by using XOR,
AND, and OR logic gates (the use of NOT and other logic gates is prohibited).
Answer:
The key difference: Unlike Full Adder, Half Adder computation circuit does not take carry-in
value (for addition operation), and is used for adding the least significant bits of input
arguments.

Computer Architecture – Final Exam 2022

Page 4 of 8

Student Name:
Question 6. (1+1 points) Describe the purpose and the main principles of a function calling
convention. Which data does a function stack frame contain?
Answer:
The answer should be based on the following slides.
The purpose and the main principles of a function calling convention:

Slide related to data, which is contained in a function call frame:

Computer Architecture – Final Exam 2022

Page 5 of 8

Student Name:
Question 7. (1 x 3 points) Describe the specific properties and differences for the following
processor architectures: register-set based, accumulator-set based, and stack-based.
Answer:
The answers should be based on the following slides:

Computer Architecture – Final Exam 2022

Page 6 of 8

Student Name:

This is the end of the student book
Computer Architecture – Final Exam 2022

Page 7 of 8

Student Name:
Draft (will not be checked)

Computer Architecture – Final Exam 2022

Page 8 of 8

## 2022: Midterm

Files: [Fundamentals of CompArch Midterm 2022.pdf](https://glebpopov.notion.site/0dd5ac48d9834c7fb2220183d576caad)


Student Name:
Student email:

Innopolis University
Academic Year 2022/2023
Midterm Exam of Computer Architecture
27th October 2022

Student Name:
Student email:

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Total

Grade Summary (for instructors fill)
Grade

Maximum score: 14 points

Please write very clearly your names and your solution. What will not be understood will be
considered wrong. All answers must be provided in English.
You need to perform this exam alone and without the use of any equipment or book, apart
from this booklet and pens. Please do not consult any person or use any equipment, otherwise
you will be disqualified from this exam at the very first attempt.
if you need to leave the room during the written part of the exam, you will not be able to
return to the written exam.
Good Luck!
Signature:

Computer Architecture – Midterm 2022

Page 1 of 11

Student Name:
Student email:

Grades Summary for the Midterm Exam

Computer Architecture – Midterm 2022

Page 2 of 11

Student Name:
Student email:
Question 1. (1 point) Do you agree that L2 processor cache is typically faster than L1
processor cache? (Choose one)

mputer Architecture
a) Agree

b) Disagree

CPU
Increasing
memory
access
speed

Cache L1
…

Cache L(i)
System Memory

Remote Storage Devices

Increasing
storage
capacity

(SSD Disk, NAND Flash Memory, others)

4

Computer Architecture – Midterm 2022

Page 3 of 11

Student Name:
Student email:
Question 2. (1 point) What is the key idea of Moore’s law? (Choose one)
a) The storage capacity of L1 cache doubles roughly every two years
b) The number of transistors on a processor chip doubles roughly every 2 years,
and consequently, a processor speed doubles roughly every two years as well
c) The number of processor cores in a computer doubles roughly every two years

The number of transistors on a CPU chip doubled every 18-24 months until ~2010 (?)
(leading to an increased CPU speed).

Moore’s Law Stagnation

CPU speed and
single-thread
performance seem
not to increase
since ~2008

The number of cores
increases instead

10

Image is taken from https://www.quora.com/Why-is-Moores-law-no-longer-valid

Computer Architecture – Midterm 2022

Page 4 of 11

Student Name:
Student email:
Question 3. (1 point) Choose valid statement for RISC-V processor architecture:
(Choose one)
a) RISC-V is an example of a stack-based processor architecture
b) RISC-V has 32 directly addressable integer registers
c) The length of a binary representation of RISC-V processor instructions is 128 bits
d) No choice is correct
RISC-V is a load/store architecture (not stack-based!), that is all instructions, except memory
access, operate on registers

RISC-V Registers
32 directly addressable integer registers:
- Have their names (x0..x31)
- 64 bits per register, by default
- Directly addressable
- Reserved for different purposes

Clock

PC

x0

x4

…

…

Integer Registers

x19

…

x31

: Floating-Point Registers for RISC-V Architecture

Other (floating point and special-purpose) registers are available as well:

4

Program Counter
special-purpose
register
Clock

PC

x4

x0

…

x19

x31

Integer Registers

f0

f1

f2

…

f31

Floating-Point Registers
(to deal with floating-point instructions)

Computer Architecture – Midterm 2022

Page 5 of 11

Student Name:
Student email:
Question 3. (1 point) Choose valid statement for RISC-V processor architecture:
(Choose one)
a) RISC-V is an example of a stack-based processor architecture
b) RISC-V has 32 directly addressable integer registers
c) The length of a binary representation of RISC-V processor instructions is 128 bits
d) No choice is correct

Some Types of RISC-V Instructions: R, I, and S
All RISC-V instructions are 32 bit long in their binary representation;
The difference is in the number of fields, their meaning, and sizes

R-type

funct7

rs2

rs1

funct3

rd

opcode

add, sub, …

rs1

funct3

rd

opcode

addi, ld, …

rs1

funct3

imm[0:4]

opcode

sd, …

(“register”, or “regular”)

I-type

immediate

(“immediate”)

S-type

immediate[11:5]

rs2

(“store”)

32 bits (1 RISC-V word, a total instruction length)

57

Computer Architecture – Midterm 2022

Page 6 of 11

Student Name:
Student email:
Question 4. (2 point) What is a Program Counter (PC) register of a processor?
Answer:

Program
Counterfor
(PC)RISC-V
register
– the register containing the index/address of a program
p: Floating-Point
Registers
Architecture

instruction being executed by a processor at a current time (or of the next instruction to be
executed)

Program Counter
special-purpose
register
Clock

PC

x4

x0

…

x19

x31

Integer Registers

f0

f1

f2

…

f31

Floating-Point Registers
(to deal with floating-point instructions)

Computer Architecture – Midterm 2022

7

Page 7 of 11

Student Name:
Student email:
Question 4. (2 point) What is a Program Counter (PC) register of a processor?
Answer:
Program Counter (PC) register – the register containing the index/address of a program
instruction being executed by a processor at a current time (or of the next instruction to be
executed)
PC-relative addressing:
This mode can be used to load a register with a value stored in program memory
Target address = PC + offset × 4 (each RISC-V instruction takes 4 bytes)
PC already incremented by 4 by this time
Datapath
PC register
in CPU
circuit design (more details will be studied later):
Simplified
view:

NOTE:

Datapath and Control Signals

PC is Program Counter. It is also known as instruction pointer.

Final view:
Details on the circuit above will be provided later in tutorials
A. Tormasov

5 / 48

NOTE: More details in later tutorials
A. Tormasov

Computer Architecture – Midterm 2022

11 / 48

Page 8 of 11

Student Name:
Student email:
Question 5. (2 points) Latency and throughput are two performance metrics for computers.
Briefly describe what latency is, and what throughput is, illustrating with (an) example(s).
Answer:
Latency (or response time): How long does it take for a job to run?

Latency vs. Throughput:
Throughput: How many jobs
machine can run at once?
Interpretation

The image is taken from:
http://avinashmaurya.com/a-primer-on-GPGPU/
Latency - a time delay between the cause and the start of the effect:
A. Tormasov

•
•
•

13 / 48

Synonym to ”delay” and ”response time”
But not ”execution time”! The latter includes ”latency” together with additional timing
overheads;
A precise definition depends on the context

Note:
We cannot say what is better, having a higher latency or having a higher throughput. It is
implementation dependent. Different applications might require different criteria.

Computer Architecture – Midterm 2022

Page 9 of 11

Student Name:
Student email:
Question 6. (3 points) Translate the following pseudocode expression into RISC-V code:
𝑓 = ℎ − 𝑚𝑦𝐴𝑟𝑟𝑎𝑦[20] + 7
Assume that 𝑚𝑦𝐴𝑟𝑟𝑎𝑦 denotes the array of long long int elements (having size of 64 bits, or
“double word”, each).
Assume the following registers assignment:
Register 𝑠0 – for variable ℎ
Register 𝑠1 – for the base address of array 𝑚𝑦𝐴𝑟𝑟𝑎𝑦
Register 𝑠2 – for variable 𝑓
Assume that variables ℎ and 𝑓 are declared as long long int type (meaning that they take 64
bits each), value of variable ℎ is already loaded into register 𝑠0, and the base address of
𝑚𝑦𝐴𝑟𝑟𝑎𝑦 is already loaded into register 𝑠1.
Answer:

A possible implementation (out of many other):

ld
t0, 160(s1)
sub s0, s0, t0
addi s2, s0, 7

Computer Architecture – Midterm 2022

Page 10 of 11

Student Name:
Student email:
Question 7. (4 points) What is a transparent S/R latch? Specify the truth table of a S/R latch.
Draw the logic circuit of a S/R latch by using NAND and NOT logic gates. Provide a finite state
machine for a S/R latch, demonstrating the transitions between its states.
Answer:
A transparent S/R latch – a digital circuit to store 1 bit of information.
Truth table:
S, R – inputs
Q – output
S = 1, R = 0, then Q = 1
S = 0, R = 1, then Q = 0
S = 0, R = 0, then Q = Qprev
S = 1, 

(the rest is in the file)

## 2022: Pre Final

Files: [Fundamentals of CompArch Pre Final 2022.pdf](https://glebpopov.notion.site/16636d99e6ce4fa090854e154f36ea56)


Innopolis University
Academic Year 2022/2023
Prefinal Exam of Computer Architecture
08th December 2022
Exam Duration: 60 minutes

Student Name:
Student Email:
Student Group:

Question
Question 1
Question 2
Question 3
Question 4
Question 5
Question 6
Question 7
Total (max: 12 points)

For Instructors Use: Grade Summary
Grade

Please write very clearly your names and your solution. What will not be understood
will be considered wrong.
You need to perform this exam alone and without the use of any equipment or book, apart
from this booklet and pens. Please do not consult any person or use any equipment, otherwise
you will be disqualified from this exam at the very first attempt.
Student’s signature:

Student Name:

Grades Summary for the Pre-Final Exam

Computer Architecture - Prefinal

Page 2 of 7

Student Name:
Question 1. (1 point) Do you agree that, according to "a memory wall problem", the key
performance bottleneck of modern computer platforms is a slow memory access speed,
rather than a slow CPU execution speed?
Select one:
• True - correct
• False

Question 2.
Note: This question was graded “correct” to all students (due to typo in RISC-V
instruction name, “sll” should be “slli”)
(1 point) Assume that two RISC-V processor integer registers, t0 and t1, contain the following
binary data (for simplicity, we assume 8-bit registers, rather than 32):
t0:
t1:

00100000
01010101

What is the value of register t1 after the execution of the following RISC-V instruction?:
sll t1, t0, 3
Answer:

Question 3. (1 point) Convert decimal value "-4" into 4 bit one's complement notation for
representing signed numbers.
Answer:

1 0 1 1

Question 4. (1+1 points) What is a “universal logic gate”? Provide the names of two universal
logic gates.
Answer:
A universal logic gate is the one, which can be used to implement any other logic gate

2 examples of universal logic gates:

NAND

NOR

(XOR without constant “1” is considered incorrect)

Computer Architecture - Prefinal

Page 3 of 7

Student Name:
Question 5. (2 points) Briefly describe at least 4 key differences between CPU and GPU
computer units.
Answer:
Possible (but clearly not all) differences are summarized in the table below.
Multicore CPU / Multiprocessor GPU
Data parallelism
Task parallelism
Parallelism Type
(A small set of relatively simple
(A concurrent execution of
Supported
totally different programs/tasks) operations repeated over large volumes
of data)
Single Instruction Multiple Data (SIMD)
Parallelism Model
Multiple Instructions Multiple
Single Instruction Multiple Threads
(Flynn’s taxonomy)
Data (MIMD)
(SIMT)
Efficient for multitasking
Efficient for processing large volumes of
Target
Inefficient for processing large
data Less efficient for multitasking
volumes of data
Cores Number
Several (~2-10) cores
Multiple (~100s) smaller cores
~10s of relatively heavyweight ~10’000s of lightweight threads on
Parallelism Scope
threads on ~10s CPU cores
~100s/1000s of GPU cores
Each thread is managed and
Threads are managed and scheduled by
Thread Management
scheduled explicitly
hardware by means of threads groups
Each thread is programmed
Threads are programmed in batches (by
Thread Programming
individually
using kernels)

Computer Architecture - Prefinal

Page 4 of 7

Student Name:
Question 6. (1+1 points) Provide a circuit implementation of 2-to-4 demultiplexer by using
AND, OR, and NOT logic gates (use all or only some of them). Provide implementation of such
a circuit in Verilog HDL.
Answer:
Circuits assumed to be correct:
2-to-4 demultiplexer, 2-to-4 decoder, or 1-to-4 demultiplexer
2-to-4 decoder:

1-to-4 demultiplexer:

2-to-4 demultiplexer:

One of the possible Verilog implementations:

Computer Architecture - Prefinal

Page 5 of 7

Student Name:
Question 7. (1 x 3 points) Briefly describe three major types of CPU pipeline hazards,
together with conceptual illustrations helping to understand your answers. For each hazard
type, provide at least one solution.
Answer:
Hazard types: structural, data, control
Structural hazard – hazard caused by attempt to use the same (hardware) resource by two
or more instructions at the same time

Solutions:
•
•

Stall cycle – the delay the second access by one clock cycle, or
provide separate memories for instructions and data ( “Harvard Architecture”)

Computer Architecture - Prefinal

Page 6 of 7

Student Name:
Data hazard – caused by an attempt to use data before it is ready
Example:

Solutions:
•
•
•

Forwarding
Stalling
Compiler Scheduling

Control Hazards – caused by an attempt to make branching decisions before branch
condition is evaluated

Solutions:
• Stalls
• Branch Prediction / Compiler directives (e.g. likely-unlikely) (for the minimization of
misprediction cases)
Computer Architecture - Prefinal

Page 7 of 7

## 2021: Midterm

Files: [Fundamentals of CompArch Midterm 2021.pdf](https://glebpopov.notion.site/e50c526f036944dea00ba7b36aca0b6a)


e
i

Student Name:
Student email

Question 1. (1 point) Consider the logic circuit depicted below, which is implemented by using

NOR universal logic gates:

What is the corresponding logic gate among the following, which corresponds to the circuit
above? ”

O [

) XOR,
-

Question 2, (1 point) Choose valid statement(s) for MIPS32 processor architecture:

a) MIPS32 is a CISC architecture

®) The storage capacity of each MIPS32 register is 32 bytes
¢) MIPS32 is a load/store architecture

d) No choice is correct (]

Question 3. (1 point) Consider MIPS registers listed below. Which register(s) is reserved for a
system call (“syscall”) code?

$s0 $s1 $t7 ($v0) $a3  Ssp |

~pf

TIT,OI ¢ Question 4. (1 point) For each processor architecture listed below, specify its respective type
~ CISC or RISC:
MIPS: RISC
Intel x86: CISC
ARM: RISC

Computer Architecture - Midterm 2021 Page 2 of 6

AL\ N Ao

Student Name:
Student email:

We use #w outhatechure i ot

Question 5.
What is (he(zepoénu) Briefly describe at least 2 major principles of Von Neumann architecture.
y difference between Von Neumann and Harvard architectures; illustrate with

conceptual diagrams
’ng)'re ; dada ""/

one place
13 kJ PrmtIPlef

5&3

‘ 00;‘)\1_ Ll

[

[ $ystem menior / yigE [ .
Kud priceip (%
Tnstuelion gwve ceparale

n 6. (3 points) Translate the following pseudocode expression into MIPS assembly code;
f=@+h/p=7

Assume the following registers assignment:

Questio:

$s0-for g
$s1-forh
$s2 - forp
$s3 - for f
Assume that all variables are restricted to integers, and values for variables g, h, and p are

already loaded into respective MIPS registers. Assume “/" to denote integer division.

aAdA $4p £, $s,

Computer Architecture - Midterm 2021 Page 3 of 6

e e

i

Slael oot shachere

us 28" Se ppor funchion,
cedls ﬂm S
ahd 4

Values whith we puad i
frofrom

Student Name:
Student email:

Question 7. (3 points) Provide the logic circuit for 2-to-1 multiplexer implemented by v
AND, OR and NOT logic gate types.

inf“LrLA:@

Question 8. (3 points) Explain how a stack data structure is used to support . cti
computer program. Briefly explain the notion of a stack frame and types of data it
conceptual diagrams to support/illustrate your answer.

Student Name:
Student emaijl;

Question 9,

(4 points) peser,
Provide the

circuit for addin

ibe the differenc,
8 2-bit two input arguments.

¢ J 9,’\' v
i cor*d”
, 9

e between half-adder and full-adder logic circuits.

This is the end of the exam paper

Page 5 of 6
Computer Architecture - Midterm 2021

e

## 2020: Midterm

Files: [Fundamentals of CompArch Midterm 2020.pdf](https://glebpopov.notion.site/6fcb4a886d244f609f9899876b8f5d5f)


Innopolis University
Academic Year 2019/2020
Midterm Exam of Computer Architecture
34 October 2019
Questions
Max 10 points + 3 points (30%) extra credit
Total time: 60 minutes

1. (1 point) Briefly describe the principles of Von Neumann architecture. Illustrate with a diagram.

2. (2 points) Translate the following MIPS code to C (or pseudocode). Assume that variables f, g, h,
and i are assigned to registers $s0, $s1, $s2, and $s3, respectively.

sub  $t0, $s1, $s2
addi  $t0, $t0, 3
add  $s0, $s3, $t0

3. (3 points) Describe the steps that transform a program written in a high-level language such as C
into a representation that is directly executed by a computer processor. Illustrate with a diagram;
provide a brief description for each step.

4. (4 points) Prove that the AND and NOT logic gates can be implemented by using only the NOR logic
gate.

5. (3 points - 30% extra credit) Consider three different processors P1, P2, and P3 executing the same
instruction set. P1 has a 3 GHz clock rate and a CPI of 1.5. P2 has a 2.5 GHz clock rate and a CPI of 1.0.
P3 has a 4.0 GHz clock rate and has a CPI of 2.2. Answer the following questions:

a) Which processor has the highest performance expressed in instructions per second?

b) If the processors each execute a program in 10 seconds, find the number of cycles and the
number of instructions.

c) We are trying to reduce the execution time by 30% but this leads to an increase of 20% in the
CPI. What clock rate should we have to get this time reduction?

Hint: To simply computations, consider that 1/2.2 = 0.45and 1/7 = 0.14

This is the end of the questions of the exam.

## 2020: Pre Final

Files: [Fundamentals of CompArch Pre Final 2020.pdf](https://glebpopov.notion.site/540d5c91a3e047a19b3333ba4ddefbd0)


11/27/21, 9:04 PM

Pre-Final: Attempt review

Dashboard / My courses / [F20]FoCA / Week 14 - 03 December 2020 / Pre-Final

Started on Thursday, 3 December 2020, 12:41 PM
State

Finished

Completed on Thursday, 3 December 2020, 1:31 PM
Time taken 49 mins 29 secs
Grade 76.50 out of 100.00
Question 1
Correct
Mark 3.00 out of 3.00

Please select the “True” if the following statement is true otherwise “False.”
Loader is a system program, that combines independently assembled machine language programs and resolves all undefined
labels into an executable file.

Select one:
True
False 

The correct answer is 'False'.

Question 2
Correct
Mark 3.00 out of 3.00

Which parallel programming model(s) exist(s)?
Select one or more:
a. Single Instruction, Multiple Threads



b. Single Instruction, Multiple Data



c. Simultaneous Multithreading



d. None of the above

Your answer is correct.
The correct answers are: Single Instruction, Multiple Threads, Single Instruction, Multiple Data, Simultaneous Multithreading

https://moodle.innopolis.university/mod/quiz/review.php?attempt=51092&cmid=45937

1/13

11/27/21, 9:04 PM

Pre-Final: Attempt review

Question 3
Partially correct
Mark 2.00 out of 3.00

Which of those statements about RISC is/are FALSE?
Select one or more:
a. Pipelining is easy
b. It has many specialized instructions, some of which may only be rarely used in practical programs
c. It simplifies the processor by efficiently implementing only the instructions that are frequently used in programs, while the
less common operations are implemented as subroutines
d. Complexity lies in microprogram



e. Emphasis on hardware



Your answer is partially correct.
You have correctly selected 2.
The correct answers are: Complexity lies in microprogram, It has many specialized instructions, some of which may only be rarely
used in practical programs, Emphasis on hardware

Question 4
Incorrect
Mark 0.00 out of 3.00

Select types of hazards in a pipelined processor
Select one or more:
a. Control hazards



b. Structural hazards



c. Pipeline hazards



d. Data hazards



Your answer is incorrect.
The correct answers are: Structural hazards, Data hazards, Control hazards

Question 5
Incorrect
Mark 0.00 out of 3.00

Please select the “True” if the following statement is true otherwise “False.”
An edge-triggered clocking methodology means that any values stored in a combinational logic element are updated only on
a clock edge, which is a quick transition from low to high or vice-versa.
Select one:
True 
False

The correct answer is 'False'.

https://moodle.innopolis.university/mod/quiz/review.php?attempt=51092&cmid=45937

2/13

11/27/21, 9:04 PM

Pre-Final: Attempt review

Question 6
Correct
Mark 3.00 out of 3.00

Please select the “True” if the following statement is true otherwise “False.”
Caching can be considered as an example of one of the great ideas of prediction.

Select one:
True 
False

The correct answer is 'True'.

Question 7
Incorrect
Mark 0.00 out of 3.00

What about the following statement: is it correct for a load instruction?
MemtoReg should be set to cause the correct register destination to be sent to the register file.
Refer to the following diagram:

Select one:
True 
False

The correct answer is 'False'.

https://moodle.innopolis.university/mod/quiz/review.php?attempt=51092&cmid=45937

3/13

11/27/21, 9:04 PM

Pre-Final: Attempt review

Question 8
Incorrect
Mark 0.00 out of 3.00

Please select the “True” if the following statement is true otherwise “False.”
In most computer systems, the memory is a true hierarchy, meaning that data cannot be present in level i unless it is also present
in level i + 1.

Select one:
True
False 

The correct answer is 'True'.

Question 9
Correct
Mark 3.00 out of 3.00

Please select the “True” if the following statement is true otherwise “False.”
In memory hierarchy structure the distance from the processor increases, the size of the memories and the access time both
increase.

Select one:
True 
False

The correct answer is 'True'.

Question 10
Correct
Mark 3.00 out of 3.00

Select the arithmetic-logical instructions in MIPS:
Select one:
a. beq, j
b. add, sub, AND, OR, and slt



c. lw, sw

Your answer is correct.
The correct answer is: add, sub, AND, OR, and slt

https://moodle.innopolis.university/mod/quiz/review.php?attempt=51092&cmid=45937

4/13

11/27/21, 9:04 PM

Pre-Final: Attempt review

Question 11
Correct
Mark 3.00 out of 3.00

Please select the “True” if the following statement is true otherwise “False.”
The term cache is also used to refer any storage managed to take advantage of locality of access.

Select one:
True 
False

The correct answer is 'True'.

Question 12
Incorrect
Mark 0.00 out of 3.00

Which of those statement(s) about decoders is/are FALSE?
Select one or more:
a. Decoder has an n-bit input and 2*n outputs
b. Decoder is a logic block



c. All of the above

Your answer is incorrect.
The correct answer is: Decoder has an n-bit input and 2*n outputs

Question 13
Correct
Mark 3.00 out of 3.00

Which instruction field(s) is/are contained in MIPS I-format Instructions?
Select one or more:
a. Function code (funct)
b. Destination register number (rd)
c. Target register number (rt)



d. Operation code (op)



e. Source register number (rs)



f.



Constant or address

Your answer is correct.
The correct answers are: Operation code (op), Source register number (rs), Target register number (rt), Constant or address

https://moodle.innopolis.university/mod/quiz/review.php?attempt=51092&cmid=45937

5/13

11/27/21, 9:04 PM

Pre-Final: Attempt review

Question 14
Correct
Mark 3.00 out of 3.00

Which of those statement(s) about D-latch is/are FALSE?
Select one or more:
a. D-latch has 3 inputs



b. If CLK is 0, Q holds its previous value
c. D-latch can be built based on SR-latch
d. D-latch is made of 2 SR Latches



e. If CLK is 1, Q holds its previous value



Your answer is correct.
The correct answers are: D-latch is made of 2 SR Latches, D-latch has 3 inputs, If CLK is 1, Q holds its previous value

Question 15
Correct
Mark 13.00 out of 13.00

Translate the below statement into MIPS assembly language instruction. You can assume that counter is the label of an integer
(one 32-bit word) stored in main memory.

counter++;

Select one:
a.

b.



c.

Your answer is correct.

The correct answer is:

https://moodle.innopolis.university/mod/quiz/review.php?attempt=51092&cmid=45937

6/13

11/27/21, 9:04 PM

Pre-Final: Attempt review

Question 16
Incorrect
Mark 0.00 out of 3.00

Please select the “True” if the following statement is true otherwise “False.”
All unconditional jumps are considered as taken branches.
Select one:
True
False 

The correct answer is 'True'.

Question 17
Incorrect
Mark 0.00 out of 3.00

What about the following statement: is it correct for a load instruction?
MemtoReg should be set to cause the data from memory to be sent to the register file.
Refer to the following diagram:

Select one:
True
False 

The correct answer is 'True'.

https://moodle.innopolis.university/mod/quiz/review.php?attempt=51092&cmid=45937

7/13

11/27/21, 9:04 PM

Pre-Final: Attempt review

Question 18
Correct
Mark 3.00 out of 3.00

Please select the “True” if the following statement is true otherwise “False.”
Temporal locality principle states that if a data location is referenced then it will tend to be referenced again soon.

Select one:
True 
False

The correct answer is 'True'.

Question 19
Correct
Mark 3.00 out of 3.00

What is the difference between jump and branch instructions
Select one or more:
a. Branch instructions are all pseudo-instructions, but jump is not
b. Jumps doesn’t have conditions



c. Branch is an alias for jump
d. Jump can make bigger $pc shifts



Your answer is correct.
The correct answers are: Jump can make bigger $pc shifts, Jumps doesn’t have conditions

Question 20
Correct
Mark 3.00 out of 3.00

Please select the “True” if the following statement is tr

(the rest is in the file)

## 2019: Final

Files: [Fundamentals of CompArch Final 2019.pdf](https://glebpopov.notion.site/19acb3b114b146de86ae8e165750a767)


lnnnsmll c;; Unl\•rr"lt.Y
1\t .1d l' m lr Yr.1 r 2 01 'l /2 0 l0
nn.111-:-.;,H n nf (o mpur c r ,\rchit cclurt:'
ZR'" No\·emhcr 20 1<l

Qu c .~lion~
M.n IO point-. + 1 polnrs ( 30% ) cxtr.1 credit
Tnt.11 lime : 60 minute s

- 1 11 point) 1\ , •, ttnH· th.it l\V\l \ I IF''- rc:~1'ilt:r'-. S., o ,ind Ss l cont.1 1n th e tn llow, n ~ h1 11.1r;. J .lt.1
!f111 " ""f1l1, 11 ) W(' ·'""'lnll' B-hll rcg1qcrs r.1rhcr th ,1t]ZJ
'J. c; tl
',,; (

Oil l llll()(Hl
fl\ tllflllll

Wh.11 1., 1Jw ,·.dtt <' n l regis t er Ss 1 .1tt cr 1hc C'\Cl°\1 !1011 o l the tnllowin~ ~IIPS instnll11n n '

)( L 12 p111 11t , ) Hril'll v de-,cribl' thl· key d1ffcrC'11cc(s) hl't\\C<'n cnmh,n.1t1on.1I .111J scqu,l·nt1.1I
I ' lng, r , 1n 1nt s .
' ' - < .--

cru

.,,_ .l (.l p111111 s ) n,wll y J csr nhC' 3 m.1jor ty pes nl haz.,m .ls of., pq1cl11w,I
c:...ccut11rn. Bncrlv
lis t p11 ~,;il1k ,0l11t1 011s lor l',1ch 1y pr n l h.r1.,1rd. Note. rlcscnption i11 words ,s su/Jicrcnl no
.<1n1ph11·0 / 1//11stro tions nrc nhli,qntory.
.r· ,', '- ,, .,-,
'

I

"·1 (·I po111t s ) l1rlllll' w l1.1t ,1 rrn1lt1plc xor lugic l:ircui\ i_s (\\'1lh ,111 .1rh1trL1r;.· rrnrnh rr 111 inputs)
Pr n\'idc .11111th t.1h lc Im ,1 l- lu:J multiplc,Q_r. Pro vide ,J lng1c nn:1111 1inplt•111 cn1111~ ,1 ;! ln · ~ ,
l1111lt iplt~,11r, r h.,111 ,;l's /\N ll, NOT. ,111d OR lng,c g,ll l's D~'scnht• .1 Vl•nlng 11111J11ll' 1111pk111e111111~

suc h .1 lng1 i: c1n·1111 111 ., :t-ln - 1 111 11111plc,or

'-

I :, ( .I p11111l s - .10•1;11'\l r.1 crcd 11) VVhcn .1 p rngr.1m is ,1~l.1plt'd 111 ru 11 on 111ul11pk pr11cl'ssors 111
.1 11111ll1pr,11·essnr svstcrn. th l' e:...l'n1 t io11 1111w on 1•.1ch prth·t..•ssnr is rn mpns nl ol n 1111p11ltn~
111111• ,111d th e nv1•r l11•,1d t1nw rcq111n•d for lock,•d uilir.tl scc111111s .111d / 11r 111 s1'1HI d .1t.1 tm111
, 1111' prnn_•,; ~, 1r I 11 .111111 hl'r. /\ssu nw ., prngr,1111 rcqu 1res t = It)() s llt L'\t' nr t 10n t 11111· 011 1111c
p r,11·,•,,; pr_\V h1·11 r1111 I' prnn•,; q1r,, l'.1r h pn1u",sor rt•q111 rt'S t/ p s . .1s \\'I'll .,s .111 ,1dd1t1on ,1I •1 s
,, 111\ 1' 1h,•,rd , irr,•s 1w ct1\'I' ,111lw 1111 11llwr nl pr,11·,,_,,,H·s. Cnmptlll' thl' ('l'r- prol'l'ssor c:1.,xut1011
1i111I' l,H· 2 .11HI ·I prl1ccs:-1ir~. 1-'Pr l',H h r.1s c, lrs l 1h1• rorrl'Sptind ing s 111'cd11p rc l,1l l\'l' 111 .1 s ingk
Jl l'IH , .,., 111 , 111d th,• r.,t 111 lwl\\'1•,· 11 .1r111.d spet•dup ,·t•rs us itk.11 spl'cd 11p (spccd u11111lwr1' w ,1:;
1

1111 ,1,•1•rh1•,1d) /11111 '" )'Oilr ( 11/IIJ)ll/(l(IOl!S , ( ons,clcr thot I is,, .: :, 0.0 I HS (/ /Id t;'}_l) .,,, n.o:HS.

Thi.,; is th,• l' rHI ol lhe qut•stions or lhc P,.1111 .

1:11,.II i-:,.,m ol C:ompll ll'r i\n-hi1t•c111 rt•

P.1g<' I o l l

## 2019: Midterm

Files: [Fundamentals of CompArch Midterm 2019.pdf](https://glebpopov.notion.site/c150a7b524544a71bd3d41e6c63bed48)


Innopolis University
Academic Year 2019/2020
Midterm Exam of Computer Architecture
34 October 2019
Questions
Max 10 points + 3 points (30%) extra credit
Total time: 60 minutes

1. (1 point) Briefly describe the principles of Von Neumann architecture. Illustrate with a diagram.

2. (2 points) Translate the following MIPS code to C (or pseudocode). Assume that variables f, g, h,
and i are assigned to registers $s0, $s1, $s2, and $s3, respectively.

sub  $t0, $s1, $s2
addi  $t0, $t0, 3
add  $s0, $s3, $t0

3. (3 points) Describe the steps that transform a program written in a high-level language such as C
into a representation that is directly executed by a computer processor. Illustrate with a diagram;
provide a brief description for each step.

4. (4 points) Prove that the AND and NOT logic gates can be implemented by using only the NOR logic
gate.

5. (3 points - 30% extra credit) Consider three different processors P1, P2, and P3 executing the same
instruction set. P1 has a 3 GHz clock rate and a CPI of 1.5. P2 has a 2.5 GHz clock rate and a CPI of 1.0.
P3 has a 4.0 GHz clock rate and has a CPI of 2.2. Answer the following questions:

a) Which processor has the highest performance expressed in instructions per second?

b) If the processors each execute a program in 10 seconds, find the number of cycles and the
number of instructions.

c) We are trying to reduce the execution time by 30% but this leads to an increase of 20% in the
CPI. What clock rate should we have to get this time reduction?

Hint: To simply computations, consider that 1/2.2 = 0.45and 1/7 = 0.14

This is the end of the questions of the exam.

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)

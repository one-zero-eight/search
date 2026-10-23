---
type: course
title: "Compiler Construction"
description: "A course covering the overall compilation architecture, including lexical, syntax, and semantic analysis, code generation, optimization, and virtual machines."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Compilers_Construction"
tags: ["compilers", "programming-languages", "software-engineering", "code-generation", "optimization"]
aliases: ["BSc:CompilersConstruction"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Compilers_Construction"
    id: "7196"
    title: "BSc: Compilers Construction"
    last_modified: "2022-07-12T09:56:57Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:40:35+00:00"
status: draft
stale_after: "2024-07-11T09:56:57+00:00"
taught_by: ["/people/evgeniizouev.md", "/people/nikolaykudasov.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Compiler Construction

## Compiler Construction
- **Course name**: Compiler Construction
- **Code discipline**: n/a
- **Subject area**: Programming Languages and Software Engineering

### Short Description
This course covers the following concepts: Overall compilation architecture; Lexical analysis; Syntax analysis; Semantic analysis; Code generation; Program optimization; Virtual machines and JIT technology.

### Prerequisites

#### Prerequisite subjects


#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Introduction to compilers and compiler construction | # Basic notions: source and target languages, target architecture, compilation phases. <br> # The history of languages and compiler development. Typical compiler examples. <br> # Compilation & interpretation. Virtual machines, JIT & AOT technologies. Hybrid modes. |
| Lexical, syntax and semantic analyses | # Compilation pipeline & compilation data structures <br> # Lexical analysis and deterministic state automata <br> # Bottom-up and top-down parsing <br> # Principles of semantic analysis |
| Code generation, optimization and virtual machines | # Low-level code generation: machine instructions, assembly language <br> # Virtual machines’ architecture and their byte codes. <br> # The notion of language projections. <br> # Introduction to optimization techniques. |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The software development process and the depth of programming cannot be understood without a detailed analysis of the compilation process, from the lexical analysis to the syntactical and semantic analysis up to code generation and optimization, and without understanding both strength and limitation of this process. This course dig deeper into this topic building on the fundamental notions studied in theoretical computer science of which is the natural continuation. The typical compiler pipeline will be studied and a project will allow students to practice with the relevant tools.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Understanding in depth the compilation process
- Realizing the limits of the process and of Semantic Analysis
- Read and write grammars for programming language constructs
- Perform lexical analysis and use lexical analyzer generators
- Perform top-down parsing, bottom-up parsing and use parser generators
- Perform semantic analysis

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- How to design and develop compilers and language-related tools.
- The contents of each phase of the compilation process.
- How integrate compilers into an IDE.
- How to design a virtual machine for a language.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- To be able to develop a language compiler. 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 85-100 | - |
| B. Good | 75-84 | - |
| C. Satisfactory | 60-75 | - |
| D. Poor | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 40 |
| Interim performance assessment | 40 |
| Exams | 30 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Alfred V.Aho, Monica S.Lam, Ravi Sethi, Jeffrey D. Ullman. Compilers. Principles, Techniques, & Tools, Second Edition, Addison-Wesley, 2007, ISBN 0-321-48681-1.
- N. Wirth, Compiler Construction, Addison-Wesley, 1996, ISBN 0-201-40353-6
- http://www.ethoberon.ethz.ch/WirthPubl/CBEAll.pdf, 2005

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 |
| --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 1 | 1 |
| Homework and group projects | 1 | 1 | 1 |
| Oral polls | 1 | 0 | 0 |
| Discussions | 1 | 1 | 0 |
| Reports | 0 | 1 | 0 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is compilation process? | 1 |
| Question | What’s the difference between compiler and interpreter? | 1 |
| Question | How to compile a program? | 0 |
| Question | How to run a program? | 0 |
| Question | How to debug a program? | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Abstract syntax tree & symbol tables: what is it for and how create and manage them? | 1 |
| Question | How to organize communication between compilation phases? | 1 |
| Question | What are basic differences between bottom-up and top-down parsing? | 1 |
| Question | How to implement a hash function for a symbol table? | 0 |
| Question | How to write a grammar for an expression using YACC/Bison tool? | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What’s the difference between assembly and machine instructions? | 1 |
| Question | What’s the similarities and differences between real target platforms and virtual machines? | 1 |
| Question | Explain some of widely used approaches for optimizing program source code? How these approaches can be implemented in a compiler? | 1 |
| Question | Explain the idea behind the notion of control flow graph. | 0 |
| Question | What is “basic block” in CFG and what is it for? | 0 |
#### Final assessment
**Section 1**
1. What are significant phases of a compilation process?
1. Why do we need optimization phase?
1. What’s the difference between syntax and semantic analyses?
**Section 2**
1. Characterize the principles of top-down and bottom-up parsing.
1. Explain how a symbol table can be implemented.
1. AST: is it a tree or a graph? What’s about semantic attributes in an AST?
**Section 3**
1. Give some simple examples of language-code projections.
1. How the object code for an expression can be optimized?
1. How to avoid tail recursion while optimizing code?

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

<!-- catix:relations -->
## Relations

- Taught by: [Evgenii Zouev](/people/evgeniizouev.md), [Nikolay Kudasov](/people/nikolaykudasov.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Compilers Construction](https://eduwiki.innopolis.university/index.php/BSc%3A_Compilers_Construction), revision 7196

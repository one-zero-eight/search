---
type: course
title: "Advanced Compiler Construction and Program Analysis"
description: "A course covering type systems, lambda calculi, and the implementation of lazy functional languages including the STG machine."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3AAdvancedCompilerConstructionAndProgramAnalysis"
tags: ["compiler", "type-systems", "functional-programming", "lambda-calculus", "stg-machine"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3AAdvancedCompilerConstructionAndProgramAnalysis"
    id: "3637"
    title: "BSc:AdvancedCompilerConstructionAndProgramAnalysis"
    last_modified: "2022-03-15T08:53:53Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:27:20+00:00"
status: draft
stale_after: "2024-03-14T08:53:53+00:00"
---

# Advanced Compiler Construction and Program Analysis

## Advanced Compiler Construction and Program Analysis

- **Course name:** Advanced Compiler Construction and Program Analysis
- **Course number:** n/a
- **Subject area:** Programming Languages and Software Engineering

### Course characteristics

#### Key concepts of the class

- Type Systems
- Lambda calculi as the core representation
- Type checking and type inference
- Simple types and derived forms
- Subtyping
- Imperative objects
- Recursive types
- Universal polymorphism
- Compiling lazy functional languages

#### What is the purpose of this course?

This course covers two main topics: theory and implementation of type systems and implementation of lazy functional languages. We will study different type system features in detail, starting from an untyped language of lambda calculus and gradually adding new types and variations along the way. The course assumes familiarity with basics of compiler construction, basics of functional programming and familiarity with some static type systems (C++ and Java would suffice, but knowing type systems of Haskell or Scala will help).

Even though the most obvious benefit of static type systems is that it allows programmers to detect some errors early, it is by far not the only application. Types are used also as a tool for abstraction, documentation, language safety, efficiency and more. In this course we will look at features of type systems, common to many programming languages, like C++, Java, Scala and Haskell.

After we have reached System F, a type system at the core of languages like Haskell, we will look into how lazy functional languages are implemented. We will in particular look in detail at Spineless Tagless Graph reduction machine (also known as STG machine) that is used to compile Haskell code.

#### Course Objectives Based on Bloom’s Taxonomy

##### What should a student remember at the end of the course?

- Remember syntax and computation rules of untyped lambda calculus.
- Remember nameless representation of lambda terms.
- Remember definition of normal form, weak head normal form.
- Remember syntax, typing and computation rules of simply typed lambda calculus.
- Remember definition of imperative objects.
- Remember syntax and semantics of Featherweight Java.
- Remember typing rules for subtyping.
- Remember typing rules for pairs, tuples, records, sums, variants, and lists.
- Remember typing rules for let-bindings and type ascription.
- Remember typing rules for recursive types.
- Remember definition and typing rules for universal polymorphism.
- Remember syntax, typing and computation rules for System F.
- Remember representation of closures when compiling functional languages.
- Remember representation of lazy data structures when compiling.
- Remember the syntax and semantics of the STG language.

##### What should a student be able to understand at the end of the course?

- Understand how type systems relate to language design.
- Understand differences between call-by-name, call-by-need, and call-by-value evaluation strategies.
- Understand the tradeoffs introduced by various type system features.
- Understand the idea of nameless representation of terms.
- Understand the tradeoffs of mutable references and exceptions introduced in a language.
- Understand how imperative objects model objects in modern object-oriented langauges.
- Understand the difficulties of compiling lazy expressions.
- Understand the differences between Hindley–Milner type system and System F.

##### What should a student be able to apply at the end of the course?

- Implement an interpreter for a programming language with untyped lambda calculus as its core representation.
- Implement an interpreter for a programming language with simply typed lambda calculus as its core representation.
- Implement type checking algorithm for a language with simple types, recursive types, imperative objects, and universal polymorphism.
- Implement Damas–Hindley–Milner type inference algorithm for a programming language with a Hindley-Milner style type system.

#### Course evaluation

**Course grade breakdown**

|  | **Proposed points** |
| --- | --- |
| Labs/seminar classes | 20 |
| Interim performance assessment | 30 |
| Exams | 50 |

##### Labs/seminar classes

In-class participation 1 point for each individual contribution in a class but not more than 1 point per class (i.e. 14 points in total for 14 classes),
overall course contribution (to accumulate extra-class activities valuable to the course progress,
e.g. a short presentation, book review, very active in-class participation, etc.) up to 6 points.

##### Interim performance assessment

In-class tests up to 10 points for each test, computational practicum assignment up to 10 points for each task.

##### Exams

Mid-term exam up to 20 points, final examination up to 30 points.

**Overall score:** 100 points (100%).

##### Grades range

**Course grading range**

|  |  | **Proposed range** |
| --- | --- | --- |
| A. Excellent | 85-100 | 85-100 |
| B. Good | 75-84 | 75-84 |
| C. Satisfactory | 60-75 | 60-75 |
| D. Poor | 0-59 | 0-59 |

#### Resources and reference material

- Benjamin C. Pierce. *Types and Programming Languages. The MIT Press 2002*
- Simon Peyton Jones. *Implementing functional languages: a tutorial. Prentice Hall 1992*
- Simon Peyton Jones. *Implementing Lazy Functional Languages on Stock Hardware: The Spineless Tagless G-machine. Journal of Functional Programming 1992*

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

**Course Sections**

| **Section** | **Section Title** | **Lecture Hours** | **Seminars (labs)** | **Self-study** | **Knowledge evaluation** |
| --- | --- | --- | --- | --- | --- |
| 1 | Lambda calculus and simple types | 10 | 10 | 10 | 2 |
| 2 | References, exceptions, imperative objects, Featherweight Java | 6 | 6 | 6 | 1 |
| 3 | Recursive types, type reconstruction, universal polymorphism | 10 | 10 | 10 | 2 |
| 4 | Compiling lazy functional languages | 4 | 4 | 4 | 1 |
| 5 | Project presentation |  |  |  | 2 |

#### Section 1

##### Section title:

Lambda calculus and simple types

##### Topics covered in this section:

- The history of typed languages. Type systems and language design.
- Basic notions: untyped lambda calculus, nameless representation, simple types.

##### What forms of evaluation were used to test students’ performance in this section?

Development of individual parts of software product code & 1

Homework and group projects & 1

Midterm evaluation & 0

Testing (written or computer based) & 0

Reports & 0

Essays & 0

Oral polls & 1

Discussions & 1

**Forms of evaluation**

| **Form of evaluation** | **Usage** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 0 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 1 |
| Discussions | 1 |

##### Typical questions for ongoing performance evaluation within this section

1. What is the role of the type system in language design?
1. How to evaluate lambda terms using call-by-name/call-by-value strategies?
1. What is the typing relation?
1. What is type safety?
1. What is erasure of types?
1. What is general recursion?

##### Typical questions for seminar classes (labs) within this section

1. Evaluate a given lambda expression using call-by-name strategy.
1. Convert a given lambda expression to/from a nameless representation.
1. Draw a type derivation tree for a given lambda term in simply typed lambda calculus.
1. Provide a type for a given lambda term in a given simple type system.

##### Test questions for final assessment in this section

1. Present an implementation of an interpreter for untyped lambda calculus.
1. Present an implementation of a type checker for simply typed lambda calculus.

#### Section 2

##### Section title:

References, exceptions, imperative objects, Featherweight Java

##### Topics covered in this section:

- References, store typings, raising and handling exceptions
- Subsumption and the subtyping relation, coercion semantics, the Bottom Type
- Object-oriented programming and lambda calculus with imperative objects
- Featherweight Java

##### What forms of evaluation were used to test students’ performance in this section?

Development of individual parts of software product code & 1

Homework and group projects & 1

Midterm evaluation & 0

Testing (written or computer based) & 0

Reports & 0

Essays & 0

Oral polls & 1

Discussions & 1

**Forms of evaluation**

| **Form of evaluation** | **Usage** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 1 |
| Testing (written or computer based) | 0 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 1 |
| Discussions | 1 |

##### Typical questions for ongoing performance evaluation within this section

To be done

##### Typical questions for seminar classes (labs) within this section

To be done

##### Test questions for final assessment in this section

To be done

#### Section 3

##### Section title:

Recursive types, type reconstruction, universal polymorphism

##### Topics covered in this section:

- Recursive types, induction and coinduction, finite and infinite types
- Polymorphism, type reconstruction, universal types
- System F and Hindley-Milner type system

##### What forms of evaluation were used to test students’ performance in this section?

Development of individual parts of software product code & 1

Homework and group projects & 1

Midterm evaluation & 0

Testing (written or computer based) & 0

Reports & 0

Essays & 0

Oral polls & 1

Discussions & 1

**Forms of evaluation**

| **Form of evaluation** | **Usage** |
| --- | --- |
| Development of individual parts of software product code | 1 |
| Homework and group projects | 1 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 0 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 1 |
| Discussions | 1 |

##### Typical questions for ongoing performance evaluation within this section

To be done

##### Typical questions for seminar classes (labs) within this section

To be done

##### Test questions for final assessment in this section

To be done

#### Section 4

##### Section title:

Compiling lazy functional languages

##### Topics covered in this section:

- Challanges of compiling lazy functional languages
- Representing functional closures at run-time
- Representing lazy data structures at run-time
- The syntax and semantics of the STG language

##### What forms of evaluation were used to test students’ performance in this section?

Development of individual parts of software product code & 1

Homework and group projects & 1

Midterm evaluation & 0

Testing (written or computer based) & 0

Reports & 0

Essays & 0

Oral polls & 1

Discussions & 1


**Forms of evaluation**

| **Form of evaluation** | **Usage** |
| --- | --- |
| Development of individual parts of software product code | 0 |
| Homework and group projects | 0 |
| Midterm evaluation | 0 |
| Testing (written or computer based) | 1 |
| Reports | 1 |
| Essays | 0 |
| Oral polls | 1 |
| Discussions | 1 |


##### Typical questions for ongoing performance evaluation within this section

To be done

##### Typical questions for seminar classes (labs) within this section

To be done

##### Test questions for final assessment in this section

To be done

# Citations

1. [BSc:AdvancedCompilerConstructionAndProgramAnalysis](https://eduwiki.innopolis.university/index.php/BSc%3AAdvancedCompilerConstructionAndProgramAnalysis), revision 3637

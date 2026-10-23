---
type: course
title: "High Performance Computing"
description: "A course on parallel computing architectures and algorithms, covering OpenMP, CUDA, and parallel solutions for linear algebra, differential equations, and signal processing."
resource: "https://eduwiki.innopolis.university/index.php/BSTE%3AHighPerformanceComputing"
tags: ["hpc", "parallel-computing", "cuda", "opencl", "linear-algebra", "numerical-methods"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSTE%3AHighPerformanceComputing"
    id: "982"
    title: "BSTE:HighPerformanceComputing"
    last_modified: "2021-10-18T07:15:54Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:14:04+00:00"
status: draft
stale_after: "2023-10-18T07:15:54+00:00"
duplicate_of: ["/courses/bsc-highperformancecomputing.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# High Performance Computing

## High Performance Computing

### Course Characteristics

#### Key concepts of the class

- MIMD and SIMD architectures
- OpenMP, OpenCL, CUDA
- Algorithms of computationam mathematics
- Parallelism

#### What is the purpose of this course?

The course outlines some well-known numerical algorithms and discusses a range of problems related to their parallelization. 
Direct methods for solving systems of linear algebraic equations with matrices of both general and special types (Gauss exclusion method, Cholesky decomposition, run-through method), iterative methods for solving systems of linear equations (methods of simple iteration and upper relaxation, conjugate gradient method), sparse algebra problems, methods for parallel solution of systems of ordinary differential equations and partial differential equations, digital signal processing, Monte Carlo methods are considered.

#### Prerequisites

- Introduction to Programming (C++ programming language),
- Computer Architecture,
- Calculus,
- Linear Algebra,
- Differential Equations
- Digital signal processing

#### Resources and reference material

- Sanders, J., Kandrot, E. (2010) CUDA by example : an introduction to general-purpose GPU programming, Addison-Weslye
- Scarpino, M. (2011) OpenCL in Action: How to Accelerate Graphics and Computations, Manning.
- Banger, R., Bhattacharyya, K. (2013) OpenCL Programming by Example, Packt Publishing.

### Course Sections

The main sections of the course and approximate hour distribution between them is as follows:

- Introduction to OpenMP, OpenCL and CUDA
- Basic parallel algorithms of Linear Algebra
- Parallel methods of solving the systems of ordinary differential equations
- Parallel methods of solving partial differential equations
- Parallelism in Digital Signal Processing
- Parallel Monte-Carlo methods

##### Section title:

Introduction to OpenMP and OpenCL

#### Topics covered in this section:

- Existing multicore systems
- MIMD and SIMD programming models
- Massively parallel accelerators
- Memory hierarchy

##### Section title:

Basic parallel algorithms of Linear Algebra

#### Topics covered in this section:

- Matrix multiplication (demonstration of optimization based on different types of device's memory)
- Direct methods of solving SLAE 
    - Gaussian elimination
    - Cholessky decomposition
    - Sweep methods
- Iterative methods of solving SLAE
    - Solution of sparse SLAE by iterative methods in the problem of heat propagation in a plate
    - Solution of symmetric sparse SLAE by upper relaxation method with Chebyshev acceleration
    - Solution of symmetric sparse SLAE by conjugate gradients with preconditioning
    - Solution of sparse SLAE by generalized minimal residuals with preconditioning

##### Section title:

Parallel methods of solving the systems of ODE

#### Topics covered in this section:

- Integration of a stochastic differential equation in the problem of calculating the fair price of an option of the European type
- Integration of a system of differential equations in the problem of modeling processes in a neural network

##### Section title:

Parallel methods of solving partial differential equations

#### Topics covered in this section:

- Solution of the wave equation
- Solution of the problem of thermal conductivity
- Solution of the Dirichlet problem for the Poisson equation
- Solution using Fast Fourier Transform
- Solving partial differential equations on the example of the problem of calculating the fair price of a composite option
- Using the fast Fourier transform to solve the problem of heat propagation in the plate

##### Section title:

Parallelism in Digital Signal Processing

#### Topics covered in this section:

- Simple color transformation
- Filtration, convolution
- Boundaries detection
- Images scaling

##### Section title:

Parallel Monte-Carlo methods

#### Topics covered in this section:

- Calculation of definite integrals
- Ways to reduce the variance
- Pseudorandom number generators
- Approaches to parallelization of Monte Carlo methods
- Parallel Monte Carlo methods in the problem of calculating the fair price of an option of the European type

<!-- catix:relations -->
## Relations

- Duplicate of (the page edited last): [BSc: HighPerformanceComputing](/courses/bsc-highperformancecomputing.md)
<!-- /catix:relations -->

# Citations

1. [BSTE:HighPerformanceComputing](https://eduwiki.innopolis.university/index.php/BSTE%3AHighPerformanceComputing), revision 982

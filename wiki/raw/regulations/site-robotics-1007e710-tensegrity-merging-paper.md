---
type: regulation
title: "Тема — «Объединение топологий тенсегрити структур: метод с использованием целочисленной выпуклой оптимизации». — Tensegrity merging paper"
resource: "https://robotics.innopolis.university/wp-content/uploads/2022/03/Tensegrity_merging_paper.pdf"
source_kind: official-document
language: ru
section: "site/robotics"
sources:
  - resource: "https://robotics.innopolis.university/wp-content/uploads/2022/03/Tensegrity_merging_paper.pdf"
    id: "97a28fd4b96b"
    title: "Тема — «Объединение топологий тенсегрити структур: метод с использованием целочисленной выпуклой оптимизации». — Tensegrity merging paper"
    last_modified: "2026-10-31T09:36:36+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-10-31T09:36:36+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Тема — «Объединение топологий тенсегрити структур: метод с использованием целочисленной выпуклой оптимизации». — Tensegrity merging paper

Tensegrity Topology Merging: Mixed-Integer Convex optimization-based Method

Ramil Khafizov

Center for Technologies in Robotics and Mechatronics Components Innopolis University Innopolis, 420500 Email: r.khafizov@innopolis.university

Sergei Savin

Center for Technologies in Robotics and Mechatronics Components Innopolis University Innopolis, 420500 Email: s.savin@innopolis.ru

In practice it might be desirable to use smaller hand-designed tensegrity structures as building blocks in creating larger ones. However, existing methods do not provide an automated robust method for merging pre-generated structures: combining separate structures into a more complex single tensegrity with possible addition of new structural elements supporting the merge. Introduction of such algorithms would not only let us construct more complex structures, but also give an opportunity to add human expertise into generation procedure, by combining human designed and computer designed structures together.

Abstract—This paper proposed a mixed-integer convex optimization-based method for merging multiple tensegrity structures. Merging is extremely useful in constructing complex structures, which consist of lots of cables and struts, whereas building such structures from scratch might be infeasible. In addition to that, merging procedure let’s us use human-designed structures as elementary units of resulting object. The proposed method permits utilization of lots of constraints, used during tensegrity generation procedure. At the same time we also try to merge structures with as little additional connections as possible. In comparison to existing approaches, this method is a single-step algorithm and does not make any assumption on shape and relative position of merged structures.

In this paper we propose a new optimization-based automated method for merging arbitrary number of tensegrity structures together. The whole algorithm is formulated as a one-step mixed-integer convex program.

I. INTRODUCTION

The term tensegrity refers to a prestressed structure, consisting of a discontinuous set of compressive components (struts) connected via a connected set of tensile components (cables)

This paper is organized in following way. In section II we give a definition of tensegrity structure’s dynamical model. In section III we first describe general convex-optimization based approach for generation, then we introduce our method for merging tensegrity structures. Section IV is dedicated to a numerical experiments, where we show the ability of our method to merge structures and provide relevant analysis.

[1]. Most of classical tensegrity structures are prestress-stable

[2], [3]. The stability is defined by the positive definiteness of the tangent stiffness matrix; prestress stability indicates that the structure is stable in the current configuration, given correct prestress (action of internal elastic forces) [4].

Let us consider the problem of generating tensegrity structure in a stable configuration, when the topology, structural parameters and configuration can be modified, subject to constraints. It can be referred to as tensegrity generation problem. A substantial amount of work has been done in this area. Major directions include tensegrity generation based on machine learning and evolutionary algorithms (such as Viability Evolution and Neuro-Evolution of Augmenting Topologies in [5]) and nonlinear optimization. The later includes mixed-integer convex optimization (MICP)-based methods, which have presented a number of promising results [6], which we will discuss in detail later. Here we want to point out that the resulting optimization problems are tractable, but large and resulting structures are not always optimal: they require fine tuning, and importantly the problems do not take into account local stiffness properties of the robot.

A. State of the art

The problem of design of tensegrity structures has been extensively studied previously. Originally, such structure were designed by human experts in architecture and civil engineering. We should note that the generation problem includes at least two different sets of problems (divided so based on the difference in approaches to solving them, rather than on any inherent distinction): 1) topology design, where the goal is to find the number of nodes as well as number, placement and type of elastic elements connecting nodes; 2) stable configuration and pre-stress design, where the position of the nodes and pre-stress of elastic elements (or more often, a subset of them) are acting as decision variables, and the goal is to find a statically stable configuration of the tensegrity structure. A multitude of automated approaches for solving these and related problems has been proposed: genetic algorithms [7]–[9], machine learning [10], stochastic methods

978-1-6654-2407-3/21/$31.00 ©2021 IEEE [11], non-linear optimization and iterative convex optimization

[12]; for some special cases, algebraic conditions and even analytical solutions have been found [13], [14].

One of the first methods for topology design, based on convex optimization was proposed in [6]. There, a mixed-integer programming-based two step approach was proposed, taking into account equilibrium condition and a discontinuity constraints. Later the method was improved by turning it into a single step procedure [15]. Implicit symmetry control during design process was also investigated [15]. Further, generalizations of these methods were studied for generating arbitrary class structures (where class of tensegrity structure is the maximum amount of struts connected to any joint) [16] and for additions of rigid bodies [17].

In our work we are focusing on formulating the mixed integer programming-based approach for merging arbitrary tensegrity structures into a single one. The only research we are aware of, where work in this direction has been reported is [6], where only structures with same position relationship one-by-one are connected in a two-step process . Our method for merging tensegrity structures is distinct in: 1) the whole procedure is done in a single step 2) being easily extendable to an arbitrary number of tensegrity structures, which can have any arbitrary shape and be freely located and merged via auxiliary elements (both struts and elastic elements) 3) allowing all constraints required in generation task, including explicit assignment of the desired class of the structure. In the following sections we present general mathematical description of the tensegrity models and outline our method. At the end of the paper we provide numerical experiments demonstrating work of the method.

II. MODEL OF A TENSEGRITY STRUCTURE IN STATIC EQUILIBRIUM

Tensegrity structure may be approximately modelled as a set of point masses ri representing coordinates of the nodes (connection points of struts and cables). We can write force balance equations for the structure which should to hold for each node in order for the structure to be stable: n fi,j(r) = 0, ∀i,j ∈ {1,2,...,n} (1) j=1 where fi,j - elastic force acting between nodes i and j, n - total number of nodes in the structure. Elastic forces fi,j can be modelled as follows: ri − rj ||ri − rj||

. (2) fi,j = µi,j(||ri − rj|| − ρi,j) where ri, rj are positions of the nodes, µi,j is the linear stiffness coefficient of the elastic element connecting the nodes, and ρi,j is its rest length.

A. General tensegrity generation framework

Generation procedure consists of combining several convex and mixed-integer constraints and an objective function.

First, we should rewrite static equilibrium constraints (1),

(2). For that we introduce force-density variables and directional matrices to handle static equilibrium constraints.

Let Pi = pi1, pi2, ... pin be the matrix, indicating directions from the i-th node in the tensegrity structure to all other points:

Pi = (r1 − ri) (r2 − ri) ... (rn − ri) (3) Then, the static equilibrium for the i-th node can be described as:

Pifi = 0 (4) where fi ∈ Rn can be seen as forces parametrized with scalar values along pre-defined directions, or as Lagrange multipliers, or as a free variables. In the presence of external forces gi, the condition becomes:

Pifi = gi (5)

Other constraints are written by means of two symmetric connectivity matrices R,C ∈ Rn×n, where R describes strut connections, and C describes cable connections. If two nodes i,j are connected with a strut, then Rij = 1, otherwise Rij =

**0.** Same goes for cable connections in the matrix C.

We should add constraints on class of tensegrity (6), unidirectionality of cable and strut forces (7) and on symmetry of matrices R,C (8): n

Rij = 1, ∀i ∈ {1,2,...,n} (6) j=1 where Rij is the i,j-th element of the matrix R. fij ≤ MCij, ∀i,j ∈ {1,2,...,n} −fij ≤ MRij, ∀i,j ∈ {1,2,...,n}

(7) where M ∈ R is the maximum admissible force component-wise magnitude.

C = C , R = R Cii = Rii = 0, ∀i ∈ {1,2,...n}

(8)

There are also many other possible constraints, such as constraint on strut and cable length limits, which can be either limit absolute length of the strut or cable, or its projection on some axis; these and others gives more control over resulting structure and its properties. We leave them out here for simplicity, as our main focus is on merging different structures.

B. Merging tensegrity structures as a mixed-integer program

Assume that each tensegrity is defined by connectivity matrices Ri, Ci, and the merged structure will be defined by its connectivity matrices R, C. In case we want to add new cable or strut connections it is necessary to edit connectivity matrices.

Consider the case when two tensegrity structures need to be merged; we will refer to them as parent structures. First let

Fig. 1: Tensegrity structures, generated using points sampled from spherical and cylindrical grids, before merging

Fig. 2: Tensegrity structures, generated using points sampled from spherical and cylindrical grids, after merging us consider procedure where we do not add any new nodes, but only add new connections. Thus, set of nodes of resulting tensegrity is a union of sets of nodes of merged structures.

For concreteness we can define dimensions of the connectivity matrices C1 ∈ Rn×n,C2 ∈ Rm×m and strut R1 ∈ Rn×n,R2 ∈ Rm×m. We combine them diagonally into new cable C¯ ∈ Rm+n×m+n and strut R¯ ∈ Rm+n×m+n matrices,

C1 0

C¯ =

0 C2 R ¯ =

R1 0 0 R2

(9)

Note that the node arrays of the parent structures are to be merged as well; hence, number of constraints (4) and (5) should increase accordingly.

Thus constructed matrices C¯ and R¯ contain only information about internal connections on the parent structures. In order to get inter-parent connections we introduce new binary decision variables: δR ∈ R(m+n)×(m+n) for strut connections and δC ∈ R(m+n)×(m+n) for cable connections. Connectivity matrices of resulting merged structure will be following:

(a) before merging (b) after merging

Fig. 3: Tensegrity structures, generated using points sampled from prismatic grids, before and after merging

C = C¯ + δC R = R¯ + δR

(10)

As an objective function we are minimizing number of additional connections. That is a very natural objective, because if we would like to merge separate structures, we would prefer to do it with minimal modifications. m+n m+n m+n m+n δR (11)

Jc = δC + i=1 j=0 i=1 j=0

If we wish to add k new nodes, we only need to modify connectivity matrix and add more rows:

 

  ∈ R(m+n+k)×(m+n+k)

C1 0 0 0 C2 0 0 0 0

C¯ =

(12)

 

  ∈ R(m+n+k)×(m+n+k)

R1 0 0 0 R2 0 0 0 0

R¯ =

One of the positive sides of the proposed method is that we can keep all same constraints as we use in general tensegrity generation framework.

III. NUMERICAL EXPERIMENTS

Our approach lets us do experiments not only with automatically generated structures, but also with structures, designed by human experts.

In automatic generation we first generate set of nodes ri for each structure, which is a subset of some regular grid (cylinder,

(a) before merging

(b) after merging

Fig. 4: Tensegrity structures, generated using points sampled from prismatic, spherical, cylindrical grids, before and after merging cube or sphere). In our experiments each set consists of ten points. Then we separately apply general optimization-based generation procedure on each set of nodes and obtain separate structures. After we shift them some of them in arbitrary direction in order to get more visually clear results and apply merging.

For mounted tensegrity structures, such as tensegrity robot arms, tensegrity bridges and towers, it is important to allow the structure to have fixed nodes. Fixed nodes can be seen as nodes with constraints put on them, with reaction forces imposing those constraints. We keep the number of fixed nodes to three after merging: such condition will automatically enforce some new connections to keep equilibrium condition satisfied. In automatic tensegrity generation we use three fixed nodes.

A. Example 1: sphere and cylinder

In this experiment we took structures, generated from spherical and cylindrical grids shifted by some distance in x-axis direction. Merging procedure produced 4 additional connections: 2 cable and 2 strut.

B. Example 2: two prisms In this experiment we were investigating the possibility of merging two prisms into a tensegrity tower. Our method succeeded with this task and 4 additional cables were enough for merging.

C. Example 3: prism, sphere and cylinder Our method is scalable and might be applied to merge any reasonable amount of structures. In this experiment we merge three, made of prism, sphere and cylinder grids. Only 3 additional strut connections and 2 cables were needed.

D. Conclusions

In this research we proposed a new method for merging tensegrity structures, using mixed-integer convex programming, which allows usage of all constraints, used in automatic tensegrity generation. Method was tested in several numerical experiments, where we were able to merge different structures into a single one. In numerical experiments we also show that method might be applied for simultaneous merging of a larger number of tensegrity structure, without significant modifications of their internal connections. The benefit of proposed algorithm is that it can also be applied for merging structures, designed by human expert.

REFERENCES

[1] R. Motro and V. Raducanu, “Tensegrity systems,” International Journal of Space Structures, vol. 18, no. 2, pp. 77–84, 2003.

[2] W. W. R. Connelly, “Second-order rigidity and prestress stability for tensegrity frameworks,” in SIAM J Discrete Math, 6. IEEE, 1996, pp. 453–491.

[3] R. Connelly, “Tensegrity structures: why are they stable?” in Rigidity theory and applications. Springer, 2002, pp. 47–54.

[4] M. Ohsaki and J. Zhang, “Stability conditions of prestressed pinjointed structures,” International Journal of Non-Linear Mechanics, vol. 41, no. 10, pp. 1109–1117, 2006. [Online]. Available: https://www.sciencedirect.com/science/article/pii/S0020746206000904

[5] E. Zardini, D. Zappetti, D. Zambrano, G. Iacca, and D. Floreano, “Seeking quality diversity in evolutionary co-design of morphology and control of soft tensegrity modular robots,” arXiv preprint arXiv:2104.12175, 2021.

[6] S. Ehara and Y. Kanno, “Topology design of tensegrity structures via mixed integer programming,” International Journal of Solids and Structures, vol. 47, no. 5, pp. 571–579, 2010. [Online]. Available: https://www.sciencedirect.com/science/article/pii/S0020768309004132

[7] C. Paul, H. Lipson, and F. J. V. Cuevas, “Evolutionary form-finding of tensegrity structures,” in Proceedings of the 7th Annual Conference on Genetic and Evolutionary Computation, ser. GECCO ’05. New York, NY, USA: Association for Computing Machinery, 2005, p. 3–10. [Online]. Available: https://doi.org/10.1145/1068009.1068011

[8] K. Koohestani, “Form-finding of tensegrity structures via genetic algorithm,” International Journal of Solids and Structures, vol. 49, no. 5, pp. 739–747, 2012. [Online]. Available: https://www.sciencedirect.com/science/article/pii/S0020768311003970

[9] S. Lee and J. Lee, “A novel method for topology design of tensegrity structures,” Composite Structures, vol. 152, pp. 11–19, 2016. [Online]. Available: https://www.sciencedirect.com/science/article/pii/S0263822316304640

[10] E. Zalyaev, S. Savin, and L. Vorochaeva, “Machine learning approach for tensegrity form finding: Feature extraction problem,” in 2020 4th Scientific School on Dynamics of Complex Networks and their Application in Intellectual Robotics (DCNAIR), 2020, pp. 265–268.

[11] Y. Li, X.-Q. Feng, Y.-P. Cao, and H. Gao, “A monte carlo form-finding method for large scale regular and irregular tensegrity structures,” International Journal of Solids and Structures, vol. 47, no. 14-15, pp. 1888–1898, 2010.

[12] S. Savin, O. Balakhnov, and A. Maloletov, “Linearization-based forward kinematic algorithm for tensegrity structures with compressible struts,” in Proceedings of 15th International Conference on Electromechanics and Robotics” Zavalishin’s Readings”. Springer, 2021, pp. 293–303.

[13] A. Tibert and S. Pellegrino, “Review of form-finding methods for tensegrity structures,” International Journal of Space Structures, vol. 18, no. 4, pp. 209–223, 2003.

[14] K. Koohestani and S. Guest, “A new approach to the analytical and numerical form-finding of tensegrity structures,” International Journal of Solids and Structures, vol. 50, no. 19, pp. 2995–3007, 2013.

[15] Y. Kanno, “Exploring new tensegrity structures via mixed integer programming,” Structural and Multidisciplinary Optimization, vol. 48, pp. 95–114, 2013.

[16] X. Xian, Y. Wang, and Y. Luo, “General approach for topology-finding of tensegrity structures,” Journal of Structural Engineering, vol. 142, p. 04016061, 04 2016.

[17] Y. Wang, X. Xu, and Y. Luo, “Topology design of general tensegrity with rigid bodies,” International Journal of Solids and Structures, vol. 202, pp. 278–298, 2020. [Online]. Available: https://www.sciencedirect.com/science/article/pii/S0020768320302031

# Citations

1. [Тема — «Объединение топологий тенсегрити структур: метод с использованием целочисленной выпуклой оптимизации». — Tensegrity merging paper](https://robotics.innopolis.university/wp-content/uploads/2022/03/Tensegrity_merging_paper.pdf), file 97a28fd4b96b

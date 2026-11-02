---
type: regulation
title: "Read the article [NIR_2022_stiffness-analysis]"
resource: "https://innopolis.university/filespublic/NIR_2022_stiffness-analysis.pdf"
source_kind: official-document
language: ru
section: "site/university"
sources:
  - resource: "https://innopolis.university/filespublic/NIR_2022_stiffness-analysis.pdf"
    id: "b4cee548cca7"
    title: "Read the article [NIR_2022_stiffness-analysis]"
    last_modified: "2026-10-24T23:45:43+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-10-24T23:45:43+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Read the article [NIR_2022_stiffness-analysis]

Stiffness Analysis of the Double Pantograph Transmission System

Walid Shaker

Innopolis University Innopolis, Russia w.shaker@innopolis.university

Alexandr Klimchik

Innopolis University Innopolis, Russia a.klimchik@innopolis.ru

Abstract—This article is devoted to implement the stiffness modeling of 1-DOF double pantograph robot, which consists of two legs connected to each other with two revolute joints. The stiffness modelling is implemented using two techniques: Virtual joint modeling (VJM) and Matrix structural analysis (MSA). In order to find end-effector deflection, an applied load is exerted along different directions at multiple points in the robot workspace, which is presented in scatter plots. The computational cost and difference between results were studied and compared for both methodologies.

Index Terms—Stiffness modeling, Parallel robot, Double pantograph, Virtual joint modeling, Matrix structural analysis

Github repository: https://github.com/Walid-khaled/Double-Pantograph-Stiffness-Modelling

I. INTRODUCTION

Parallel manipulators have been widely used in modern applications as a machine tool. As a result, considerable attention has been paid to the tool accuracy for more precise industrial operations. In addition to that, parallel structures have some advantages over serial manipulators such as higher payload, and higher rigidity. Since the external load is distributed among several legs, these structures have higher stiffness and higher accuracy as the error is not accumulated at the end-effector (EE) as in the case of serial robots [1].

Double pantograph, which is frequently referred as scissor lifting mechanism, is 1-DOF transitional mechanism consists of two serial kinematic legs move simultaneously and attached to EE platform as shown in Fig.1. It has one horizontal prismatic joint and it can be actuated using electric motor or hydraulic system. The main application of scissor lifts is the vertical load transmission with or without human intervention. They are commonly used in parts assembly and disassembly, construction maintenance, and other industrial tasks such as landing access [2].

To address the accuracy problem, stiffness analysis can be considered as a best practise because it allows us to calculate the deflections at the EE under an applied external load. Hence to improve the overall accuracy by calculating the difference between the desired pose and the actual pose of the robot [3]. In literature, three main approaches for stiffness modelling are determined. FEA (Finite Element Analysis) [4] [5] is the most accurate approach and suitable for non-linear analysis; however, it is computationally expensive as it decomposes structure’s links into large number of finite small elements. Matrix Structural Analysis (MSA) [6] [7] [8] applies the same idea of FEA, but it handles the computational cost as structure’s elements are significantly simplified. Nevertheless, it is only suitable for parallel robots. Finally, the Virtual Joint Modeling (VJM) [9] [10] [11] which is the simplest technique as it assumes that all links are rigid expanded with virtual joints which represents the elasticity of links and joints. In this work, MSA and VJM are implemented and a comparison between the two methods is held.

Fig. 1. Scissor Lifting Mechanism II. KINEMATICS

In order to implement the stiffness modelling of the double pantograph robot, forward and inverse kinematics have to be derived for each kinematic chain. The kinematics scheme is illustrated in Fig.2.

A. Forward Kinematics

As shown, the local coordinate frames of both serial chains coincide, and they are located in the middle of the horizontal prismatic joint, x-axis. Since we only have one prismatic joint, it will drive both legs with half of its stroke. For example, when the active prismatic joint is advanced with dx, each chain will be advanced with a horizontal distance dx/2. It is also noticeable that each leg contains three revolute joints and their axis of rotation, y-axis, is perpendicular to the prismatic joint axis. These 2 legs also coincide at the upper local coordinate frame which is the EE frame. As the lower and upper local frames are shifted only in the direction of z-axis, it means that if one leg is translated in +x-axis first, it will translate in −x-axis later and vice versa. Since the robot structure consists of 2 similar chains, the forward kinematics of each chain i can be written as a product of the following homogeneous transformations:

T = TbaseTx (di,1)Ry (qpassive i,1)Tx(l)Ry (qpassive i,2) Tx(l)Ry (qpassive i,3)Tx (di,2)Ttool

(1)

Fig. 2. Kinematic Schematic where l is the link length. For the ith leg, di,j is half of displacement of the jth prismatic joint, and qpassive i,j is revolute joint variable for the jth passive joint. Transformation between the global coordinate frame and to the local coordinate frame is described by Tbase matrix, while transformation between legs’ end is given by Ttool matrix. Table 1 presents the translational and rotational parameters for each single leg.

TABLE 1 KINEMATICS PARAMETERS

| Parameter | i = 1 | i = 2 |
| --- | --- | --- |
| di,1 | dx/2 | −dx/2 |
| di,2 | −dx/2 | dx/2 |
| qpassive i,1 | −q3 | −q1 |
| qpassive i,2 | q2 | −q2 |
| qpassive i,3 | q1 | q3 |

where q1 = atan2 l2 − dx2,dx (2) q3 = 180◦ − q1 (3) q2 = q3 − q1 (4)

Thus, given dx from prismatic joint, the height of the pantograph dz can be calculated as T(3,4).

B. Inverse Kinematics

The inverse kinematics aims to calculate the active and passive joints of the robot at each height dz. It is simple and straight forward as it can be written as:

- • Active prismatic joint: dx = l2 − dz42

- • Passive revolute joints q1,q2,q3 can be obtained from

equations 2, 3, 4.

C. Structure Limits

This type of structures should implies some constraints on motion to avoid structure failure. Hence, structure limits should be analyzed as follows: Since l2 − dz

4 ≥ 0 thus dz ≤ 2l Similarly, z = 2√l2 − dx2 so l2 − dx2 ≥ 0 thus dx ≤ l Assuming that l = 0.5 m, dx ≤ 0.5,dz ≤ 1

- • when the structure is totally expanded dz = 1,dx = 0

q1 = q3 = 90◦, and q2 = 0

- • when it is totally compressed dx = 0.5,dz = 0 q1 = 0,

and q2 = q3 = 180◦

In both cases, the structure will break because it is not allowed to derive the robot at these limits. Thus, 0.1 m and 0.9 m are assigned as minimum and maximum height the robot can reach safely as shown in Fig.3.

Fig. 3. Pantograph Model

III. STIFFNESS OF THE LINKS

We considered links as cylindrical beams made of aluminium. Generally, 3D beam elements could have stiffness matrix K in the following form:

K11 K12 K21 K22

(5) where

K =

- • K11 : represents force/torque reaction due to left-end

deflection at the left-end point of the beam.

- • K12 : represents force/torque reaction due to right-end

deflection at the left-end point of the beam.

- • K21 : represents force/torque reaction due to left-end

deflection at the right-end point of the beam.

- • K22 : represents force/torque reaction due to right-end

deflection at the right-end point of the beam. For regular beam:

K11 =    EA L 0 0 0 0 0 0 12EI z L3 0 0 0 6EI z L2 0 0 12LEI3 y 0 −6EIL2y 0 0 0 0 GILρ 0 0 0 0 −6EIL2y 0 4EIL y 0 0 6EI z L2 0 0 0 4EI z L   

K12 =



−EAL 0 0 0 0 0 0 −12EI

L3 0 0 0 −6EI z L2 z

0 0 −12LEI3 y 0 6EIL2y 0 0 0 0 −GILρ 0 0 0 0 −6EIL2y 0 2EIL y 0 0 6EI

 

L2 0 0 0 2EI z z

L

K21 = K12T





EA L 0 0 0 0 0 0 12EI

L3 0 0 0 −6EI z L2 z

0 0 12LEI3 y 0 6EIL2y 0 0 0 0 GILρ 0 0 0 0 6EIL2y 0 4EIL y 0 0 −6EI

K22 =

 

 

L2 0 0 0 4EI z z

L

- • L : is the length of the beam.

- • Iy : is the principle moment of inertia around y-axis.

- • Iz : is the principle moment of inertia around z-axis.

- • Iρ : is the torsional moment of inertia.

- • E : Young’s modules of the aluminium beam.

- • G : Coulomb’s modules of the aluminium beam.

IV. VIRTUAL JOINT MODELLING

Kinematic model for each leg can be represented as depicted in Fig.4 where Ac, Ps refers to active joint and prismatic joint respectively.

Fig. 4. Kinematic Model

In VJM, active prismatic joint could be presented by adding 1-DOF virtual spring, while elastic links can be expressed as rigid links followed by 6-DOF virtual spring as illustrated in Fig.5.

Fig. 5. VJM Model

The corresponding transformation can be obtained by extending equation 1 as follows:

T = TbaseTx (di,1)Tx (θi,1)Ry (qpassive i,1)Tx(l) T3D (θi,2−7)Ry (qpassive i,2)Tx(l)T3D (θi,8−13) Ry (qpassive i,3)Tx (di,2)Ttool

(6) where Tbase and Ttool are identity matrices in our case. For the ith leg, θi,j is the jth virual joint. The T3D θi,j−(j+5) is the 6-DOF virtual spring, and it can be described as the following transformations:

T3D θi,j−(j+5) = Tx (θi,j)Ty (θi,j+1)Tz (θi,j+2) Rx (θi,j+3)Ry (θi,j+4)Rz (θi,j+5)

(7)



In [9], the classical Cartesian stiffness matrix for each chain can be caculates as:

 

−1

Kc,i0 = Jθ,iKθ,i−1Jθ,iT

(8) where the Jθ is the numerical jacobian matrix calculated with respect to the virtual joint variables, and the Kθ is the aggregated spring stiffness matrix. It is 13×13 diagonal matrix contains three major diagonal components which are the stiffness parameters of the flexible elements. The first component is a scalar value represents the active joint stiffness and it is assumed as 106N/m. The second and third components are 6 × 6 matrices represents the stiffness properties of the two links respectively.

 

 

Kactive 0 0 0 K22,6×6 0 0 0 K22,6×6

(9)

Kθ =

13×13

K22 is used because virtual joints are attached to the right-end of the links. Using the classical Cartesian stiffness matrix Kc0 obtained at equation 8, the Cartesian stiffness matrix of the chain i can be found:

Kc,i = Kc,i0 − Kc,i0 Jq,iKCq,i (10) where

KCq,i = Jq,iT KC,i0 Jq,i −1 Jq,iT KC,i0 (11)

In equation 11 Jq is the numerical jacobian matrix calculated with respect to the passive joint variables. It is 6 × 3 matrix since the single chain consists of three passive joints.

Therefore, Cartesian stiffness matrix Kc of the whole robot can be computed as the summation of the Cartesian stiffness matrices of the two chains [9].

Kc = n

Kci (12) i=1

Consequently, the EE deflection ∆t can be obtained from Hook’s law as shown below.

∆t = Kc−1W (13)

V. MATRIX STRUCTURAL ANALYSIS

The MSA model for the double pantograph [12] is depicted in Fig.6 where the structure is represented by 21 nodes. These nodes are connected to each other based on the structure connection type. The following table explains the nodes connections and connection types.

TABLE 2 NODES CONNECTIONS AND CONNECTION TYPES

| Flexible Links | Passive Joints | Rigid Joints | Elastic Joints | Rigid Support |
| --- | --- | --- | --- | --- |
| <3,5>, <4,6>, <7,9>, <8,10>, <11,13>, <12,14>, <15,17>, <16,18> | <0,3>, <2,4>, <5,6>, <9,11>, <10,12>, <13,14>, <17,19>, <18,e>, <19,e> | <0,1>, <5,8>, <6,7>, <13,16>, <14,15> | <1,2> | <0> |

Fig. 6. MSA Model

The rigid support constraint at node 0 can be expressed as follows:

W0 ∆t0

= 06×1 (14) The deflection and loading constraints for flexible links

06×6 I6×6 could be described as:

  

   =

Wi

Wj

−I6×6 06×6 Ki,j11 Ki,j12 06×6 −I6×6 Ki,j21 Ki,j22

06×1 06×1

∆ti

∆tj

(15) where i and j are the node numbers. It should be noted that the stiffness matrices used in flexible links constraints should be global matrices, thus a transformation from local stiffness matrices to the global coordinate system are applied as described below.

Ki,j11 Ki,j12 Ki,j21 Ki,j22

=

QKi,j11QT QKi,j12QT QKi,j21QT QKi,j22QT

(16) where Q is 6×6 matrix consists of two main diagonal rotation matrices R which describes the rotation of the link end.

R3×3 03×3 03×3 R3×3

(17) The passive joints allows rotations around y-axis, then the

Q = constraints are:

  

   (18)

  

   =

  

  

05×6 05×6 λr,yi,j −λr,yi,j

05×1 05×1 01×1 01×1

Wi

Wj λr,yi,j λr,yi,j 05×6 05×6 λp,yi,j 01×6 01×6 01×6 01×6 λp,yi,j 01×6 01×6

∆ti

∆tj where λp,yi,j = 0 0 0 0 1 0 (19)





1 0 0 0 0 0 0 1 0 0 0 0 0 0 1 0 0 0 0 0 0 1 0 0 0 0 0 0 0 1 λr,yi,j =

(20)

 

  while rigid joints constraints are as follows:

  

   =

Wi

Wj

06×6 06×6 I6×6 −I6×6 I6×6 I6×6 06×6 06×6

06×1 06×1

∆ti

∆tj

(21) Since the active elastic joint 1-2 is translate along x-axis, the constraints can be described by the following equation:

  

   =

 

 

 

 

W1

W2

05×6 05×6 λr,x1,2 −λr,x1,2 I6×6 I6×6 06×6 06×6 λe,x1,2 01×6 Kaλe,x1,2 −Kaλe,x1,2

05×1

06×1 01×1

∆t1

∆t2

(22) where λe,x1,2 = 1 0 0 0 0 0 (23)





0 1 0 0 0 0 0 0 1 0 0 0 0 0 0 1 0 0 0 0 0 0 1 0 0 0 0 0 0 1 λr,x1,2 =

(24)

 

 

The external force is applied at node e and it is donated by the following equation:

I6×6 06×6

We ∆te

= Wext (25)

We can aggregate all of the system linear equations in matrix form using the above-mentioned equations (14)-(25). Since we have 21 nodes, and each node is represent by wrench and deflection, the aggregated matrix could be described as shown below:

 

  =

Wag126×1 ∆tag120×1 ∆te

A282×246 B282×6 C6×246 D6×6

0282×1 Wext

(26) The above equation can be written in the following form:

Mx = v (27) where the main matrix M is 288 × 252. The system is over constrained, since M matrix is not invertible. In order to solve such a system, we need to find the smallest 2-norm x which at the same time provides the least residual e. e = Mx − v (28)

As the minimum of ||e||2 coincides with the minimum of (Mx − v)T(Mx − v), then the solution to this least squares problem is given by a pseudoinverse similar to finding the extremum as follows:

2MT(Mx − v) = 0 MTMx = MTv x = (MTM)−1MTv then x can be calculated as x = M+v (29) So, the EE deflection ∆t is the last 6 elements of vector x:

∆t6×1 = 06×246 I6×6 x252×1 (30) and it is obtained due to the applied wrench Wext.

VI. RESULTS

VJM and MSA are implemented to calculate the deflection due to applied loads in different directions. The robot EE deflection is found at multiple points in the workspace. Since, the structure translate along z-axis, deflection calculations are performed at 30 different points from minimum to maximum height limits introduced in section II-C.

Fig. 7. Deflection using MSA due to wrench [100, 0, 0, 0, 0, 0]N

Fig. 8. Deflection using VJM due to wrench [100, 0, 0, 0, 0, 0]N

Fig. 9. Deflection using MSA due to wrench [0, 100, 0, 0, 0, 0]N

Fig. 10. Deflection using VJM due to wrench [0, 100, 0, 0, 0, 0]N

Fig. 11. Deflection using MSA due to wrench [0, 0, 100, 0, 0, 0]N

Fig. 12. Deflection using VJM due to wrench [0, 0, 100, 0, 0, 0]N

Fig.7 and Fig.8 show the deflections, using MSA and VJM approaches respectively, due to 100N load applied in the x-axis direction. Fig.9 and Fig.10 present the deflections due to 100N load applied in the y-axis direction, while the deflections due to 100N load in the z-axis are shown in the last two figures Fig.11 and Fig.12. According to the deflections scatter plot analysis, it is notable that the deflections computed by VJM approach due to an external force applied in x-axis and z-axis are not reasonable comparing to the results obtained from MSA method. This is because of some limitations of using VJM to model this type of structures. The idea is when implementing VJM, we extended the kinematic model for each chain with virtual joints, but there is no way to introduce passive joints constraints which connect the two legs such as connections <5,6> and <13,14> described in the MSA model Fig.6. Without these constraints, we can justify the huge deflection values which are shown in

Fig.8 and Fig.12. VII. DISCUSSION

In fact, the classical structure for the VJM approach is a parallel connection of strictly serial chains. But it is not the case in the double pantograph structure as the two chains are connected through the passive joints <5,6> and <13,14> described in the MSA model Fig.6. Hence, we cannot add the Cartesian stiffness matrices for the two legs through applying equation 12 directly. This is the main reason for such a difference between MSA and VJM results, especially when the robot EE is subjected to loads in x-axis and z-axis.

The VJM results can be enhanced by deriving the Cartesian stiffness matrix for the whole system at once. As explained in [13], the potential energy of the system can be expressed as

θiTKθiθi (31)

E (θ1,θ2) = i=1

At the equilibrium, this energy must be minimised subjected to the geometrical constraints. The physical interpretation for these constraints is described by the passive joints between the two chains. Mathematically, it can be presented as t = gi(θi,qi),i = 1,2 (32) and it can be introduced in the Lagrange function as follows.

θiTKθiθi + λTi (t − gi (θi,qi)) (33)

L(θ1,θ2,q1,q2) = i=1 i=1

We can obtain the Cartesian stiffness matrix for the system including the constraints. This will be implemented in future work as an approach for improving VJM results.

However, VJM results in sensible deflection values when applying force in the direction of the axis of rotation, y-axis, and we can visually notice that both MSA and VJM result in approximately similar deflection values in this case. Therefore, a comparison is held in the following section to analyse the results of both MSA and VJM due to an applied force in y-axis.

VIII. MSA AND VJM COMPARISON

In this section, a comparison between MSA and VJM is presented in terms of computation time and deflection deference due to an applied load in y direction as VJM limitations do not allows us to compare the deflections due to forces in x and z directions with the corresponding deflections from MSA.

Fig. 13. Deflection Average

It is found that the total time elapsed to execute MSA approach for deflection calculations of 30 points is 2.77 seconds, while 5.77 was recorded as an execution time for the same points using VJM approach.

Fig.13 represents the scatter plots for both MSA and VJM due to 100N exerted in y-axis. The maximum deflection is found at the maximum height that the EE can reach. The figure shows that 5.2mm is the maximum deflection of VJM approach, while only 1.3mm is the MSA maximum deflection. In addition, it shows the average deflection of both approaches.

Fig. 14. Deflection Deference

The deflection deference is depicted in Fig.14 where the deference percentage at the maximum points is around 76%. This deference is due to passive constraints between the two legs which are not applied in the VJM implementation.

IX. CONCLUSION

This paper presents the stiffness analysis of the double pantograph transmission system. Stiffness modelling is implemented using VJM and MSA techniques to find the EE deflection at different points in the workspace. After deflection calculations, deflection scatter plots are built to analyse the maximum deflection due to 100N force along x,y,z directions respectively. It was found that VJM method has some limitations to model this structure, which prevent evaluating the deflection with an external load in x,z directions. A comparative analysis is performed to compare both MSA and VJM computation complexity and deflection deference. It was noticeable that MSA has less computation cost and no limitations to model the double pantograph structure compared to VJM approach.

REFERENCES

[1] S. Staicu, “Spatial parallel robots,” in Dynamics of Parallel Robots. Springer, 2019, pp. 191–243.

[2] B. Hamidi, “Design and calculation of the scissors-type elevating platforms,” Open Journal of Safety Science and Technology, vol. 2, pp. 8–15, 2012.

[3] D. Kirsanov, I. Sevostianov, O. Rodionov, and M. Ostanin, “Stiffness analisys of the tripteron parallel manipulator,” in 2020 International Conference Nonlinearity, Information and Robotics (NIR). IEEE, 2020, pp. 1–6.

[4] S. Yan, S. Ong, and A. Nee, “Stiffness analysis of parallelogram-type parallel manipulators using a strain energy method,” Robotics and Computer-Integrated Manufacturing, vol. 37, pp. 13–22, 2016.

[5] B. Bouzgarrou, J. Fauroux, G. Gogu, and Y. Heerah, “Rigidity analysis of t3r1 parallel robot with uncoupled kinematics,” in Proc. of the 35th International Symposium on Robotics (ISR), Paris, France, 2004.

[6] A. Klimchik, A. Pashkevich, and D. Chablat, “Fundamentals of manipulator stiffness modeling using matrix structural analysis,” Mechanism and Machine Theory, vol. 133, pp. 365–394, 2019.

[7] D. Popov, V. Skvortsova, and A. Klimchik, “Stiffness modeling of 3rrr parallel spherical manipulator.” in ITTCS, 2019.

[8] D. Deblaise, X. Hernot, and P. Maurine, “A systematic analytical method for pkm stiffness matrix calculation,” in Proceedings 2006 IEEE International Conference on Robotics and Automation, 2006. ICRA 2006. IEEE, 2006, pp. 4213–4219.

[9] A. Klimchik, “Enhanced stiffness modeling of serial and parallel manipulators for robotic-based processing of high performance materials,” Ph.D. dissertation, Ecole Centrale de Nantes (ECN); Ecole des Mines de Nantes, 2011.

[10] C. Quennouelle and C. m. Gosselin, “Instantaneous kinemato-static model of planar compliant parallel mechanisms,” in International Design Engineering Technical Conferences and Computers and Information in Engineering Conference, vol. 43260, 2008, pp. 163–173.

[11] S.-F. Chen and I. Kao, “Conservative congruence transformation for joint and cartesian stiffness matrices of robotic hands and fingers,” The International Journal of Robotics Research, vol. 19, no. 9, pp. 835–847, 2000.

[12] A. Klimchik, A. Pashkevich, and D. Chablat, “Stiffness modeling of navaro ii transmission system,” IFAC-PapersOnLine, vol. 52, no. 13, pp. 701–706, 2019.

[13] A. Pashkevich, A. Klimchik, S. Caro, and D. Chablat, “Stiffness modelling of parallelogram-based parallel manipulators,” in New Trends in Mechanism Science. Springer, 2010, pp. 675–682.

# Citations

1. [Read the article [NIR_2022_stiffness-analysis]](https://innopolis.university/filespublic/NIR_2022_stiffness-analysis.pdf), file b4cee548cca7

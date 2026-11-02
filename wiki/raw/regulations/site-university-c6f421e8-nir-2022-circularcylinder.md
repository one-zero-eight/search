---
type: regulation
title: "Read the article [NIR_2022_circular-cylinder]"
resource: "https://innopolis.university/filespublic/NIR_2022_circular-cylinder.pdf"
source_kind: official-document
language: ru
section: "site/university"
sources:
  - resource: "https://innopolis.university/filespublic/NIR_2022_circular-cylinder.pdf"
    id: "d0ebe1b1b013"
    title: "Read the article [NIR_2022_circular-cylinder]"
    last_modified: "2026-10-24T23:44:43+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-10-24T23:44:43+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Read the article [NIR_2022_circular-cylinder]

On the stability of the system of Thomson vortex n-gon and a moving circular cylinder

Leonid Kurakin

Water Problems Institute, RAS Moscow, Russia Southern Mathematical Institute, VSC RAS Vladikavkaz, Russia Southern Federal University Rostov on Don, Russia lgkurakin@sfedu.ru

Irina Ostrovskaya

Southern Federal University Rostov on Don, Russia ivostrovskaya@sfedu.ru

Abstract—The stability problem of a moving circular cylinder of radius R and a system of n identical point vortices uniformly distributed on a circle of radius R0 is considered. The circulation around the cylinder is zero. There are three parameters in the problem: the number of point vortices n, the added mass of the cylinder a and parameter q = R2/R02.

The linearization matrix and the quadratic part of the Hamiltonian of the problem are studied. As a result, the parameter space of the problem is divided into the area of linear stability, where nonlinear analysis is required, and the instability area. In the case n = 2, 3 two domains of linear stability are found. In the case n = 4, 5, 6 there is found one domain. In the case n 7, the studied solution is unstable for all of problem parameters values. The obtained results in the limiting case at a → ∞ agree with the known results for the model of point vortices outside the circular domain.

Index Terms—Point vortices, Hamiltonian equation, Thomson polygon, Stability

I. INTRODUCTION

Thomson vortex polygon is a configuration of identical point vortices located at the vertices of a regular polygon. This vortex configuration owes its name to two famous scientists. W. Thomson (Lord Kelvin) posed the stability problem of such a polygon on the plane in connection with his vortex theory of the atom [1]. Its study in a linear formulation was began by J. J. Thomson [2] and completed by T. H. Havelock [3]. The history of solving this problem in linear and nonlinear formulation is described in detail in [4], [5].

The numerous studies have been devoted to the dynamics of point vortices outside a circular domain (see review [6]). The stability problem of stationary rotation of Thomson vortex polygon outside unmoving circular cylinder with the zero circulation around the cylinder had been solved by Havelock in [3]. The nonlinear analysis of this problem required the involvement of the resonances theory of equilibria of Hamiltonian systems (see review [7]). It turned out that two resonances lead to instability, although stability takes place in the linear formulation. The effect of circulation in the problem under

The work of the first author was carried out within the framework of the project no. FMWZ-2022-0001 of the State Task of the IWP RAS consideration in the case of a vortices outside a circle was studied in [8].

Various forms of the motion equations for a moving rigid circular cylinder interacting with an n point vortices were obtained in [9]–[13]. The history of the derivation of these equations is given in the introduction of [13].

In this paper, the stability of a system consisting of a Thomson n-gon and a moving cylinder is studied for arbitrary n with zero circulation around cylinder. A linear stability analysis is carried out for an arbitrary number of point vortices n 2. In the case n 6, linear stability conditions are found under which nonlinear analysis is required to solve the stability problem. It is prooved that in the case of n 7, the considered system is unstable for all values of the problem parameters. Here we also correct the erroneous results of the paper [14] for the case n = 2.

II. FORMULATION OF PROBLEM

The motion of a circular cylinder interacting with n identical point vortices is considered. As a result of the reduction of the complete equations of motion, system of equations are written in the complex form in [12] n az˙c = av = −iγzc + iγ0

( zj − zj), j=1

R2v zk2 iγ zk − iγ0 zk − zk z˙k = −v +

+

+ n

zk − zj −

zk − zj

+ iγ0

, k = 1,...,n. j=1 j =k

(1)

Here complex variables zc = xc + iyc, zk = xk + iyk define the position of the cylinder and point vortices, v = v1 +iv2 is

R2 zk is the reflection of the kth vortex from the boundary of the circle, R is cylinder radius, the constant coefficient a involves the added mass of the cylinder, and the constants γ and γ0 are connected with the circulation cylinder velocity, zk = around the cylinder Γ and the intensity of identical point vortices Γ0 by the formulae γ = 2Γπ and γ0 = Γ

2π. Further in the paper we will consider the case

γ = nγ0. (2)

Note that in [15] a complete bifurcation analysis of the motion of the circular cylinder and two point vortices with arbitrary circulation was carried out in the case not considered here when circulation γ and the total impulse of the system are equal to zero. In [13] this works has been made for case of two point vortices with opposite intensity.

The system (1), (2) can be written in the form

, γ0z˙k = −2iHz

. (3) nγ0z˙c = −2iHz c k

The Hamiltonian H = H(z,z), z = (zc,z1,...,zn) is given by formula n γ02

a|v|2 + ln |zk|2 − R2 − nln|zk|2 +

H = k=1 γ02 2 1≤k<j≤n ln R2 − zjzk 2 − ln|zj − zk|2 .

+

The system (3) has the solution

(4)

2π n (k−1) (5) zc = 0, zk = eiω ntuk, uk = R0ei corresponding of the stationary rotation of the n point vortices around the cylinder with constant angular velocity ωn:

R2 R02 γ0 2R02

2n 1 − qn

. (6) ωn = −

3n − 1 −

, q =

The point vortices are located uniformly on a circle of radius R0, R0 > R. Then 0 < q < 1.

Without loss of generality, we will further assume that γ0 = 1, R0 = 1. (7) The change of variables nt, zk = √1 + 2rkei(ω zc = (qc + ipc)eiω

(8) nt+2π(kn−1)+θk), k = 1,...,n, reduces the system (3), (4) to the perturbation equations with the Hamiltonian E=E(ρ), ρ = (qc,r1,...,rn,pc,θ1,...,θn):

E(ρ) = H(z(ρ),z(ρ))+ n

(9) ωn

nqc2 + np2c − n − 2

+ rk . k=1

The stationary solution (5) corresponds to a continuous family of equilibria

C = {qc = pc = r1 = ... = rn = 0, θ1 = ... = θn}. (10)

The stability of the continuous family of equilibria (10) is equivalent to the orbital stability of the stationary solution (5).

Let

E2(ρ) = Snρ,ρ (11) be the quadratic terms of the expansion of the Hamiltonian E(ρ) into Taylor series in power of ρ in a neighborhood of the zero equilibrium position. Here ·,· is the scalar product.

The symmetric matrix Sn has the form

  

   na1n nb1nh1 0 −nb2nhn−1 nb1nh1 F1n nb1nhn−1 G0n 0 nb1nhn−1 na1n nb2nh1

Sn =

−nb2nhn−1 −G0n nb2nh1 F2n

The vectors h1 and hn−1 are given by formulas

n

(1,cosν,...,cos(n − 1)ν), h1 =

(12)

n

(0,sinν,...,sin(n − 1)ν), hn−1 =

Here ν = 2nπ, coefficients a1n, b1n and b2n are given by formulas

√2n(1 + q) 4a

√2n(1 − q) 4a ωn

n 2a

+

, b1n =

, b2n =

. a1n =

Symmetric matrices F1n, F2n and skew-symmetric matrix G0n are circulant matrices: n−1 n−1 fmjCj, G0 def=

Fmn def= fm0In + g0jCj, j=1 j=1





0 1 0 0 ... 0 0 0 1 0 ... 0 ... ... ... ... ... ...

,

C =

 

 

0 0 0 0 ... 1

1 0 0 0 ... 0 where In is unit matrix of size n × n. The coefficient fmj and g0j can be written as:

fm0 0(q) + fm1 0(a,q), fmj(q,a) = fm0(q,a) =

fmj0 (q) + fmj1 (a,q), (13) g0j(q,a) =

g00j(q) + g01j(a,q), j = 1,...,n − 1.

Here the coefficients fmj0 and g00j match the corresponding coefficients written out in the papers [3], [8].

The coefficients fmj1 and g01j, j = 0,...,n − 1 are given by equalities f11j(a,q) = (1 + q)2 2a cosνj, j = 0,...,n − 1 f21j(a,q) = (1 − q)2 2a cosνj, g01j(a,q) =

(14) q2 − 1 2a sinνj.

The values λmk and iλ0k are eigenvalues of matrices Fmn and G0n given in the form λmk(q,a) =

λ0mk(q) + λ1mk(q,a), (15) where λ01k, λ02k and λ00k are the same as in the papers [3], [8] and λ11k, λ12k and λ10k are defined as n(1 + q)2 4a λ111 = λ11,n−1 =

, n(1 − q)2 4a λ121 = λ12,n−1 =

, n(q2 − 1) 4a λ101 = −λ10,n−1 =

, λ11k = λ12k = λ10k = 0, k = 1,n − 1.

(16)

The symmetric matrix Sn has zero eigenvalue, corresponding to family of equilibrium (10). The family C is Lyapunov stable in the exact nonlinear setting if the Hamiltonian E(ρ) has an extremum on it. To do this, it is necessary that all the eigenvalues of the matrix Sn except for a simple zero have the same sign. As shown later in the Proposition 2, this does not hold.

The linearization matrix Ln of the system with Hamiltonian

(9) about the zero solution has the form

Ln = 2K−1JSn, J =

0 In+1 −In+1 0

, (17) where K−1 is diagonal matrix of size (2n + 2) × (2n + 2):

K−1 = diag (1/n,−1,...,−1,1/n,−1,...,−1,).

Then matrix Ln can write as

  

  .

0 b1nhn−1 a1n b1nh1 nb2nhn−1 G0n −nb1nh1 −F2n

Ln = 2

−a1n −b1nh1 0 b2nhn−1 nb1nh1 F1n nb1nhn−1 G0n

Instability of solution (5) occurs when the linearization matrix Ln has eigenvalues with positive real part.

In the case n = 2 the characteristic polynomial of the linearization matrix L2 is given by equality det(σI6 − L2) = σ2Ψ12(σ2), (18) where Ψ12(σ2) is biquadratic polynomial

Ψ12(σ2) = σ4 + 8p11σ2 + 16p01, (19) p11 = a212 − 8b1b2 + λ11λ21, (20) p01 = a212λ11λ21 − 4b212λ21 − 4b222λ11 + 16b212b222. (21)

If n 3, the eigenvalues of the linearization matrix Ln are root of the following polynomial: det(σI2n+2 − Ln) = σ2 n

Ψjn(σ2). (22) j=1

Here Ψ1n(σ2) is bicubic polynomial Ψ1n(σ2) = σ6 + 4p21σ4 + 16p11σ2 + 64p01 (23) p21 = 2λ11λ21 + 2λ201 − 4nb1nb2n + a21n p11 = 4n2b21nb22n − 4nλ201b1nb2n − 4nλ01λ21b21n

− 4nλ01λ11b22n + 4nλ01a1nb1nb2n − 4nλ21λ11b1nb2n − 2nλ21a1nb21n − 2nλ11a1nb22n + λ401 − 2λ201λ21λ11

+ 2λ201a21n + λ221λ211 + 2λ21λ11a21n p01 = 2nb1nb2n λ01 + nb21nλ21 + nλ11b22n + a1nλ201 −λ11λ21a1n)2 , the polinomial Ψjn(σ2), j = 2,..., n−21 for n > 3 are biquadratic polynomials

Ψjn(σ2) = σ4 + 8p1jσ2 + 16p0j (24) p1j = λ1j λ2j + λ20j, p0j = λ1jλ2j − λ20j 2 . In the case of even n 4 the polynomial Ψn

2 ,n(σ2) has the form

2 ,n(σ2) = σ2 + 4λ11λ12. (25)

Ψn

In the case n 4, the polynomial (24), (25) do not depend on parameter a, and their roots coincide with the corresponding eigenvalues of the linearization matrix in the case of a unmoving cylinder [3]. In [3] it has been shown that among them for n 7 there is at least one eigenvalue with positive real part. Hence, and from the analysis of polynomials Ψjn in the case of 2 n 6, the following statements follow.

Proposition 1.

- 1) If n 7 the solution (5), (6) is unstable for any values

of problem parameters: 0 < q < 1, a > 0.

- 2) If n = 2 all eigenvalues of the linearization matrix L2

lie in the imaginary axes, if coefficients of biquadratic polynomial Ψ12(σ2) satisfy to conditions: p01(q,a) 0, p11(q,a) 0, D12(q,a) = p211 − 4p01 0. (26)

- 3) If 3 n 6, all eigenvalues of the linearization matrix

Ln lie in the imaginary axes, if all following conditions are valid:

- a) The cubic polynomial Ψ1n(s) is stable, that is,

satisfies the Vyshnegradsky conditions: p01(q,a) 0, p11(q,a) 0, p21(q,a) 0, ∆1n(q,a) = p11p21 − p01 0. (27) and its discriminant D1n is not negative: D1n(q,a) = −4p321p01 + p221p211 − 4p311+ + 18p01p11p21 − 27p201 ≥ 0. (28)

- b) The coefficients and discriminant of quadratic

polynomials Ψjn(s), j = 2,..., n2 for n > 3 are not negative: p0j(q) 0, p1j(q) 0, Djn(q) = p21j − 4p0j 0.

(29)

- 4) The linearization matrix Ln, n = 2,...,6 has at least

one eigenvalue in the right half-plane, if at least one of the conditions 2) or 3) is violated.

Let’s analyze the eigenvalues of the matrix Sn in the case 2 n 6.

If n = 2, then its characteristic polynomial has the form det(ΛI6 − S2) = Λ(Λ − λ12)Φ21(Λ)Φ22(Λ), where Φ2m(Λ) are quadratic polynomials Φ2m = Λ2 + k1mΛ + k0m = 0, k1m = −2a12 + λm1, k0m = 8b2m2 − 2a12λm1.

In the case n = 3, 5 the characteristic polynomials of the matrix Sn are det(ΛI8 − S3) = Λ(Λ − λ13)Φ231(Λ), det(ΛI12 − S5) = Λ(Λ − λ15)Φ251(Λ)Φ252(Λ). (30)

In the case n = 4, 6, we have det(ΛI10 − S4) = Λ(Λ − λ14)Φ241(Λ)Φ42(Λ), det(ΛI14 − S6) = Λ(Λ − λ16)Φ261(Λ)Φ262(Λ)Φ63(Λ).

(31)

The polynomials Φn1(Λ) in (30), (31) are cubic polynomials given by formula

Φn1(Λ) = Λ3 + k21Λ2 + k11Λ + k01, k21(q,a) = −na1n − λ21 − λ11, k11(q,a) = − b21n + b22n n2 + a1n (λ21 + λ11)n

+ λ21λ11 − λ201, k01(q,a) = 2λ01b1n b2n + λ11b22n + λ21b21n n2 − a1n λ21λ11 − λ201 n.

The polynomial Φ42(Λ) and Φ63(Λ) are written as

(32)

(Λ) = (Λ − λ1,n

)(Λ − λ2,n

).

Φn,n

The polynomials Φ52(Λ) and Φ62(Λ) are quadratic polinomial:

Φn2(Λ) = Λ2 + k12Λ + k02, k12(q) = −λ12 − λ22, k02(q) = λ12λ22 − λ202.

(33)

The calculations show that in the case 3 n 6 the roots of cubic polynomials Φn1(Λ) have different signs. Similar case takes place for polynomial Φ21Φ22 at n = 2.

Proposition 2. The matrix Sn, 2 n 6, has eigenvalues with different sings for all values of the problem parameter and quadratic form (11) is sign-variable one. Thus nonlinear stability analysis is required in linear stability domains (white domain in the Figs 1–3).

III. FORMULATION OF RESULTS

In the case n 7 the solution (5), (6) is unstable for all of values of problem parameter (Proposition 1).

We introduce the parameter α:

1 − a 1 + a

. (34) α =

In the case 2 n 6, analysis of the eigenvalues of the matrices Ln and Sn show that the space of parameters (q,α), where 0 < q < 1, and −1 < α < 1, is divided into two types of areas shown in the Figs. 1–3:

- 1) White area is linear stability area, where the eigenvalues

of linearization matrix Ln are all purely imaginary, and the eigenvalues of the matrix Sn have the different signs. In this case, a nonlinear analysis is required to conclude stability.

- 2) Shaded area is instability area. The linearization matrix

Ln has eigenvalues with positive real part. The solution

(5), (6) is instable in the exact nonlinear setting.

The Figs. 1, 2 present the cases n = 2,3 respectively, and the Fig. 3 shows the cases n = 4,5,6.

For n = 2,3 two areas of linear stability are found. In the Fig. 1 the curves α12 are given by equation D12 = 0, where D12 is discriminant of biquadratic polynomial (19). The curves α22 are defined by equality p01 = 0, where p01 is given by (21). In the Fig. 2 the boundary of linear stability domains are given by equality D13 = 0, where D13 is given by formula (28).

In the cases n = 4,5,6 one linear stability area is shown in Fig. 3. Its boundary consists of the curve α1n, given by the equation D1n = 0 and straight line q = q∗n. Here D1n is given by equality (28). The constants q∗n was calculate by Havelock in [3]: q∗2 ≈ 0.148536, q∗3 ≈ 0.273695, q∗4 ≈ 0.308125, q∗5 ≈ 0.334596, q∗6 ≈ 0.295985.

Fig. 1. The diagram of stability of stationary rotation of the Thomson vortex n-gon around cylinder (the solution (5)) in the case n = 2

Fig. 2. The diagram of stability of the solution (5) in the case n = 3

REFERENCES

[1] W. Thomson, “Floating magnets (illustrating vortex systems)”, Nature, London, vol. 18, pp. 13–14, 1878.

[2] J.J. Thomson, A Treatise on the Motion of Vortex Rings: An essay to which the Adams Prize was adjudged in 1882, in the University of Cambridge. London: Macmillan, pp. 94–108, 1883.

[3] T. H. Havelock, “The stability of motion of rectilinear vortices in ring formation”, Phil. Mag., vol. 11, no 70, pp. 617-633, 1931.

[4] L. G. Kurakin and V. I. Yudovich, The stability of stationary rotation of a regular vortex polygon, Chaos, vol. 12, pp. 574–595, 2002.

[5] A. V. Borisov and I. S. Mamaev, “The Kelvin problem and its solutions”, in Mathematical Methods in the Dynamics of Vortex Structures. Moscow–Izhevsk, Institute of Computer Sciences, pp. 261–265, 2005.

[6] A. A. Kilin, A. V. Borisov, and I. S. Mamaev, “The Dynamics of Point Vortices Inside and Outside a Circular Domain”, Fundamental and Applied Problems in the Theory of Vortices, pp. 414–440, 2003.

[7] L. G. Kurakin, A. P. Melekhov, and I. V. Ostrovskaya, “A Survey of the Stability Criteria of Thomson’s Vortex Polygons outside a Circular Domain”, Bol. Soc. Mat. Mexicana, vol. 22. N 2. P. 733-744, 2016.

[8] L. Kurakin and I. Ostrovskaya “On the Effects of Circulation around a Circle on the Stability of a Thomson Vortex N-gon”, Mathematics, vol.

**8.** p. 1033, 2020.

[9] S. M. Ramodanov, “Motion of a circular cylinder and N point vortices in a perfect fluid,” Regular Chaotic Dyn., vol. 7, pp. 291, 2002.

[10] B. N. Shashikanth, J. E. Marsden, J. W. Burdick, and S. D. Kelly, “The Hamiltonian structure of a two-dimensional rigid circular cylinder interacting dynamically with N point vortices,” Phys. Fluids, vol. 14, pp. 1214, 2002.

[11] A. V. Borisov, I. S. Mamaev, and S. M. Ramodanov, “Motion of a circular cylinder and N point vortices in a perfect fluid,” Regular Chaotic Dyn. vol. 8, pp. 449, 2003. a) b) c)

Fig. 3. The diagram of stability of the solution (5) in the case

- a) n = 4, b) n = 5, c) n = 6

[12] A. V. Borisov, I. S. Mamaev, S. M. Ramodanov, “Dynamics of a cylinder interacting with point vortices”, in Mathematical Methods in the Dynamics of Vortex Structures. Moscow–Izhevsk, Institute of Computer Sciences, pp. 286–307, 2005.

[13] I. S. Mamaev, I. A. Bizyaev, “Dynamics of an unbalanced circular foil and point vortices in an ideal fluid”, Phys. Fluids, vol. 33, 087119, 2021.

[14] A. V. Borisov and L. G. Kurakin, “On the Stability of a System of Two Identical Point Vortices and a Cylinder”, Proc. Steklov Inst. Math., vol. 310, pp. 25–31, 2020.

[15] S. M. Ramodanov and S. V. Sokolov, “Dynamics of a Circular Cylinder and Two Point Vortices in a Perfect Fluid”, Regular Chaotic Dyn., vol. 26, no. 6, pp. 675–691, 2021.

# Citations

1. [Read the article [NIR_2022_circular-cylinder]](https://innopolis.university/filespublic/NIR_2022_circular-cylinder.pdf), file d0ebe1b1b013

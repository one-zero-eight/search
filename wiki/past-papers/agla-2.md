---
type: page
title: "Past exam papers: AGLA 2"
description: "Past exams and tests of AGLA 2 at Innopolis University (18 papers, 2020–2026), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "agla-2"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "AGLA 2"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: AGLA 2

Exams and tests of **AGLA 2** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2026: Midterm

Files: [AGLA 2 Midterm 2026.pdf](https://glebpopov.notion.site/356e746cceef807fb43cf501dee9335d)


Midterm 2026
1. Let


A=


4 5 −2 6 0
.
1 1 0 1 0

a) Find the four fundamental subspaces of A.

[3 pts]

b) Verify the orthogonality relations between the corresponding subspaces.

[2 pts]

2. Use the normal equations to find the least-squares line y = ax + b for the points
(1, 2), (2, 4), (3, 5), (4, 4), (5, 6).
[5 pts]
3. Let



4 2
A=
.
2 4

a) Find the eigenvalues and eigenvectors of A.

[3 pts]

3

b) Compute A − A.

[1 pt]

c) Verify that the eigenvectors are orthogonal.

[1 pt]

4. Solve the system


x1 + 2x2 + 3x3 + 4x4 = 5,
2x1 + 4x2 + 6x3 + 8x4 = 10,


x1 + 2x2 + 2x3 + 3x4 = 4.
[5 pts]
5. Let




1 1
A = 0 1  ,
1 0

 
1
b = 1 .
1

a) Find the projection matrix P onto Col(A).

[3 pts]

b) Find the projection of b onto Col(A).

[2 pts]

6. Let


A=


i 1 i
.
1 −i 0

a) Solve Ax = 0.

[3 pts]

b) Show that N (A) ⊥ C(AH ), but N (A) ̸⊥ C(AT ).

[2 pts]

1

## 2026: Test 1

Files: [AGLA 2 Test 1 2026.pdf](https://glebpopov.notion.site/356e746cceef807d9644df23f9b1f396)


AGLA II TEST I
1. Compute the LU decomposition of


1 3 5
A = 3 12 18
5 18 30
and solve the system
LU x = b,
2. Consider the matrix

 
1

b = 1 .
1



4 1 1
A = 1 3 0 .
1 0 2

(a) Check whether it is positive definite or not.
(b) Is the LU decomposition for this matrix unique? Why?
3. Find the complete solutions of the linear system
 

 x
 
1 3 1 2  
1
2 6 4 8  y  = 3 .
z 
0 0 2 4
1
w
4. Apply the Gram–Schmidt process to the following vectors to orthonormalize them,
and use it to compute the QR decomposition of the matrix
A = [a, b, c],
where

 
1
a = 2 ,
0

 
1
b = 1 ,
0

 
1
c = 1 .
1

5. Find a basis for the orthogonal complement of the row space of the following matrix:


1 0 2
.
1 2 6
Split
x = [2, 2, 2]
into a row-space component and a nullspace complement xn .

1

## 2026: Test 2

Files: [AGLA 2 Test 2 2026.pdf](https://glebpopov.notion.site/356e746cceef80e28811e95dd686427f)


AGLA TEST 2

Problems Only
Task 1
Given the quadratic form:
Q(x) = 4x21 + 2x22 + 3x23 − 2x1 x2 + 4x1 x3
(a) Write Q(x) in the form xT Ax (find the symmetric matrix A).
(b) Determine whether A is positive definite or not.

Task 2
Given the function:
f (x, y) = x2 − xy + y 2
(a) Find all critical points of f .
(b) Compute the Hessian matrix of f .
(c) For each critical point, determine its type (local minimum, local maximum, or
saddle point).

Task 3
Given the matrix:




1 0 0
A=
0 2 0

(a) Find the singular values of A.
(b) Find the full SVD of A, i.e., matrices U , Σ, and V such that A = U ΣV T .
(c) Find the SVD of 5A.

1

Task 4
Assume A and B are both symmetric positive definite matrices (of the same size).
(a) Explain why A + B is also positive definite.
(b) Explain why det(A) > 0.
(c) For what values of k is the following matrix positive definite?


4 k 0
k 9 0
0 0 1

2

Solutions
Task 1 — Solution
(a) The symmetric matrix A is constructed so that for i ̸= j, the coefficient of xi xj in
Q(x) is 2aij . For x2i terms, the coefficient is aii .
a11 = 3, a22 = 2, a33 = 4
Coefficient of x1 x2 = −2 ⇒ 2a12 = −2 ⇒ a12 = −1, a21 = −1
Coefficient of x1 x3 = 4 ⇒ 2a13 = 4 ⇒ a13 = 2, a31 = 2
Coefficient of x2 x3 = 0 ⇒ a23 = a32 = 0
Therefore,



3 −1 2
A = −1 2 0 ,
2
0 4

Q(x) = xT Ax.

(b) Check leading principal minors:
• ∆1 = 3 > 0


3 −1
• ∆2 = det
=6−1=5>0
−1 2
• ∆3 = det(A):
det(A) = 3(2 · 4 − 0) − (−1)((−1) · 4 − 0 · 2) + 2((−1) · 0 − 2 · 2)
= 3(8) + 1(−4) + 2(−4) = 24 − 4 − 8 = 12 > 0
Since all leading principal minors are positive, A is positive definite.

Task 2 — Solution
(a) First partial derivatives:
fx = 2x − y = 0

⇒

y = 2x

fy = −x + 2y = 0

⇒

x = 2y

3x = 0

⇒

Substitute y = 2x into x = 2y:
x = 2(2x) = 4x

⇒

x=0

Then y = 0. The only critical point is (0, 0).
(b) Second partial derivatives:
fxx = 2,
Hessian matrix:

fyy = 2,


fxy = −1

2 −1
H=
−1 2



(c) At (0, 0):
det(H) = 4 − 1 = 3 > 0,

fxx = 2 > 0

The Hessian is positive definite, so (0, 0) is a local minimum.
3

Task 3 — Solution
(a) Compute AAT :


 1 0


1 0 0 
1
0
T
0 2 =
AA =
0 2 0
0 4
0 0


Eigenvalues: 4, 1. Singular values: σ1 = 2, σ2 = 1.
(b) U : eigenvectors of AAT :
λ = 4 : (0, 1)T

⇒

u1 = (0, 1)T ;

λ = 1 : (1, 0)T


0 1
U=
1 0

Σ:

⇒

u2 = (1, 0)T



2 0 0
Σ=
0 1 0

V : eigenvectors of AT A:


1 0 0
AT A = 0 4 0
0 0 0
Eigenvalues: 4, 1, 0. Corresponding eigenvectors:
v1 = (0, 1, 0)T ,

v2 = (1, 0, 0)T ,


0 1 0
V = 1 0 0
0 0 1

v3 = (0, 0, 1)T

Thus A = U ΣV T .
(c) For 5A, multiply Σ by 5:
T

5A = U (5Σ)V ,



10 0 0
5Σ =
0 5 0

U and V remain unchanged.

Task 4 — Solution
(a) For any non-zero vector x:
xT (A + B)x = xT Ax + xT Bx
Since A and B are positive definite, both terms are > 0. Hence xT (A + B)x > 0.
Also (A + B)T = AT + B T = A + B, so A + B is symmetric positive definite.
(b) A symmetric positive definite matrix has all eigenvalues positive. The determinant
equals the product of eigenvalues, so det(A) > 0.

4




4 k 0
(c) Matrix M = k 9 0. Leading principal minors:
0 0 1
∆1 = 4 > 0




4 k
= 36 − k 2 > 0
k 9

⇒

−6 < k < 6

∆3 = det(M ) = 1 · (36 − k 2 ) > 0

⇒

−6 < k < 6

∆2 = det

Therefore, M is positive definite for −6 < k < 6 .

5

## 2025: Test 2

Files: [AGLA 2 Test 2 2025.pdf](https://glebpopov.notion.site/1e0e746cceef808eb1c2e4b3b023ad6a)


Full Name: Innopolis University

Test 2 AG&LA T
Variant 1 Spring 2025
Duration: 90 Minutes 08.04 2025

You need to perform this exam alone and without the use of any equipment or book, apart
from this booklet and pens. Please do not consult any person or use any equipment,
otherwise you will be disqualified from this exam at the very first attempt.

Good Luck'

Grade Table (for teacher use only
Question 1 2 3 4 5 6 | Total
Points 7 2 3 3 2 2 19
Score

Exercises

. Consider the matrix A,

2 1-i
A‘(l+i 3 )

(a) (6 points) Diagonalize matrix A by constructing its eigenvalue matrix A and its eigenvector matrix
S

(b) (1 point) Find A inverse using results from previous part.
. (2 points) Find all eigenvalues of matrix A;

1 2 3
A= -3 -2 -1
£1 0
. (3 points) If eigenvalues of matrix A are \; = =2, ), = 2 Ay = 7, find all eigenvectors of matrix A;

113
A=10 20
6 3 4

. (3 points) Solve the 4 by 4 system, Fyc = y, if the right-hand sides are yo = 2, yy = 0,43 = 2, ys = 0
(2 points) (EXTRA points) Find all roots of the equation 2* + i = 0.
. (2 points) (EXTRA points) Find the lengths of u,v € C*.

OnlinePhotoScanner.com

Full Name: Innopolis University
Test 2 AG&LA T

Variant 2 Spring 2025
Duration: 90 Minutes 0R.04 2025

";Yuu need l;p:f:rm this exam alone and without the use of any equipment or book, apart

fromn this booklet and pens. Please do not consult any person or use any equipment,
otherwise you will be disqualified from this exam at the very first attempt.
Good Luck!

Grade Tuble (for teacher use only
Question: 1 2 3 4 5 6 | Total
Points: 7 2 3 3 2 2 19
Score:

Exercises

A (2+8n/§ 2-4“/5)

(a) (6 points) Diagonalize this matrix by constructing its cigenvalue matrix A and its eigenvector
matrix S

(b) (1 point) Find A inverse.
(2 points) Find all cigenvalues of matrix A;

1 -1 2
A=[2 0 3
0 -2 -§

. (3 points) If cigenvalues of matrix A are A} = =3, Ay = =2, Ay = —1, find all eigenvectors of matrix

A;
-3 0 0
A= 1 2 -4
-2 3 -5

(3 points) Solve the 4 by 4 system, Fyc = y. if the right-hand sidesare yg =0,y = ~21, py =0, 3 =
-2

. (2 points) (EXTRA points) Find all roots of the equation z* — i = 0.
. (2 points) (EXTRA points) Find the lengths of u,v € C*.

OnlinePhotoScanner.com

Pall Namst oo lnnopolis University

Tem 2 ACLLA I

Vu~3 Spring 2025

Duration: %0 Mmutes 08 04 2025
==

i Yaﬂhwﬁ-huhdwm-dqwam;w;]
’i from this hooklet and pens. Please do not consult amy person or use any equipment, |
i} otherwise you will be disqualified from this exam at the very first sttempt. ]
li Good Lasck! |

= =

Grade Table (for teacher wee only)
{Quesion | 1 | 2 | 3 | 4 5
(Pomte | 7 | 2 { 2
pP—

4
4

E

6
2

-
3

3 | 3

’'.

._...“..‘.
.
T -

N S .

J

1
-
1

A

3-1 =2
"[ ‘ -l-c]
(a) (6 points) Diagonalize this matrix by constructing its eigenvalue matrix A and its eigemvector
matrix §

(b) (1 point) Find A inverse
2. (2 potnts) Find all eigenvalues of matrix A;

3. (3 points) Hf eigenvalues of matrix A are ); = 0,Ay = 1, A3 = 3, find all eigenvectors of matrix A;

1 -1 0
A=|-1 2 -1
0 -1 1
4 (3 points) Soive the 4 by 4 system, Fec = y, if the right-hand sides are o = 1 +im. 3y = Oy =
1-mm =0

5. (2 points) Find all roots of the equation z* + 1 =0.
6. (2 poimts) Find the lengths of u,v € C.

OnlinePhotoScanner.com

## 2024: Final

Files: [ALGA 2 Final 2024.pdf](https://glebpopov.notion.site/ae7aa32a420544af9fa09c0d19d5ab31)


AGLA2 2024 Final
Variant 2
May 8, 2024
1. (4 pts). Diagonalize matrix A by finding its eigenvalues and its eigenvectors.
(1 pt). Find A inverse.



8
−1 + i
A=
−1 − i
7
2. (5 pts). Show that A and B are similar B = M 1 AM by finding matrix M :




8
−1 + i
7 − i 1 − 2i
A=
B=
−1 − i
7
1+i 8+i
3. (5 pts) For which α and β quadratic form Q(x, y, z) is positive definite:
Q(x, y, z) = 2αx2 + y 2 + z 2 − 2βxy + 4xz
4. (5 pts) Solve the second order differential equation system:
 2
d x(t)

= 8x(t) − (1 − i)y(t)

dt2


 d2 y(t) = −(1 + i)x(t) + 7y(t)
dt2

x(0) = 1, x′ (0) = 0



 y(0) = 1,
y ′ (0) = 0
5. (5 pts). Using least squares method to find the coefficients a and b of the curve:
f (x) = a sin(x) + b cos(x), that best fits following points:
x
f (x)

0
−0.8

π/4
0

π/2
1



A −B
6. (5 pts) If A + iB is Hermitian matrix (A and B are real) show that
is
B A
symmetric matrix.
7. (5 points) Prove that any real square matrix can be factored into A = QS, where Q is
orthogonal and S is symmetric positive semidefinite.

1

## 2024: Midterm

Files: [AGLA 2 Midterm 2024.pdf](https://glebpopov.notion.site/7cab2266bcc14784848a015af8436c31)


Tid Term Exam. Variant 1 Innopolis University

Full Name: AG&LAII
Group #: Spring 2024
Duration: 120 Minutes 13.03.2024

You need to perform this exam alone and without the use of any equipment, apart from this booklet and
pens. You can use only 1 sheet of A4 paper with formulas on both sides. Please do not consult any person
or use any equipment, except for a simple non-programmable calculator. Otherwise, you will be
disqualitied from this exam at the first attempt.

Good Luek!
Grade Table (for teacher use only)
Question 1 T 2 3 4 5 6 7 Total
| Points 3 6 4 6 6 6 4 35
Score

1. (3 points) Let§; = {x,y,z : x—2y—z=8andS, ={x,y,z: x—y+2z=2}

X
Find the line of intersection of the planes S, and S in vector form; V= [y]
z

2. Considering the matrix, A and the vector b,

-1 1 2
o1 e
A=ty 1| b=ilg

-1 -1 1

(a) (4 points) Find the projection of b onto the column space of A.
(b) (1 points) Split b into p + e, with p in the column space and e orthogonal to that space.

(c) (1 point) Which of the four fundamental spaces of A contains e.

3. Considering the following measurements:
tl2 1 1 2
b|-1 0 1 1
(a) (4 points) Find the best straight-line fit (Least squares) to the measurements.
(b) (2 point) Find the projection matrix P onto the column space of matrix 4:

1 -2

L =1
A—1 1|

1 2

4. (6 points) Find the dimensions of the four fundamental subspaces associated with A,
depending on the parameters a and j.

a 7 5 10
131 8 4
A=l 11 2

8 5 3 6

5. Find an orthonormal basis for the subspace spanned by the vectors: a,, a, and asz (4 points).
Then express A = [y, z, as] in the form of QR (2 points).

6. (4 points) Prove that the matrix A(m X n) has the same nullspace as ATA

7. (4 points) Prove that if the matrix A(n X n) is symmetric the dot product of the vectors x €
R™ and Ay is the same as the vectors Ax and y € R"

Innopolis University
AG&LAII
Spring 2024

Mid Term Exam. Variant 2
Full Name:
Group #:

Duration: 120 Minutes 13.03.2024

You need to perform this exam alone and without the use of any equipment, apart from this booklet and
pens. You can use only 1 sheet of A4 paper with formulas on both sides. Please do not consult any person
or use any equipment, except for a simple non-programmable calculator. Otherwise, you will be
disqualified from this exam at the first attempt.

Good Luck!

Grade Table (for teacher use only)

Question 1 2 3 4 5 6 7 Total
Points | 3 6 4 6 6 5 4 35
Score

1. (3 points) Let S; = {x,y,z: x+y—4z=8}and §, ={x,y,z: x + 2y + 2z = 2}

X
Find the line of intersection of the planes S; and S, in vector form: ¥ = {y]

Z

2. Considering the matrix, A and the vector b,

1 1 3
-1 1| #_]2
A= _1 O,b— 1
0 2 -1

(a) (4 points) Find the projection of b onto the column space of A.
(b) (1 points) Split b into p + e, with p in the column space and e orthogonal to that space.
(¢) (1 point) Which of the four fundamental spaces of A contains e.

3. Considering the following measurements:

t | -1

0 1

52

2
0 I I

(a) (4 points) Find the best straight-line fit (Least squares) to the measurements,
(b) (2 point) Find the projection matrix P onto the column space of matrix A:

1 -1
|t o
A‘11
1 2

4. (6 points) Find the dimensions of the four fundamental subspaces associated with 4,

depending on the parameters e and /3.

2 11 2
sl 8 6 12
118 0
9 5 4 8

5. Find an orthonormal basis for the subspace spanned by the vectors: a,, a, and az (4 points).

Then express A = [ay, a,, a;] in the form of QR (2 points).

—2] 4 1
a1=[1 ,a2=[1],a3=[—-2].
2 -1 2

6. (4 points) Prove that the matrix AT(n X m) has the same nullspace as AAT

7. (4 points) Prove that if the matrix A(n X n) is symmetric the dot product of the vectors x €
R™ and Ay is the same as the vectors Ax and y € R"

## 2024: Test 1

Files: [AGLA 2 Test 1 2024.pdf](https://glebpopov.notion.site/8b07d02859d1471aa339c9a516183e6b)


Linear Algebra. Test 1. Variant 1.

First name

- Last name Group Points#1
I . =
am, . (initials), confirming that | have read the following rules and agree to comply with
them, that all solutions on this paper is my own work.
(signature)

Rules:

— no talking AT ALL is allowed during the exam and after it (if you are still in the room)

— Yyou can use 1 sheet of A4 paper with formulas on both sides

— any electronic devices are not allowed except for a simple non-programmable calculator

~ when time is up, you have to put down your pen (pencil) and do NOT write anything else

— you can NOT leave your seat till the end of the test

1. The 4x4 matrix A reduces to the identity matrix I by the following four row operations:
o E21: subtract row 1 from row 2;
. Ezi:add 2*row 1 to row 3;
. E32: subtract 3*row 2 from row 3;
° Es1: subtract 2*row 1 from row 4;
o Es3: add row 3 to row 4;

Write and compute A" (3 points) and A (2 points).
2. Consider matrix A
1 2 0
A=12 6 -1
0 -1 1
a. Find the factorization A = LDU (3 points)
b. Find A inverse (2 points).
3. Consider matrix A

11 2 4 by
_12 1 3 6 _|b2
4=10 11 2 b= bs
1 0 1 2 by
a. Reduce the matrix A to its ordinary Echelon form U (1 point).
b. Find and describe every solution to Ax = 0 (1 point).

¢. For which nontrivial right-hand sides (find a condition on by, b3, b3, by) Ax = b

is solvable (1 point)?

d. Provide an example of vector b # 0 that makes this system solvable (1 point).
e. Find the complete solution for Ax = b using b from previous part (3.d)

(1 point).

Linear Algebra. Test 1. Variant 2.

L Firstname Last name Group Points#l
‘\ﬁ_r —

I am, (initials), confirming that | have read the following rules and agreTe to comply with
them, that all solutions on this paper is my own work.

(signature)

Rules:
- no talking AT ALL is allowed during the exam and after it (if you are still in the room)
~ You can use 1 sheet of A4 paper with formulas on both sides
— any electronic devices are not allowed except for a simple non-programmable calculator
- when time is up, you have to put down your pen (pencil) and do NOT write anything else
- you can NOT leave your seat till the end of the test

N :
@ The 4x4 matrix A reduces to the identity matrix I by the following four row operations:

. E2q1: add 2*row 1 to row 2;

. E3q: subtract row 1 from row 3;

1 E32: subtract 3*row 2 from row 3;
° Ea1: add row 1 to row 4;

. Ea3: subtract 2*row 3 from row 4;

Write and compute A (3 points) and A (2 points).

-1 -2 0
A=|-2 -1 2

0 2 1

2. Consider matrix A

Find the factorization A = LDU (3 points)
Find A inverse (2 points).

3. Consider matrix A

1 21 3 by
13 2 4 _ b2
4= 1 4 3 5 b_b3
01 11 I

a. Reduce the matrix A to its ordinary Echelon form U (1 point).

b. Find and describe every solution to Ax = 0 (1 paint).

¢. For which nontrivial right-hand sides (find a condition on by, b3, bz, by) Ax = b
is solvable (1 point)?

d. Provide an example of vector b # 0 that makes this system solvable (1 point).

e. Find the complete solution for Ax = b using b from previous part (3.d)
(1 point).

## 2024: Test 2

Files: [AGLA 2 Test 2 2024.pdf](https://glebpopov.notion.site/dbb876ee94d94407a4361e0b4c0f2b92)


Linear Algebra. Test 2. Variant 1.

First name Last name : Group Points#1
I'am, __ (initials), confirming that | have read the following rules and agree to comply with
them, that all solutions on this paper is my own work.
(signaturey
Rules:
- no talking AT ALL is allowed during the exam and after it (if you are stilf in the room)
— You can use 1 sheet of A4 paper with formulas on both sides
— any electronic devices are not allowed except for a simple non-programmable czlc_lator
- when time is up, you have to put down your pen (pencil) and do NOT write anythirg eise
— you can NOT leave your seat till the end of the test
1. Find matrix e4 (4 points) and det(e*) (1 points):
-3 4 0
A=|1 0 0|
0 1 0
2. Write down the first order equation system for the following differential equation and
solve it (4 points):
y +3y"—4y' =0
=2 y(©)=0 y0)=-1
Is the solution of this system will be stable? (1 points)
3. For what number a is the matrix A positive definite?

A=

1 1 2
1 a+1 -2

2 -2 a-2

Linear Algebra. Test 2. Variant 2.

First name Last name GI’OUp Points#1

lam, __ (initials), confirming that | have read the following rules and agree to comply with
them, that all solutions on this paper is my own work.

(signature)
Rules;

- no talking AT ALL is allowed during the exam and after it (if you are still in the room)
- Yyou can use 1 sheet of A4 paper with formulas on both sides
- any electronic devices are not allowed except for a simple non-programmable calculator

- when time is up, you have to put down your pen (pencil) and do NOT write anything else
— Yyou can NOT leave your seat till the end of the test

1. Find matrix e/ (4 points) and det(e4) (1 points):
-2 3 0

A=]1 0 0]
0 10

2. Write down the first order equation system for the following differential equation and
solve it (4 points):

Yy +2y"=3y'=0
©=3 y©)=0 y0)=1
Is the solution of this system will be stable? (1 points)

3. For what number a is the matrix A positive definite?

1 1 2
A=|1 a-1 2

2 2 a+1

## 2023: Final

Files: [AGLA 2 Final 2023.pdf](https://glebpopov.notion.site/5e7dd8e921af45b8a314d3bd22d09873)


—

|
|

Lincar Algebra. Final exam. Variant 1.

First name Iast name | Group | Points j!
[ BSI- i

I am,

(initials), confirming that I have read the following rules and agree to comply with

them, that all solutions on this paper is my own work.

Rules:

(signature)

no talking AT ALL is allowed during the exam and after it (if you are still in the room)
you can use | sheet of Ad paper with formulas on both sides

any electronic devices are not allowed except for a simple non-programmable calculator
when time is up, you have to put down your pen (pencil) and do NOT write anything else
you can NOT leave your seat 1ill the end of the test

(4 points). Diagonalize matrix A by finding its eigenvalues and its eigenvectors. Find A

inverse. (1 point).
5 -1+ i]
-1=i 4

(5 points). Show that A and B are similar B = M~*AM by finding matrix M:

— [ ¥ — [ - — [
&= [_15_ i 14+ ‘] BiE [31 +2il 61+ 251'(]

(5 points) For which @ and # quadratic form Q(x,y, z) is positive definite:

Q(x,y,2) = ax® 4+ 2y? + 22 + 4Bxy + 4xz

(5 points) Solve the second order differential equation system:
d*u(t) -5 -1
dez [-1 -5 A6
A1) YR
\#(0) = [1] () = [0]
(5 points) Using least squares method to find the coefficients a and b of the curve
f(x) = acos(x + b) that best fits following points:
X 0 | =4 |02
fe) (=10 |1

Note: cos(x + y) = cos(x) cos(y) — sin(y) sin(x).
A -—B].
(5 points). If A+ iB is a unitary matrix (4 a$nd B are real) show that |-B 4 ] is an

orthogonal matrix.
(5 points) Prove that for any square matrix A(n X n) with eigenvalues {41, 22,..., 4y} the
multiplication: (4 — 2,1)(A — Az1) - (4 — A,,I) produces the zero matrix.

## 2023: Midterm

Files: [AGLA 2 Midterm 2023.pdf](https://glebpopov.notion.site/171f3d82626d4638aef8ff854935a891)


Mid Term Exam. Variant 2 Innopolis University

Full Name: AG&LATI
Group #: Spring 2023
Duration: 120 Minutes 23.03.2023

You need to perform this exam alone and without the use of any equipment, apart from this booklet and
pens. You can use only 1 sheet of A4 paper with formulas on both sides. Please do not consult any person
or use any equipment, except for a simple non-programmable calculator. Otherwise, you will be
disqualified from this exam at the first attempt.

Good Luck!

Grade Table (for teacher use only)

Question 1 2 3 4 5 6 7 Total
Points 3 6 4 6 6 6 4 35
Score

1. (3 points) True or False statement.

For matrix A(mxn) with rank(4) < m & rank(4) < n is True | False

C(A") # C(A)
Dim[C(AT)] # Dim[C(4)]
Dim C(A") + Dim N(4) = n.

2. Considering the matrix, A and the vector b,

|’1 1 1
b=E g = 22
A= b=
-2 0 1
02 -1

(a) (4 points) Find the projection of b onto the column space of A.
(b) (1 points) Split b into p + e, with p in the column space and e orthogonal to that space.
(c) (1 point) Which of the four fundamental spaces of A contains e.

3. (4 points) LetS, = (x,y,z: x+2y—4z=8}andS, ={x,y,z: x+y+2z=3).

X
U= [y] — lies at the line of intersection of the planes S, and S. Find 7.
z

4. Considering the following measurements:

t | -1 0 1 2
o i =1 1 2

(a) (4 points) Find the best straight-line fit (Least squares) to the measurements,
(b) (2 point) Find the projection matrix of vector b = [1,~1,1,—2]" onto the column space of matrix A:

1 <oy
o I
A= 7}
5 2

5. (6 points) Find the dimensions of the four fundamental subspaces associated with A4, depending on the
parameters a and /.

a 6 8 12
iz 2
A—lﬂlo

9 4 5 8

6. Find an orthonormal basis for the subspace spanned by the vectors: a5, a, and a3 (4 points).
Then express A = [a,, a;, a;] in the form of QR (2 points).

7. (4 points) Prove that if the matrix A(n X n) is symmetric the dot product of the vectors x € R™ and Ay is
the same as the vectors Ax and y € R"

## 2023: Test 1

Files: [AGLA 2 Test 1 2023.pdf](https://glebpopov.notion.site/02bd6de22bf942c39983a450818b8c67)


1.1

1.2

Linear Algebra. Test 1: Solutions

The 4x4 matrix A reduces to the identity matrix / by the following four row operations:

Ea1; subtract row 1 from row 2;

F31: add 2*row 1 to row 3;

Fa: subtract 3*row 2 from row 3;
Far: subtract 2%row 1 from row 4;
Fa3; add row 3 to row 4;
Write and compute A’ (3 points) and A (2 points).
= FoFo kb By
0y 1
0
0

A=

(— 2=~ Sl

1
[1
0
0

O

c o - o

——a

0

0

-0 O C

- o C

==

|
=]

BB EEyFyd=] = A"

0

|
0
0

oo - o

0
0
1
0

|
0

0
0
0
I¢

0

1,40

\

A=
0
1
3
0

0 oY1
00 (o
o2
0 1l

0 0Y1
0 0/o
L ofo

|‘.‘2

0

0

c o -

0

0

0
01
00

0

0
1
0

-0 O ©

1

c o o -

-1
0
0

0
i
0
0

0
|
0
1]
0

.|

S - C©

0
0
0
1

-2
2

c W - ©

=k

0
0
0
1

The 4x4 matrix A reduces to the identity matrix / by the following four row operations:

Ez1: add 2*row 1 to row 2;

F31: subtract row 1 from row 3;

F32: subtract 3*row 2 from row 3;

E4v: add row 1 to row 4;

Ea3: subtract 2*row 3 from row 4;
Write and compute A (3 points) and A (2 points).

o C = o

c o -

o -0 o

-0 O O

- o O

—_ o o —

S —- -

EyE EpEEnA=] = A7 = E E E B E,,

oo -2

e o - o

0

0
1
0

o - o

)

0

ol

- C <

o c o —

1
]

0
0

0
|
-3

ax o

S W -

0 0y(1 00
0 0|0 1 0
L oll=1 01
0 1)lo oo
o EnER ELEY
0 01 00
0 o0flo 10
1 offo o 1
0 1)l-1 00

0

0
of
1

- o 2

|

2
0
0

[ I — N —

0

|
0
0

o e — ©

o —- O ©

o - o o

- o o

_—- o <

o W - o

W - o

- O

=]

-_-—- o

—_o o O

24

2.2

Consider matrix A
1 4 0
A= {1 6 —3]
0 -3 2

Find the factorization A = LDU (3 points)
Find A inverse (2 points).

1 0 0\/1 0 0\,1 1 0
3
A=LDU =LpIT =} 13 010 5(1’ 01 -¢
0 -3 1/\0 0 =/\g ¢ 1

Consider matrix A

1 2 0
A= [2 3 -1
0 -1 -2

Find the factorization A = LDU (3 points)
Find A inverse (2 points).

1 0 0y/1 0 O0\N/1 2 0
A=LDU=LDL"=(2 1 o) 0 -1 0)(0 1 1)
01 1/\0 o

=7 4 =2
Al = ( 4 =2 1 )
-2 1 -1

3

Consider matrix A

1 1 4 2 by
216 3 b,
A= =
01 2 1 B =
1 0 2 1 by
Reduce the matrix A to its ordinary Echelon form U (1 point).
1 1 4 2 1 1 4 2
|2 1 % 3 _jo -1 -2 -1
A=l 1 217 1o 0 0o o
1. 0 2 4 0 0 0 0
Find a solution for each free variable and describe every solution to Ax = 0 (1 point).
1 1 4 2] J A ) 4 2 1[*
2 1 6 3||% 0 -1 -2 -=1f|*2
= =0=
012 1||x]%2 o 0o o offx
1 0 2 1)[% 0 0 0 0 11X
-1 —2]
& -1 2 -2
= Tl o Xn2 =62 4
1 0]

For which nontrivial right-hand sides (find a condition on by, b3, by, by) Ax = b is
solvable (1 point)?

b,
_| b2
bZ'—bl
Provide an example of vector b # 0 that makes this system solvable (1 point).
1
s |
= b= 1
0
Find the complete solution for Ax = b using b from previous part (3.d) (1 point).
1 1 4 21*% 1 1 1 4 2% 1 0
2 1 6 3||X]|_|1 0 -1 =2 =1{(*%2]|_|-1 ] bk
01 2 1|[xs|T[1 T fo o ofllxs|T|o |7 %o
1 0 2 11[Xs 0 0 0 0 J1Xs 0 04

0

0

0 -1 -2
3 = Ryt By + Ry = é + ¢ _01 +c, _12

0 1 0

3.2 Consider matrix A

1 1 @2 3 by
1 2 3 4 b,
o= = |72
1 3 4 5 ¢ by
0 1 4 A by
Reduce the matrix A to its ordinary Echelon form U (1 point).
. 1 2 3 1. 1 2 3
|1t 2 3 4 _loo1 11
4=11 3 45/7YFJo o000
0 1 1 1 0o 0 0 O
Find a solution for each free variable and describe every solution to Ax = 0 (1 point).
1 1 2 3][* 1 1 2 3][*
1 2 3 4f|%]|_ 01 1 1||¥2|_g=
13 4 s|[x|7%% o 0o 0 ofx
0 1 1 1J1X4 0 0 0 0Jl*
-2 -1
= = —iL ¢ -1
N1 = €1 ol Xnz =C2| ¢
1 0

For which nontrivial right-hand sides (find a condition on by, b3, by, by) Ax = bis

solvable (1 point)?
b,

by
2b, — by
by — by

Provide an example of vector b # 0 that makes this system solvable (1 point).

1

.
=:»b_1
0

Find the complete solution for Ax = b using b from previous part (3.d) (1 point).

2 3] |1 11 2 3]\ 1 1
34x2]=11=01 1x2’=lo=f=0
4 s5[[x| 7 |1 0 0 0 offxs[ |0 »~ o
11 0 0000 0

-1

b= =

O
W=
w

X4 X4 0

1
0
0
=2
B R -1 -1
= X=Xp+ Xyt w2 = ]+C1 o|*e|1

1 0

OO

## 2023: Test 2

Files: [AGLA 2 Test 2 2023 Var 1 Solutions.pdf, AGLA 2 Test 2 2023.pdf](https://glebpopov.notion.site/49edad8cda7445bb8a3bce888f01f509)

### AGLA 2 Test 2 2023 Var 1 Solutions.pdf
AGLA 2 Teet 2 2023 Vor 4

@ gleh_ pp
@ -t 2 o
A= ( 1.0 OB
O 4 ¢
1=\ 2 0 1) (A-X X = hjtl o . =
i X of=o0 (h=2Iyw (49 8)|x) = o
o 4 -\

— [ O
XA = o
A

C-A)(X)+2x =0
“A’=\"4ex=0

Xy
A(N+x-e)=o0 )?j:(’:;)
=0
l>>\, SETIAN 3) (A*MI)K*—* 42 -1 o)( ::)TO
ot 2 O 4 -4 Xs
A=0 =
A=A

Pidenva lues on
moun  diagong |

O Q

. 9 4y -4 1 =3 &3 E fod -4
S—; _ = —— _ 2 = i
(? . 1) S Tan (i o :(é f g
Y O iz 5

- |G2e) \
5”‘A5=(o~2§§> => A= §

o
o
/’Or\oo
n_ -1
A= S o (taro ) S
O 0 4"
> oo P | . o
e 4N _ 4 (9 00 = ¢ 0o -
: rzon!/'\_szgr\!(o(—z)“q) S =Sloeto s
@ Q4 \0 O e'
2 3
C u A 4 4 4= Jev=p
N O o 3 -4 O
e = . ! 32 2
0 2 4|0 etal\[ £ ol=[ o2 det () = L
14 4)\ooetf\s 2 N = B
3 50 Belgtsd Gzt g

"(4) . , -y ey “t2 oy
y (o) di q y' 01 0 y
A U M)
-\ 2 o
1 - 0o|=o0
O 4 =X

Matlei x IS fthe same with  matrix A)\Ae have alread y
CO[cula{ed Hs S and <7

. o« 4 1 © O -4 ~-%£ 1 2
U= (o0 -2 4 Oeol|lt Lagl| ol=
1T 44/l o o e 4 2 o) | 4
elo 2e’-2 o 2 +4
3e? 3e? © = 2 3 4
N 3 e +
e -4 3 = 2e” -2 =" {) &=
de? ee:&)et—{ © - de? 1 ( Je ®
2% ueoaetd gy 1 P!
\—E;—— et »e?
=0 Ve (M) <o O => nof  stoble
Ao = -2 2) Some N\ =g =3
1w olher 3 <O, nNo = no{  steady

NT Novo  yes = unstable

### AGLA 2 Test 2 2023.pdf
Linear Algebra. Test 2. Variant 1.

First name Last name Group Points#1
BS1-
I am, (initials), confirming that | have read the following rules and agree to comply with

them, that all solutions on this paper is my own work.

(signature)

— no talking AT ALL is allowed during the exam and after it (if you are still in the room)

- you can use 1 sheet of A4 paper with formulas on both sides

— any electronic devices are not allowed except for a simple non-programmable calculator
— when time is up, you have to put down your pen (pencil) and do NOT write anything else
— you can NOT leave your seat till the end of the test

1. Find det(e*) for the matrix (5 points):

-1 2 0
A=[1 0 o0f
0 1 0

2. Write down the first order equation system for the following differential equation and
solve it (4 points):

{y"'+ y'—=2y'=0
y'(=2 y©0)=0 y0=1

Is the solution of this system will be stable? (1 points)

3. Find the SVD (4 points) and the pseudoinverse (1 points) of the matrix:

Linear Algebra. Test 2. Variant 2.

First name

Last name

Group

Points#1

BS1-

I am,

(initials), confirming that | have read the following rules and agree to comply with
them, that all solutions on this paper is my own work.

(signature)

— no talking AT ALL is allowed during the exam and after it (if you are still in the room)

— you can use 1 sheet of A4 paper with formulas on both sides

= any electronic devices are not allowed except for a simple non-programmable calculator
— when time is up, you have to put down your pen (pencil) and do NOT write anything else

— you can NOT leave your seat till the end of the test

1. Find det(e*) for the matrix (5 points):

A=

-2 3 0
1
0

2. Write down the first order equation system for the following differential equation and

solve it (4 points):

{y'"+ 2y"=3y'=0
y' (=3, y(0)=0, y(0)=1

Is the solution of this system will be stable? (1 points)

3. Find the SVD (4 points) and the pseudoinverse (1 points) of the matrix:

{2 2
A:
=)

## 2022: Final

Files: [AGLA 2 Final 2022.pdf](https://glebpopov.notion.site/a6d8738c602b45de8248f6f3255f0482)


Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

Points#1

I am, _____ (initials), confirming that I have read the following rules and agree to comply with them, that all solutions on this paper is my own
work.
________________ (signature)
Rules:
−
−
−
−

no talking AT ALL is allowed during the exam and after it (if you are still in the room)
when time is up, you have to put down your pen (pencil) and do NOT write anything else
you can NOT leave your seat till the end of the test
any electronic devices are not allowed except for a simple non-programmable calculator

4 3
.
1 2 

1. (5 points) Find 𝑑𝑒𝑡(𝑒 𝐴 ) for A = 

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

2. (5 points). Show that A and B are similar B = M −1 AM by finding matrix M :

4 3
3 4 
A=
B=


1 2
1 3

Points#2

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

3. (4 points) Which symmetric matrix 𝐴(3 × 3) produced this quadratic:
𝑥 𝑇 𝐴𝑥 = 2(𝑥12 + 𝑥22 + 𝑥32 − 𝑥1 𝑥2 − 𝑥2 𝑥3 )
(1 points) Is matrix 𝐴(3 × 3) positive definite?

Points#3

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

Points#4

4. (4 points) Write down the first order equation system for the following differential equation
and solve it:
 y − y − 2 y = 0

 y(0) = 6, y(0) = 0, y(0) = 3
(1 points) Is the solution of this system will be stable?

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

5. (5 points). Prove that all the eigenvalues of a Hermitian matrix are real.

Points#5

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

 −1 1
6. (4 points) Find the SVD and the pseudoinverse (1 points) of the matrix A = 
 0 −1

Points#6

0
1 

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

Points#8

7. (5 points) Prove that for any square matrix 𝐴(𝑛 × 𝑛) with eigenvalues {𝜆1 , 𝜆2 , . . . , 𝜆𝑛 } the
multiplication: (𝐴 − 𝜆1 𝐼)(𝐴 − 𝜆2 𝐼) ⋅⋅⋅ (𝐴 − 𝜆𝑛 𝐼) produces the zero matrix.

## 2021: Final

Files: [AGLA 2 Final 2021.pdf](https://glebpopov.notion.site/62662d9fd36443d39ea84dd9cc1024ac)


Linear Algebra. Final exam. Variant 1.
First name

Last name

Group

Points#1

BS1I am, _____ (initials), confirming that I have read the following rules and agree to comply with them, that all solutions on this paper is my own
work.
________________ (signature)
Rules:
−
−
−
−

no talking AT ALL is allowed during the exam and after it (if you are still in the room)
when time is up, you have to put down your pen (pencil) and do NOT write anything else
you can NOT leave your seat till the end of the test
any electronic devices are not allowed

1. (5 points) What values of α produce instability (divergence) the solution of the next
differential equation:


 y  −  y  + y = 0


 y  ( 0 ) = 1, y ( 0 ) = 1

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

2

2. (4 points) Find 𝑑𝑒𝑡(𝑒 𝐴) for A = 

2

1
.
3

Points#2

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

3. (5 points) For which α and β quadratic form 𝑄(𝑥, 𝑦, 𝑧) is positive definite:
𝑄(𝑥, 𝑦, 𝑧) = 𝑎𝑥 2 + 𝑦 2 + 2𝑧 2 + 2𝛽𝑥𝑦 + 4𝑥𝑧

Points#3

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group

Points#4

BS1-

4. (5 points) Write down the first order equation system for the following differential equation
and solve it:
 y  + y  − 2 y  = 0

 y (0) = 6, y (0) = 0, y (0) = 3

(1 points) Is the solution of this system will be stable?

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

5. (4 points). Show that A and B are similar B = M −1 AM by finding matrix M :
1
A=
1

0
1
 B=
0
0

0

0

Points#5

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS11

0

0

1

6. (4 points) Find the SVD and the pseudoinverse of the matrix A = 

0

1

Points#6

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group

Points#7

BS1-

7. (2 points) Prove that for any symmetric matrix A (nxn) and any vectors x , y  R n is true:

( Ax , y ) = ( x , Ay )

Linear Algebra. Final exam. Variant 1.
First name

Last name

Group
BS1-

8. (5 points) If a matrix P ( 3  3 ) projects every vector in R onto the plane:
3

x + 2 y + z = 0 , find the eigenvalues and the eigenvectors of P .

Points#8

## 2021: Midterm

Files: [AGLA 2 Midterm 2021.pdf](https://glebpopov.notion.site/b716aa3654654524923809cdf1cb4b36)


Full Name: _________________________
Mid Term Exam
Variant 1

Innopolis University
AG&LA II
Spring 2021

Duration: 120 Minutes

16.03.2021

You need to perform this exam alone and without the use of any equipment or book, apart from this
booklet and pens. Please do not consult any person or use any equipment, otherwise you will be
disqualified from this exam at the very first attempt.
Good Luck!
Grade Table (for teacher use only)
Question
Points
Score

1
3

2
7

3
5

4
6

5
4

6
5

Total
30

1. (3 points) True or False statement.
Statement

True

False

The vectors b that are not in the column space C(A) form a subspace.
The column space of 2A equals the column space of A.
dim(row space) + dim(nullspace) = number of columns.
2. Considering the matrix, A and the vector b,
1 1
𝐴= 1 0 ,
1 2

3
𝑏= 1
7

(a) (3 points) Find the projection of b onto the column space of A.
(b) (3 points) Split b into 𝑝 + 𝑞, with p in the column space and q perpendicular to that space.
(c) (1 point) Which of the four subspaces contains q.
3. Considering the vectors, a, b, c.
2
𝑎 = −1 ,
2

3
𝑏 = −3 ,
0

0
𝑐 = 18
0

(a) (3 points) Apply the Gram Schmidt process to find the orthonormal basis for the subspace
spanned by the vectors a, b, c.
(b) (2 points) Express 𝐴 = [𝑎 𝑏 𝑐] in the form of 𝑄𝑅 (𝐴 = 𝑄𝑅).
4. Considering the following measurements:
t
-2
-1
1
2
b
-4
-2
-2
0
(a) (4 points) Find the best straight-line fit (Least squares) to the measurements,
(b) (1 point) and draw its graph,
(c) (1 point) and write 𝐸
5. (4 points) Find the dimensions of the four fundamental subspaces associated with A, depending on
the parameters α and β.
0 𝛼 2
𝐴 = 2 −1 1
4 −2 𝛽
6. Construct a matrix with the required property or say why that is impossible.
1 2
1
(a) (3 points) Column space contains 2 , 5 and nullspace contains −1 .
3 6
1
(b) (2 points) With (1, 2, 3) in the row space and column space.

Full Name: _________________________
Mid Term Exam
Variant 2

Innopolis University
AG&LA II
Spring 2021

Duration: 120 Minutes

16.03.2021

You need to perform this exam alone and without the use of any equipment or book, apart from this
booklet and pens. Please do not consult any person or use any equipment, otherwise you will be
disqualified from this exam at the very first attempt.
Good Luck!
Grade Table (for teacher use only)
Question
Points
Score

1
3

2
7

3
5

4
6

5
4

6
5

Total
30

1. (3 points) True or False statement.
Statement

True

False

The null space of A is the solution set of the equation = 0.
The null space of an 𝑚 × 𝑛 matrix is in 𝑅
Col A is the set of all vectors that can be written as Ax for some x.
2. Considering the matrix, A and the vector b,
−1 1
𝐴 = −3 0 ,
−1 2

𝑏=

−1
1
−2

(a) (3 points) Find the projection of b onto the column space of A.
(b) (3 points) Split b into 𝑝 + 𝑞, with p in the column space and q perpendicular to that space.
(c) (1 point) Which of the four subspaces contains q.
3. Considering the vectors, a, b, c.
1
𝑎= 2 ,
0

𝑏=

8
1 ,
−6

0
𝑐= 0
1

(a) (3 points) Apply the Gram Schmidt process to find the orthonormal basis for the subspace
spanned by the vectors a, b, c.
(b) (2 points) Express 𝐴 = [𝑎 𝑏 𝑐] in the form of 𝑄𝑅 (𝐴 = 𝑄𝑅).
4. Considering the following measurements:
t
-1
0
1
2
b
-1
2
4
5
(a) (4 points) Find the best straight-line fit (Least squares) to the measurements,
(b) (1 point) and draw its graph,
(c) (1 point) and write 𝐸
5. (4 points) Find the dimensions of the four fundamental subspaces associated with A, depending on
the parameters α and β. (without row exchange)
1 −1 −2
𝛼 −1
𝐴= 1
−1 1
𝛽
6. Construct a matrix with the required property or say why that is impossible.
1 −2
14
(a) (3 points) Column space contains 2 , −5 and nullspace contains 5 .
3 −7
1
(b) (2 points) With (3, 4, 5) in the row space and column space.

Full Name: _________________________
Mid Term Exam
Variant 3

Innopolis University
AG&LA II
Spring 2021

Duration: 120 Minutes

16.03.2021

You need to perform this exam alone and without the use of any equipment or book, apart from this
booklet and pens. Please do not consult any person or use any equipment, otherwise you will be
disqualified from this exam at the very first attempt.
Good Luck!
Grade Table (for teacher use only)
Question
Points
Score

1
3

2
7

3
5

4
6

5
4

6
5

Total
30

1. (3 points) True or False statement.
Statement

True

False

If matrix A is invertible, then its rows are independent
The Column space of an 𝑚 × 𝑛 matrix is in 𝑅
dim(nullspace) = number of pivot columns
2. Considering the matrix, A and the vector b,
1 3
𝐴= 0 1 ,
1 3

2
𝑏= 1
1

(a) (3 points) Find the projection of b onto the column space of A.
(b) (3 points) Split b into 𝑝 + 𝑞, with p in the column space and q perpendicular to that space.
(c) (1 point) Which of the four subspaces contains q.
3. Considering the vectors, a, b, c.
1
𝑎= 1 ,
1

1
𝑏= 2 ,
0

2
𝑐= 0
1

(a) (3 points) Apply the Gram Schmidt process to find the orthonormal basis for the subspace
spanned by the vectors a, b, c.
(b) (2 points) Express 𝐴 = [𝑎 𝑏 𝑐] in the form of 𝑄𝑅 (𝐴 = 𝑄𝑅).
4. Considering the following measurements:
t
1
2
3
4
b
0
3
2
5
(a) (4 points) Find the best straight-line fit (Least squares) to the measurements,
(b) (1 point) and draw its graph,
(c) (1 point) and write 𝐸
5. (4 points) Find the dimensions of the four fundamental subspaces associated with A, depending on
the parameters α and β. (without row exchange)
2
5 1
𝐴 = −1 𝛼 0
−2 −5 𝛽
6. Construct a matrix with the required property or say why that is impossible.
−1
3
−6
(a) (3 points) Column space contains −3 , 4 and nullspace contains −2 .
2
−3
1
(b) (2 points) With (2, 1, 3) in the row space and column space.

## 2021: Retake

Files: [AGLA 2 Retake 2021.pdf](https://glebpopov.notion.site/d2780c4c6dcf4b3b9d114b55743dc059)


Linear Algebra. Retake exam.
1. If a 4x4 matrix has a det(A)=1/2, find det(2A), det(-A), det(A2), and det(A−1). (10 points)
1
2. Consider matrix: 𝐴 = [2
0
points)

2 0
6 4 ]. Find the symmetric factorization 𝐴 = LDLT, Find 𝐴-1 (10
4 11

3. Find a parabola that best fits to the following points:
(-1, 2), (1, -3), (0, 0), (2, - 5). (10 points)
4. Find extrema and saddle points for the following function:

f ( x, y ) = 3x3 + y 2 + 4 xy − x + 2 (10 points).
Formulate Sylvester’s criterion (2 points).
5. Prove that for any square matrix A (nxn) with eigenvalues 1 , 2 ,..., n  the multiplication:

( A − 1I )( A − 2 I )  ( A − n I ) produces the zero matrix? (12 points).
10

6. Find A

 4 3
 . (10 points).
1 2 

for the matrix A = 

7. Find eigenvector of the circulant matrix C for the eigenvalue  = c1 + c2 + c3 + c4 . (12 points)

 c1
c
C= 4
 c3

c2

c2
c1
c4
c3

c3
c2
c1
c4

c4 
c3 
c2 

c1 

8. Solve the differential equation, (10 points):

3
du  4 −2 
=
u
t
,
u
0
=
(
)
(
)
2
dt 1 1 
 
What happens to u ( t ) as t →  (2 points).

0
 −1
 2
1
0
0
1 
0






9. Apply the Gram-Schmidt process to: x1 =
, x =
, x =
, x =   and write the
 2 2  1  3 0 4  0 
 
 
 
 
0
0
0
 −1
result in form A = QR (12 points)
1 0 1 
10. Find the SVD and the pseudoinverse of the matrix: A = 
 (10 points).
0 1 0 

## 2020: Final

Files: [AGLA 2 Final 2020.pdf](https://glebpopov.notion.site/15b518097ec64506a498667e8c16596f)


Problem SVD3

Find the SDV of the matrix A = [; f]

Problem DE3

Problem EV1

Write down the system (and the matrix) for the fol-
lowing differential equation. Check it for stability.

yIV) + 3y + 3y +y =0

Find S, A such that S—'AS = A, where A is a diago-
nal matrix with eigenvalues on the main diagonal and

1 3 0
A=10 2 0
00 0 Problem PD3

positive semidefinite.

Problem FT1

Prove that any real square matrix can be factored into
A = QS where Q is orthogonal and gis symmetric

The signal corresponding to a single impulse at time
zero is (roughly) described by

1
0
0
0

Find the Fourier transform of this signal.

Problem ARPD

and any vectors x,y € R" is true:

(x,y)=(x,4y)

Prove that for any symmetric matrix 4 (nxn)

## 2020: Midterm

Files: [AGLA 2 Midterm 2020.pdf](https://glebpopov.notion.site/6d3cc4c19bb84fc9865768bad47d8a52)


Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #1
1. (5 pts) Solve the system of equations with the use of Gaussian elimination process (without
pivoting). Describe your solution in terms of matrix operations (after the final matrix operation
you have to obtain augmented matrix in the form [I|x] ):


x1 + 2x2 + 4x3 = 31
5x1 + x2 + 2x3 = 29


3x1 − x2 + x3 = 10

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #1
2. (5 pts) Solve the given system of equations with the use of Cholesky decomposition (in other
words, find decomposition A = LLT and then solve equations Ly = b, LT x = y):


81x1 − 45x2 + 45x3 = 531
−45x1 + 50x2 − 15x3 = −460


45x1 − 15x2 + 38x3 = 193

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #1
3. (5 pts) Forward elimination changes Ax = b to a row echelon form Rx = d. Compose the vector
d and
solution
 the
 matrix
 R
 if the complete


 is the following:
4
−3
−8
−1
2
−3
−6
7
 
 
 
 







y = 0 + c1  1  + c2  0  + c3 
0
0
0
1
0
0
0
0
1

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #1
4. (5 pts)
 Solve
 thegiven
 system Ax = b with the use of least-square approximation:
1 4
5
A = 1 5; b = 6.
0 0
0

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #1
5. (5 pts) Represent a matrix as a QR decomposition according to Gramm-Schmidt orthogonalization: 

1 1
1
A = 1 −1 1 .
1 1 −1

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #1
6. (extra 5 pts) Prove the following statement: if a matrix A is symmetric then the dot product
of two vectors x and y satisfies the property x · Ay = y · Ax.

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #2
1. (5 pts) Solve the system of equations with the use of Gaussian elimination process (without
pivoting). Describe your solution in terms of matrix operations (after the final matrix operation
you have to obtain augmented matrix in the form [I|x] ):


−x1 + x2 − 4x3 = −11
3x1 + 2x2 + x3 = 10


x1 − x2 + 2x3 = 5

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #2
2. (5 pts) Solve the given system of equations with the use of Cholesky decomposition (in other
words, find decomposition A = LLT and then solve equations Ly = b, LT x = y):


36x1 + 30x2 + 18x3 = 288
30x1 + 41x2 + 23x3 = 296


18x1 + 23x2 + 14x3 = 173

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #2
3. (5 pts) Forward elimination changes Ax = b to a row echelon form Rx = d. Compose the vector
d and
solution
 the
 matrix
 R
 if the complete


 is the following:
1
−3
−4
6
3
−2
2
−3
 
 
 
 







y = 0 + c1  1  + c2  0  + c3 
0
0
0
1
0
0
0
0
1

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #2
4. (5 pts)
 Solve
 thegiven
 system Ax = b with the use of least-square approximation:
1 3
4
A = 1 4; b = 5.
0 0
0

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #2
5. (5 pts) Represent a matrix as a QR decomposition according to Gramm-Schmidt orthogonalization: 

1 −1 0
A = 0 1 2.
1 0 1

Full name:
Linear Algebra–II
Midterm

e-mail:
Date: March 10th , 2020

Variant #2
6. (extra 5 pts) Prove the following statement: if a matrix A is symmetric then the dot product
of two vectors x and y satisfies the property x · Ay = y · Ax.

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)

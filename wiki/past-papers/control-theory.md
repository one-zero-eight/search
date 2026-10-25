---
type: page
title: "Past exam papers: Control Theory"
description: "Past exams and tests of Control Theory at Innopolis University (5 papers, 2019–2021), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "control-theory"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "Control Theory"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: Control Theory

Exams and tests of **Control Theory** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2021: Final

Files: [Control Theory Final 2021.pdf](https://glebpopov.notion.site/14ee746cceef80da83d3fd8c25eb6414)


Procedure
Solve all tasks the best you can. Incomplete solution will also be graded.
For remote students only:
In 60 minutes after the beginning of the exam you should submit your
solutions to email of your professor (s.savin@innopolis.ru) and your TA
(v.skvortsova@innopolis.university, s.sellami@innopolis.university,
s.nedelchev@innopolis.university).
Good luck and do your best!

1

Task 1

You have a linear system:

ẋ =


 
1
1
x+
u
−2
0

5
0

(1)

∗
∗
We want to find an affine control law
 u = −K(x −x ) + u that would drive


−7
1
the system towards the points 1) x∗ =
, 2) x∗ =
, where K = 10 10 .
0
1
Is there such u∗ that the resulting control law would achieve this goal?

1. Yes/No
2. Yes/No

2

Task 2

You have a linear dynamical system.
ẋ = 2x + u
Given cost function:

(2)

Z
J=

g(x, u)dt

(3)

where g(x, u) = 5x2 + u2 , and knowing that optimal cost-to-go is J ∗ = sx2 , find
the value of s and the optimal linear feedback control u = −kx that stabilizes
the origin by solving Algebraic Riccati equation.
• s =?
• k =?

1

3

Task 3

Given linear dynamical system:

"
\#
" #

−1
1
1

ẋ =
x+
u
0 −1
0
h
i


y = 2 0.5 x

(4)



and control law u = − 1 1 x̃, find if the following observer will make the
state dynamics and observer error dynamics stable (if x will approach origin,
and x̃ will approach x):


 


˙x̃ = −1 1 x̃ + 1 u + L 2 0.5 (x − x̃)
(5)
0 −1
0
 
2
For L =
. Prove that this observer and controller produce a stable linear
0
system, and if not - propose a different choice of L that does.

4

Lookup info

4.1

Determinant
|A| =

4.2

a
c

Eigenvalues
|A − λI| =

4.3

b
= ad − bc
d

a−λ
c

b
=0
d−λ

Quadratic eq.
√

2

b −4ac
For scalar quadratic eq. ax2 + bx + c = 0, the roots are x = −b± 2a
.

4.4

Hamilton-Jacobi-Bellman eq.

Hamilton-Jacobi-Bellman eq. for system ẋ = f (x, u) and cost J =
has the form:


∂J ∗
f (x, u)
u∗ = arg min g(x, u) +
∂x
u
It would achieve extremum if:

( 
∂
∂J ∗
∂u g(x, u) + ∂x f (x, u) = 0
∗

g(x, u) + ∂J
∂x f (x, u) = 0

2

R∞
0

g(x, u)dt
(6)

(7)

## 2021: Midterm

Files: [Control Theory Midterm 2021.pdf](https://glebpopov.notion.site/14ee746cceef808ca505f39dda5e16a9)


Control Theory, Midterm, 2021
1

Problem 1

Consider the following linear systems
SYSTEM I:
 
  
ẋ1
−2 −3 x1
=
ẋ2
1 −1 x2
SYSTEM II:
10ẍ = −1.5ẋ + 2x
SYSTEM III:
−10ẍ = −2.5x
SYSTEM IV:

 



" # "
\#" # "
\# u1 



ẋ1
−5 0 x1
1 1 2 1 
u2 




=
+

u 


ẋ
2
2
x
3
3
−7
0
2
2

 3



u4
 



u1
0 10 " #








u2 
10 0  x1


  = −



u 

20 4  x


 3

 2


 u
0 −1
4
SYSTEM V:
ẋ1 = −5x1 + x2 ,

ẋ2 = −3x1

Which of the systems are asymptotically stable?

1

Figure 1: poles of the systems

2

Problem 2

Consider LTI systems with poles (eigenvalues) as shown on the
graphs (see Fig. 1)
Which are stable in the sense of Lyapunov?

3

Problem 3

Consider LTI system:
  
   
ẋ1
−5 2
x1
0
=
+
u
ẋ2
2 −2 x2
1
and the following control law:
2

 

x1
− xdesired + udesired
x2
 
4
Can the system stabilize at point xdesired =
, what control
10
udesired should be chosen?:


u = − 0.15 0.4

4

Problem 4

You have discrete linear systems
SYSTEM I:

"
\#
"
\#

−1 −1/4
1/4 −1/4


xi −
ui

xi+1 = −1/2
1
−1/4
0
\#
"

−0.7
−0.7


(xi − xdesired )

ui = − −1
2
SYSTEM II:

"
\#
" #

1
1/3
2

xi+1 =
xi −
ui
−1/6
1/5
0
h
i


ui = − −0.2 −0.2 (xi − xdesired )
Which of them are stable?

5

Problem 5

For the systems
  in the Problem 4, which can stabilize point
0.5
xdesired =
(make trajectory x = xdesired (t) into an asymp0.5
totically stable solution, after substituting control law ui )

3

6

Your answers

Please write your answers in the table below:
Table 1: Your answers
Question
Your Name, Surname

Answer

Your Group
Problem 1 answer
Problem 2 answer
Problem 3 answer
Problem 4 answer
Problem 5 answer

7

Lookup info

Determinant:
|A| =

a b
= ad − bc
c d

Eigenvalues:
|A − λI| =

a−λ
b
=0
c
d−λ

4

## 2020: Final

Files: [Control Theory Final 2020.pdf](https://glebpopov.notion.site/14ee746cceef80ba95f5cd62f94d52a2)


1

Procedure

Solve the problem according to your variant. Record your screen while you
work. In 60 minutes after the beginning of the exam you should submit your
code (and if you wish, screenshot of the output it produced on your system) to
email indicated in the variant. After that, upload same results to moodle. Any
further modification of the code is not allowed and will result in exam being
failed.
If after 70 minutes at least one of the following isn’t true, the exam is considered failed:
• email with your results is sent;
• email with your results is received;
• your results are uploaded to moodle.
Store your screen recording files for at least 3 months after the exam. Sorry
for the inconvenience!
Good luck and do your best!

2

Terms
• To prove by a numeric demonstration in this exam means to show something by computing it. For example, to prove that matrix X had negative
real parts of eigenvalues, you can print the result of eig(X) and this is
considered a proof in this context.

3

Variant 1

You have a linear system:

1
ẋ = 2
2



1
0
7
10 −7 x + −1
0
7
0


1
2 u
0

(1)

Tasks:
• Find stabilizing control law and prove that the closed loop system with
that control law is stable.
 
1
• Find control that stabilizes the point xd = 1, or prove that this point
1
is impossible to stabilize and find a different non-zero point that can be
stabilized. Plot the simulation results that demonstrate stability of the
point you stabilized.

1

• Make the system track the next trajectory, demonstrate its performance:


sin(t)
xd (t) = cos(t) − 7 sin(t2 )
(2)
t−10
|t−10|

• Submit results to s.savin@innopolis.ru and sh.mamedov@innopolis.
ru

4

Variant 2

Task #1: You have a linear system:





2 1 2 1
0 1



3 3 3 3
1 0








ẋ
=
x
+



u


5 5 0 5
0 1

1 0

"5 5 1 5 #




1 0 0 0


x
y =
0 0 −2 1


6 8 4 7
u=−
x
7 4 3 5

(3)

(4)

Design an observer - an algorithm, which will produce estimates of the state
that would converge to the true state. Simulate the system forward and plot
the evolution of the state of the observer and the state of the system. Show
that the observation error tends to zero.
Task #2: You have a linear system:





0
0 1 0 0








0 0 0 0
1
ẋ = 

x + 
0
2 2 0 2



1 0 1 0
0



y = Cx


1
0

u
0

(5)

0

You can choose to measure one state: x1 , x2 , x3 or x4 . The measurement is
precise, no noise is present: y = xi .
• Is it enough to observe the whole state (to design a stable observer)? Give
a prove (by a numeric demonstration).
• If measuring only one state is enough, show which of states can be chosen
to be measured, so the system remains observable (in the sense given
above). If one state isn’t enough, show which pairs of states needs to be
measured for the system to be observable.
Submit results to s.savin@innopolis.ru and m.ivanov@innopolis.ru
2

5

Variant 3

Task #1: Consider an actuated spring-damper system is described by equations:
mẍ + µẋ + kx = 10u + f

(6)

where m is mass, µ is a viscous friction coefficient, k is a stiffness coefficient
and f is a constant external force, u is the control input and x is the position
of the spring-damper. Parameters m, µ, k and f are not known to the control
system.
Write an algorithm that estimates those parameters (either via adaptive
control approach or by an offline data collection and estimating the parameters
from data) of this system, with accuracy up to 0.15.
True values of parameters are: m = 10, µ = 1, k = 20, f = 30.
Task #2: Consider a DC motor, with the following dynamics:
(
J ẇ = Cτ I
LI˙ + Ce w + RI = u

(7)

where J is the inertia of the rotor, Cτ is a torque constant, L is the inductance
coefficient, Ce is the back-emf constant, R is the coil resistance, u is the control
input, w and I are the states of the system: angular velocity and current.
Parameters Cτ , L, Ce and R are not known to the control system. Parameter
J = 1 is known to the control system.
Write an algorithm that estimates those parameters (either via adaptive
control approach or by an offline data collection and estimating the parameters
from data) of this system, with accuracy up to 0.15.
True values of parameters are: Cτ = 50, L = 0.05, Ce = 50 and R = 1.5.
Submit results to s.savin@innopolis.ru and r.abraham@innopolis.ru

3

## 2020: Midterm

Files: [Control Theory Midterm 2020.pdf](https://glebpopov.notion.site/14ee746cceef8046a2bed58d313f052d)


Linear Control Midterm , 2020
1

• d ) SYSTEM I is stable, SYSTEM II is unstable, SYSTEM

III is stable in the sense of Lyapunov , SYSTEM IV is unstable

Problem 1

• e) SYSTEM I and II are unstable, SYSTEM III and IV are

You have a linear system
SYSTEM I:

stable

Xi

- 10 - 1

Xi

-5

Xo

2

X2

SYSTEM II:
2x =

• f ) SYSTEM I is stable, SYSTEM II is unstable, for SYSTEM
III stability cannot be identified , SYSTEM IV is unstable.

• g) SYSTEM I is unstable, SYSTEM II is unstable, for SYS-

—ix + x

TEM III stability cannot be identified , SYSTEM IV is sta-

SYSTEM III:
Xi

ble.

-10 0 0 0

Xi

-1

x2

0
0
0

X2

xz
x4

0
0

0 0
2 -2
0 10

xz
x4

0
0
0
0
+ 10 2
0 -10

Ui
U2

xi
Ui

u2

0 0 1 0
0 0 0 1

x2

Problem 2

Consider LTI systems with poles (eigenvalues) as shown on the
graphs (see Fig. 1)
Which are stable? Options:

• a) SYSTEM I and II are stable, SYSTEM III is unstable,

xz

SYSTEM IV is unstable in the sense of Lyapunov

x4

SYSTEM IV:
x\ = - Ax\

2

— 2xo xo = -2

X2

Which systems are stable? Options:

• a) SYSTEM I and IV are stable, SYSTEM II and SYSTEM
III are unstable

• b) SYSTEM I is stable, others are unstable

• b) SYSTEM I, II and IV are stable, SYSTEM III is unstable
• c) SYSTEM I, III and IV are unstable, SYSTEM II is stable
• d ) SYSTEM I is stable in the sense of Lyapunov, SYSTEM
II is stable, SYSTEM III and IV are unstable

• f ) SYSTEM I, II and III are unstable, SYSTEM IV is stable
• e) SYSTEM I and II are stable, SYSTEM III is unstable,
SYSTEM IV is stable in the sense of Lyapunov

• c) SYSTEM I, III and IV are stable, SYSTEM II is unstable
1

2

SYSTEM I

CONTROL LAW III:

SYSTEM (I

Imaginary

Imaginary

i

u = [ 0 10] X i

*

Real

-i

X2

Real

t

CONTROL LAW IV:

-I

u = [-10 2] X i

X2

SYSTEM III

SYSTEM IV

Imaginary
l

• a) CONTROL LAW I, II and III stabilize the system, CON-

1

Real
1

Which control laws stabilize the system ? Options:

Imaginary

Real

TROL LAW IV does not

1

•

-1

*

• b) CONTROL LAW II and III stabilize the system , CONTROL LAW I and IV does not

• c) None of the control laws stabilize the system
• d ) all control laws stabilize the system
• f ) the system is already stable, no control needed

Figure 1: poles of the systems

3

Problem 3

• e) CONTROL LAW I, II and III do not stabilize the system,
CONTROL LAW IV stabilizes the system

Consider LTI system:

• g) CONTROL LAW II and III do not stabilize the system,

2 3
-10
Xi
Xi
x2\
[2 -6 j [ x2 + 2 u
and the following control laws:
CONTROL LAW I:
Xi

“ = [1 !] x2
CONTROL LAW II:

u = [10 0]
3

x\
x2

CONTROL LAW I and IV stabilizes the system in the sense
of Lyapunov

4

Problem 4

You have a linear system:
x = 10x - 2u

4

and cost function:

Table 1: Your answers

J=

J

( rrlOrr + u0.1u )dt

Question
Your Name
Your Surname
Problem 1 correct option is
Problem 2 correct option is
Problem 3 correct option is
Problem 4 correct option is

Optimal cost is J * = f ( xSx ) dt . Solve Algebraic Riccati equation
and find S.
0
• a ) S = .V05|
'

• b) S = 10.5
• c) S = 3\/5
• d ) S = 3.2

—
~

\#

e) 5 =

6

-VZ -2

[0

'

•

Lookup info

Determinant:

3
4 .

a b

\ A\ = c d = ad — be

• f ) S = 30 ±|\/5

•

Answer

Eigenvalues:

g) 3 = -VE

\A - X I\ =

,

h ) S = i + j\/5

a

cX

•0 S =|±|\/5

• j) 5 =|± iv/5
• k) 5 = f %/5 ± ifv/5
5

Your answers

Please write your answers in the table below:

5

6

b
0
d-A =

## 2019: Midterm

Files: [the row](https://glebpopov.notion.site/14ee746cceef8044bdb7ecf7012a7b4f)

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)

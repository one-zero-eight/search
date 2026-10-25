---
type: page
title: "Past exam papers: Physics 1"
description: "Past exams and tests of Physics 1 at Innopolis University (8 papers, 2020–2026), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "physics-1"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "Physics 1"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: Physics 1

Exams and tests of **Physics 1** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2026: Quizzes

Files: [Physics 1 Quiz 1 2026.pdf](https://glebpopov.notion.site/3fee746cceef809f94c0fdfbeb678b06)


Quiz 1 – Kinematics
[2026] Physics 1. Mechanics

Variant 1
Problem 1 (25 pts)
Plot the velocity of the object, whose
acceleration is shown in Figure on the
right. The velocity is zero at the moment
t = 0 s. Find the mean velocity averaged
over the time interval [6, 14 s].

a (m/s2 )
2

t (s)
2

4

6

8

10

12

14

−4

Figure for Problem 1

1. Use acceleration to find the velocity changes.
Use vend = vstart + a ∆t on each constant-acceleration interval. The velocity graph is
horizontal where a = 0 and has slope a elsewhere.
2. Write the area formula before using numbers.
For endpoint velocities vi , vi+1 and durations ∆ti , add the signed trapezoid areas,
then divide by the total time:
∑
(vi + vi+1 ) ∆ti
v̄ = i ∑
.
2 i ∆ti
3. Calculate the velocities and draw the graph.
Starting from zero, the two positive pulses each add 2(2) = 4 m/s; the last pulse adds
−4(2) = −8 m/s.
8

v (m/s)

4

∆x = 44 m
2

4

6

8

10

12

14
t (s)

4. Add the areas over 6–14 s and divide by the time.
The velocity at 6 s is also 4 m/s. The four areas give
∆x = (8 + 12 + 16 + 8) m = 44 m,

v̄ =

44 m
= 5.50 m/s.
8s

Quiz — Variant 1

Quiz 1 – Kinematics

Problem 2 (25 pts)
The tram starts moving with a constant acceleration of 0.4 m/s2 . How long can a passenger stay after the beginning of the tram movement, then catch up to him, running
at a constant speed of 10 m/s?
1. Choose the model and sketch the limiting meeting.
Assume a shared starting position, a tram starting from rest, and a passenger who
waits there for time tw before instantly reaching running speed vP . Interpret the question as the longest possible wait.
Tram
Passenger

x
at2w

4

Meeting
2

0
0

1

2

3

t
tw

At the limit, equal positions and speeds make the two curves tangent.
2. Write the position equations.
With +x along the motion and t ≥ tw ,
at2
,
2
Before tw , the passenger stays at x = 0.
xT =

xP = vP (t − tw ).

3. Require a physically possible meeting.
Equating positions gives at2 − 2vP t + 2vP tw = 0. For a, vP , tw > 0, a meeting after the
wait exists when the discriminant is nonnegative: vP2 − 2avP tw ≥ 0. Thus
vP
vP
tw,max = ,
0 ≤ tw ≤ .
2a
2a
4. Calculate and interpret the answer.
10 m/s
= 12.5 s.
2(0.4 m/s2 )
At the limit t∗ = vaP = 25.0 s. For a smaller positive wait there are two meetings if both
continue; zero delay means initial coincidence.
Alternative: equal positions and speeds. The gap decreases while the passenger is
faster and increases once the tram is faster. At the limiting meeting, the smallest gap
is zero, so
{ 2
at∗
= vP (t∗ − tw ),
2
at∗ = vP .
tw,max =

v2

v2

vP
Substitute t∗ = vaP into the position equation: 2aP = aP − vP tw . Thus tw,max = 2a
= 12.5 s,
without derivatives or a discriminant.
2
Alternative: minimize the separation d(t) = at2 − vP (t − tw ). Its minimum at t = vaP is
v2

vP tw − 2aP ; requiring this to be nonpositive gives the same bound.

2

Quiz — Variant 1

Quiz 1 – Kinematics

Problem 3 (25 pts)
A drop of rain falls at an angle of α1 = 30◦
to the vertical axis when the wind speed
is u1 = 10 m/s. What is the angle α2 at
which the drop falls after the wind has
been increased to u2 = 20 m/s? Assume
that the velocity of the raindrops with
respect to the air is constant.

Wind

α Vertical

Schematic
Figure for Problem 3

1. Draw the velocities and state the working assumption.
Assume vertical downward motion relative to the air and horizontal wind in the
same direction in both states. Measure the observed angle in the ground frame. Take
+y downward; vy is the unchanged vertical velocity component.

u1
vy

u2
vy

α1
v1

α2
v2

State 1

State 2

The horizontal leg changes; the vertical leg does not.
2. Relate each angle to the components.
Velocity addition gives horizontal component ui and vertical component vy . Because the angle is measured from the vertical,
tan α1 =

u1
,
vy

tan α2 =

u2
.
vy

3. Eliminate the unknown vertical speed.
Using vy = tanu1α1 gives

(

)
u2
α2 = arctan
tan α1 .
u1

The downward-drift solution is the acute angle.
4. Evaluate the angle.
)
2
≈ 49.1◦ .
α2 = arctan(2 tan 30 ) = arctan √
3
The same relation follows from two right velocity triangles with a common vertical
leg. Without the vertical air-relative-motion assumption, the source wording does not
fix a unique numerical angle.
(

◦

3

Quiz — Variant 1

Quiz 1 – Kinematics

Problem 4 (25 pts)
A particle moves in uniform circular motion over a horizontal xy plane. It takes
20 s to make a full circle. At one instant, it moves through the point with coordinates
[4 m, 4 m] with the acceleration of (0î + 8ĵ) m/s2 . Find the x and y coordinates of the
center of the circular path.
1. Use the direction of centripetal acceleration.

C
y

R
a
x (4, 4) m

Schematic; axes indicate directions

Centripetal acceleration points toward the center. Here it is vertically upward, so xC =
x and yC = y + R.
2. Find the radius from centripetal acceleration.
Let ac = |a| be its magnitude and v the constant speed. One revolution covers 2πR
in time T , so
v2
2πR
4π 2 R
ac = ,
v=
=⇒ ac =
.
R
T
T2
3. Write the symbolic answer.
R=

ac T 2
,
4π 2

xC = x,

yC = y +

ac T 2
.
4π 2

4. Calculate the radius and coordinates.
8(20)2
800
m = 2 m.
2
4π
π
(
)
800
xC = 4 m,
yC = 4 + 2 m.
π
R=

Answer: (xC , yC ) ≈ (4, 85.1) m. The radius is added to the point’s height; it is not the
center’s height itself.
T2
, a = ω 2 (rC − r) gives rC = r + 4π
Vector alternative: with ω = 2π
2 a, the same result.
T

4

Quiz — Variant 2

Quiz 1 – Kinematics

Variant 2
Problem 1 (25 pts)
It is one-dimensional motion along the
x-axis. The initial position of the object
is x(0) = 15 m. Figure on the right shows
the change in the acceleration with time.
What is the x-coordinate of the object at
time t = 6 s, if the initial velocity equals
to −10 m/s?

a (m/s2 )
8
6
4
2

t (s)
2

4

6

8

10

Figure for Problem 1

Version note: An earlier printout asks for t = 8 s; the corrected statement above asks
for t = 6 s.
1. Split the motion into three equal time intervals.
Use 0–2, 2–4 and 4–6 s, each of duration ∆t. The accelerations are a1 = 0, a2 and
a3 = 0; the index labels the interval.
2. Write the displacement in each interval.
For constant acceleration, ∆x = vstart ∆t + a(∆t)
and vend = vstart + a∆t. Therefore
2
2

∆x1 = v0 ∆t,

∆x2 = v0 ∆t +

a2 (∆t)2
,
2

∆x3 = (v0 + a2 ∆t)∆t.

3. Add the displacements to the initial position.
x = x0 + ∆x1 + ∆x2 + ∆x3 = x0 + 3v0 ∆t +

3a2 (∆t)2
.
2

4. Calculate the coordinate and check the graph.
Use x0 = 15, v0 = −10, ∆t = 2 and a2 = 4 in SI units.
v (m/s)
2

4

6 t (s)

−2
−6
−10

∆x = −36 m

The signed areas give ∆x0–6 = −20 − 12 − 4 = −36 m. For the earlier printout, extend to
8 s: on 6–8 s, a = 0 and v = −2 m/s. Adding the initial coordinate gives
x(6) = x0 + ∆x0–6 = 15 − 36 = −21 m,
x(8) = x(6) + v(6)(8 − 6) = −21 − 2(2) = −25 m.
These are coordinates; the displacements are −36 m and ∆x0–8 = x(8) − x0 = −40 m,
respectively.
5

Quiz — Variant 2

Quiz 1 – Kinematics

Problem 2 (25 pts)
The tram starts moving with the constant acceleration a. The passenger waits for
10 s and then catches up the tram by running after with the constant velocity of 12 m/s.
What is the maximum acceleration of the tram amax to make this happen?
1. Choose the model and sketch the boundary.
Assume a shared starting position and a tram initially at rest. The passenger waits
there for time tw and then runs at constant speed vP . A limiting meeting counts as
catching up.
Tram
Passenger

x
at2w

4

Meeting
2

0
0

1

2

3

t
tw

The limiting line touches the tram’s parabola.
2. Write the meeting equation.
For t ≥ tw ,
xT =

at2
,
2

xP = vP (t − tw ),

at2 − 2vP t + 2vP tw = 0.

3. Find the largest allowed acceleration.
For positive a, vP , tw , a meeting after the wait exists when the discriminant is nonnegative: vP2 − 2avP tw ≥ 0. Thus
amax =

vP
,
2tw

0<a≤

vP
.
2tw

At the boundary the roots merge and t∗ = 2tw .
4. Calculate the maximum.
amax =

12 m/s
= 0.600 m/s2 .
2(10 s)

The meeting is at 20 s. Below the thres

(the rest is in the file)

## 2024: Final

Files: [the row](https://glebpopov.notion.site/15fe746cceef803bab32c34ad67adce2)

## 2024: Quizzes

Files: [the row](https://glebpopov.notion.site/14fe746cceef80e1ab57c4cba8cee0bd)

## 2023: Final

Files: [the row](https://glebpopov.notion.site/15ee746cceef804d89f0dd64082c697f)

## 2023: Quizzes

Files: [the row](https://glebpopov.notion.site/14fe746cceef805e8032da9dd6931711)

## 2022: Quizzes

Files: [the row](https://glebpopov.notion.site/14fe746cceef803f9e61daa9e3adacf3)

## 2020: Final

Files: [the row](https://glebpopov.notion.site/14ee746cceef809fb1a5eb5e118f84ea)

## 2020: Quizzes

Files: [Physics 1 Quiz 2 2020.pdf, Physics 1 Quiz 4 2020.pdf, Physics 1 Quiz 5 2020.pdf, Physics 1 Quiz 1 2020.pdf, Physics 1 Quiz 3 2020.pdf](https://glebpopov.notion.site/14fe746cceef8055ac47d263700b9304)

### Physics 1 Quiz 2 2020.pdf
[2020] Physics I. Mechanics

Quiz 2 – Forces and Motion
Problem 1 (25 pts) – Net Force
Three forces are applied the particle as shown in Fig. 1, left. The known magnitudes are FA =
220 N and FC = 170 N. Note that FB is acting vertically down, while the direction of FC
(angle ) is not given. The particle is moving with constant velocity. What is the magnitude
of FB?
Problem 2 (25 pts) – Forces and Velocities
A person is pulling on a rope attached to a locomotive of mass m = 100 tons (Fig. 1, right).
The person is pulling with a constant force F that is 2 times greater than their body weight,
at an upward angle θ = 30° from the horizontal. The person’s mass is 75 kg, and they moved
the train by 1 m. Neglecting any friction on wheels and assuming the train was initially
stationary, find the speed of the train v at the end of the pull. Assume g = 9.8 m/s2.
y
F
A

FC
=?

137o

F

x

30o

FB
Figure 1: Diagrams for Problem 1 (left) and Problem 2 (right)
Problem 3 (25 points) – Rope Tension
In the two blocks of masses m1 and m2 (m1 < m2) and pulley system below, assume that the
pulley is frictionless and both the cord and pulley are massless. Find an expression of the
acceleration a when the blocks are released from rest.
Problem 4 (25 pts) – Rotation with Friction
An object of mass m = 0.25 kg is rotating at constant angular velocity on a string along a
circular path of radius R = 0.7 m in the vertical plane, subject to gravitational forces (Fig. 2,
right). The maximum force that the string can sustain without breaking is 30 N. Assuming g
= 9.8 m/s2, answer the following:
4.1. What is the maximum speed v at which the breaking will occur? (20 pts)
4.2. Will the breaking occur at the lowest point or at the highest point of the circle? (5 pts)

R
v

m1

m2

g

mg

Figure 2: Diagrams for Problem 3 (left) and Problem 4 (right)

[2020] Physics I. Mechanics

Quiz 2 – Forces and Motion
Problem 1 (25 pts) – Net Force
A 3-kg object is subjected to three forces that give it an acceleration 𝑎⃗ = −8î + 6ĵ m/s2.
If two of the three forces are 𝐹⃗1 = 30î + 16ĵ N and 𝐹⃗2 = −12î + 8ĵ N, find the third force:
1.1. In unit-vector notation (15 pts)
1.2. As a magnitude and angle relative to the positive direction of the x axis (10 pts)
Problem 2 (25 pts) – Velocities
A car moving at speed v = 60 km/h crashes into a streetlight. The driver’s upper body of mass
m = 40 kg hits the airbag and moves forward by 45 cm before coming to a full stop. What is
the magnitude of force F acting on the body, assuming it is moving with constant
deceleration?
Problem 3 (25 points) – Rope Tensions
Assume you have a toy car of mass m suspended on a string as shown in Fig. 1, left. This
string is tied to another 2 strings at point B, with the opposite ends of these strings attached to
the ceiling at angles α1 and α2. Assuming α1 = 60°, α2 = 20°, m = 5 kg and g = 9.8 m/s2, find
tension forces T1 and T2 on each string.
Problem 4 (25 pts) – Rotation with Friction
A particle is located on the surface of a conically-shaped part at the radius r = 0.2 m, as
shown in Fig. 1, right. The part is rotating around the vertical axis at constant angular
velocity ω. What is the minimum angular velocity ωmin about the vertical axis y for which
the particle will remain on the surface without slipping? Assume the coefficient of static
friction between the object and the surface to be  = 0.3 and g = 9.8 m/s2.

a2
T2

a1

y
r

T1

w

B

m

mg
30o

mg

Figure 1: Diagrams for Problem 3 (left) and Problem 4 (right)

[2020] Physics I. Mechanics

Quiz 2 – Forces and Motion
Problem 1 (25 pts) – Net Force
Two forces are acting on the 5 kg object, with only one of them shown in Fig. 1. Knowing
that F1 = 20 N, θ = 30° and that the object is moving at a constant acceleration of a = 12 m/s2,
find the second force:
1.1. As a magnitude and angle relative to the positive direction of the x axis (15 pts)
1.2. In unit-vector notation (10 pts)

y

F1

a

x

q

Figure 1: Diagram for Problem 1
Problem 2 (25 pts) – Velocities
A 500 kg rocket sled can be accelerated at a constant rate from rest to 1600 km/h in 1.8 s.
What is the magnitude of the required net force?
Problem 3 (25 points) – Rope Tensions
In a hospital, a patient’s injured leg is suspended by a traction setup as shown in Fig. 2, left.
Assuming the mass of the load to be m = 8 kg and g = 9.8 m/s2, what is the traction force F
exerted on the leg? Ignore masses of pulleys and cables and friction between them.
Problem 4 (25 pts) – Rotation with Friction
A particle is located on the surface of a conically-shaped part at the radius r = 0.2 m, as
shown in Fig. 1, right. The part is rotating around the vertical axis at constant angular
velocity ω. What is the maximum angular velocity ωmin about the vertical axis y for which
the particle will remain on the surface without slipping? Assume the coefficient of static
friction between the object and the surface to be  = 0.3 and x`g = 9.8 m/s2.

y
70

Leg

F
Traction force
mg

o

r

w

m
30o

mg

Figure 2: Diagrams for Problem 3 (left) and Problem 4 (right)

### Physics 1 Quiz 4 2020.pdf
[2020] Physics I. Mechanics

Quiz 4 – Center of Mass. Momentum. Impulse

Unless specified otherwise, assume g = 9.81 m/s2. All problems are worth 25 points.

Section 1 - Center of Mass
Problem 1
A rod whose length is 10 meters has the density given by 𝜌(𝑥) = (𝑥 + 1) kg/m3 at location 𝑥
on the rod. Find the center of mass of the rod. Recall that
𝑏

𝑥COM =

∫𝑎 𝑥 ∙ 𝜌(𝑥)𝑑𝑥
𝑏

∫𝑎 𝜌(𝑥) 𝑑𝑥

Problem 2
A heavy metal ball of mass m2 = 5 kg and radius 8 cm is attached to a uniform rod of length
l= 80 cm and mass m1 = 1.5 kg, as shown below. The system is balanced on top of a pointy
pyramid. Find the distance x.

Problem 3
An object of unknown mass m2 is suspended on a massless bar at distance l/4 from its center
(see the figure below). The bar itself is balanced on the rope attached to it at the middle. The
other two objects have masses m1 = 3.5 kg and m3 = 5 kg and are suspended at the opposite
ends of the bar. Find mass m2.

[2020] Physics I. Mechanics

Section 2 – Motion of CoM
Problem 4
Two projectiles are flying such projectile A is always above projectile B. Their masses are
mA= 10 kg and mB = 6 kg, respectively, while the initial velocities are 𝑣𝐴 = 20 m/s and 𝑣
⃗⃗⃗⃗𝐵 =
10𝑖̂ m/s, respectively. What is the maximum height ymax that the center of mass of this twoprojectile system will reach? Assume zero air drag.

Problem 5
A person of mass mp = 80 kg is sitting on a seat of a stationary boat in front of his dog of
mass md. The boat has a symmetric shape and the mass of mb = 30 kg, and the seats are
located symmetrically with respect to the boat’s center of mass at distance of d = 3 m from
each other. The person and the dog switch seats, and the boat moves by 0.4 m with respect to
its initial position. Knowing that the dog is lighter than the person, find the dog’s mass md.
Assume zero drag.

Problem 6
A cat of mass mc = 3 kg starts walking from one end of an initially stationary raft of mass M=
12 kg to the other, walking a total of d = 2.4 m along the raft, as shown below. What will be
the cat’s total displacement x? Assume zero drag and friction.

[2020] Physics I. Mechanics

Section 3 – Collision and Impulse
Problem 7
In a famous circus trick, one athlete equipped with a heavy hammer
of mass m1 strikes an anvil of mass m2 that is placed on the chest of
another athlete, as shown on the right. The anvil is 50 times heavier
than the hammer. Assuming that the collision is completely elastic,
find the final velocities of hammer v1f and anvil v2f, given that the
hammer was initially moving with the speed v1i and the anvil was
stationary.

Problem 8
A cable of a stationary elevator snaps which sends the cabin with a passenger of mass m = 90
kg falling down from the height of x = 36 m. The collision is over in 5 milliseconds. What
are the impulse and average force on the passenger during the collision?

Problem 9
An ice hockey player hits a puck of mass m = 250 g with the average force of F = 400 N
during the time interval of 40 milliseconds. Assuming that before the hit the puck was
coming toward the player with the speed of v1 = 10 m/s, what will be the puck’s speed v2
after the hit?

[2020] Physics I. Mechanics

Section 4 – Conservation of Linear Momentum

Problem 10
A mini-wrecking ball of mass m1 = 0.5 kg is released from a horizontal position and swings
on a string into a stationary brick of mass m2 = 2.5 kg, performing a purely elastic collision,
as shown below. What angle 𝜃 will the ball swing back to after the collision? The length of
the string is l=70 cm. Assume zero losses.

Problem 11
An object of mass m1 = 300 gram slides to the right with the speed of v1i = 2 m/s on a
frictionless surface and collides with another object of mass m2 = 400 gram (figure below,
left). The collision is purely elastic and happens at x = 0. The second object then slides for a
= 70 cm before hitting the wall, bouncing back with no loss of speed (figure on the right).
Find position on the x axis d where the second object will catch up with the first object.

Problem 12
In an experiment aimed at investigation of the law of conservation, a puck of mass m1 is
placed stationary on a frictionless ramp at an initial height of 2.5 m, as shown below. Once
released, it slides down and collides with a stationary puck of mass m2 = 2m1. Immediately
after the collision, the second puck start moving along the surface with the coefficient of
kinetic friction μk = 0.5 and comes to a stop at distance d. Find the distance d, assuming the
collision to be fully elastic.

### Physics 1 Quiz 5 2020.pdf
[2020] Physics I. Mechanics

Quiz 5 – Rotation

Unless specified otherwise, assume g = 9.81 m/s2. All problems are worth 25 points.

Section 1 – Linear and Angular Variables
Problem 1
As shown below, wheel A of radius rA = 10 cm is connected to wheel C of radius rC = 25 cm
by a belt B. The system is initially at rest. At a certain point in time, the angular acceleration
of wheel A becomes  = 1.57 rad/s2. Find the time t needed for the wheel C to complete 20
full rotations, assuming the belt does not slip.

C
B
A

rC

rA
Problem 2

A racing car’s tire with the diameter of D = 380 mm starts rotating from rest with constant
angular acceleration  = 18 rad/s2. The wheel then starts rolling over the ground without slipping.
How much time t is required for the wheel’s center to travel the distance of x = 10 m?

Problem 3
A wheel of radius R = 1.25 m is initially rotating in the positive direction with the angular
speed of 0 = 3.2 rad/s, as shown below. At time t0 = 0 s the wheel instantaneously receives
acceleration  = − rad/s2. Find how much time is required for the elevator A attached to
the wheel’s rim to descend by d = 2.5 m once the wheel receives the acceleration.

0



x

R

A
d

[2020] Physics I. Mechanics

Section 2 – Forces and Torques
Problem 4
A cylinder of radius R is placed on a plane inclined at angle  to the horizon and attached to a
wall by a rope at point A, as shown below. Assuming the static friction coefficient to be ,
find the range of angle  corresponding to the equilibrium of the cylinder (no slip). Hint:
when solving, find the torques generated by frictional and pulling forces.

A

R



O
mg

Problem 5
The figure on the right shows 2 blocks of masses m1 = 920 g and m2 = 1 kg,
respectively. The blocks are connected by a massless rope hanged over the
pulley, which is mounted on a horizontal axle with negligible friction and
has radius of R = 5 cm. Being initially at rest, both blocks are released. In 5
seconds, block 2 falls 75 cm, without the rope slipping on the pulley. What
is the rotational inertia I of the pulley? Hint: first find linear quantities
(blocks’ accelerations, tensions) and then move onto finding torques and
pulley’s angular acceleration.

R

m1

m2

Problem 6
Two blocks weighing m = 6.2 kg each are connected by a massless rope, as shown below.
The rope is thrown over a pulley, with corresponding tensions on each side being T1 and T2.
The pulley has radius R = 2.4 cm and the moment of inertia of I = 7.40×10−4 kg ·m2. Assume
that the axis of the pulley is frictionless, however there is friction force Ffr between block 2
and the surface. When the blocks are released from rest, the pulley turns through 0.130 rad in
91.0 ms, while blocks move with constant acceleration. What is the magnitude of friction
force Ffr? Hint: first find angular quantities (pulley’s acceleration and torque) and then move
onto finding blocks’ accelerations and tension forces.

m

T2
R

Ffr

T1

m

[2020] Physics I. Mechanics

Section 3 – Energy



Problem 7
A thin rod of length L = 55 cm is falling down from its vertical-up position
while pivoting about one of its ends, as shown on the right. Do the
following:
8.1. Find the radial acceleration ar of the top point when the rod makes
an angle of  = 35 degrees with the vertical (15 pts)
8.2. Find the angle at which ar = g (10 pts)

L

ar

Problem 8
A sphere (moment of inertia J = 2/3MR2, mass M = 4.5 kg, radius R = 8.5) cm can rotate
about a vertical axis. A massless rope is connected at one its end to a block A of mass m =
0.60 kg, with its other end wrapped around the middle of the sphere. On the way to the sphere,
the rope passes over a pulley of rotational inertia 𝐼 = 0.003 kg∙m2 and radius r = 5.0 cm.
There is zero friction everywhere and the rope does not slip on the pulley. What is the speed
of the object v when it has fallen 82 cm after being released from rest? Use energy
considerations.
M, R
I, r

A

Problem 9
A thin uniform rod of length L starts falling on the ground from its vertical position. Find the
speed  of the top end of the rod just before it hits the floor, if the bottom end does not slip.
Use the conservation of energy principle.

L



[2020] Physics I. Mechanics

Section 4 – Rolling
Problem 10
A solid sphere of a given radius rolls smoothly from its original stationary position at
height H = 6 m, as shown below. The sphere then falls from the horizontal section at the end
of the track, at height h = 2 m. Assume there is no friction and no air resistance. How far (d
= ?) from the edge will the ball land on the floor?

H
h
d
Problem 11
A circular object is rolling without slipping on a surface. Assume its total kinetic energy is 20
J. The radius of the object is R = 0.15 m, its rotational inertia I = 2/3mR2 = 0.040 kg·m2
(about the axis going through its center of mass). Answer the following:
11.1. How much of this kinetic energy is rotational and how much is translational? (10 pts)
11.2. What is the speed vcom of the object’s center of mass? (10 pts)

Problem 12
A car wheel is rolling smoothly over a horizontal surface with nonnegligible friction, with its
center of mass pulled by a constant force F = 10 N. The force causes the wheel’s center of
mass to accelerate at the rate of acom = 0.60 m/s2. The wheel’s mass is m = 10 kg and its
radius is R = 0.3 m. What is the rotational inertia I of the wheel about the rotation axis
through its center of mass? Hint: you may need to find the frictional force first.

R

F

### Physics 1 Quiz 1 2020.pdf
[2020] Physics I. Mechanics

Quiz 1 - Kinematics
Problem 1 (25 pts) – Velocity and Acceleration
Plot the velocity of the object whose acceleration is shown in Fig. 1, left.
Problem 2 (25 pts) – Velocities
A drop of rain falls at an angle of 30º to the vertical axis when the wind speed is u1 = 10 m/s.
The Innopolis wind intensifies. What is the wind speed u2 if the drop falls at an angle of 60º?

v (m/s)

2 4

6

9 t (s)

a (m/s2)
5
o

vy 30 v1
2 4

9

6

o

vy 60

v2

t (s)

-5

u1

u2

Figure 1: Diagrams for Problem 1 (left) and Problem 2 (right)
Problem 3 (25 points) – Shooting Ships
Two ships are moving parallel to each other in the opposite directions with speeds v1 and v2,
respectively (Figure 2, left). The first ship shoots at the second. Find the aiming angle 
required to hit the target if the shot is made when the distance between the ships is the
shortest (shown in the figure). Assume the speed of the projectile v0 is constant.
Hint: you do not need to calculate distances but only need to consider relative motion of one
ship with respect to the other.
Problem 4 (25 pts) – Projectile
A rock thrown at an angle α = 30º to the horizon has the same height at time instants t1 = 3 s
and t2 = 5 s after the throw (Fig. 2, right). Find the initial rock speed v0.

v2

v1

shot

y

=?

vy

0

v0

vx

t1

t2

Figure 2: Diagrams for Problem 3 (left) and Problem 4 (right)

x

[2020] Physics I. Mechanics

Quiz 1 - Kinematics
Problem 1 (25 pts) – Velocity and Acceleration
Plot the velocity of the object whose acceleration is shown in Fig. 1.
Problem 2 (25 pts) – Velocities
A cart is propelled over an xy plane with acceleration components ax = – 4 m/s2 and ay = 2
m/s2. Its initial velocity has components v0x = 8 m/s and voy = 12 m/s. In unit-vector notation,
what is the velocity of the cart when it reaches its greatest x coordinate?

v (m/s)

2.5
5

10

t (s)

a (m/s2)
5
5 10
t (s)
Figure 1: Diagram for Problem 1
Problem 3 (25 points) – Ships Roundtrip
A boat travels up and down a straight part of a river between the cities A-ville and Z-burg at a
constant speed of vb = 10 km/h (Fig. 2, left). The distance between the cities is 42 km. What
is the river speed vr if the boat completes the roundtrip between the cities in 10 hours?
Problem 4 (25 pts) – Projectile
A basketball player is performing a free throw lying down on the floor, with the ball launched
at an angle α = 60º to the ground (Fig. 2, right). What should be the initial velocity of the
ball v0 (assuming zero initial position) if the player wants to hit the hoop that is located 4.6 m
away from her and 3.05 m above the ground?

Z-burg

vb -vb

y

42 km

v0
60o

3.05 m

A-ville

0

4.6 m
vr
Figure 2: Diagrams for Problem 3 (left) and Problem 4 (right)

x

[2020] Physics I. Mechanics

Quiz 1 - Kinematics
Problem 1 (25 pts) – Velocity and Acceleration
Plot the velocity of the object whose acceleration is shown in Fig. 1.
Problem 2 (25 pts) – Velocities
Which velocity has the largest magnitude (speed)?
a) 𝑣 = 1𝑖̂ − 15𝑘̂,

c) 𝑣 = 8𝑗̂ + 4𝑘̂ ,

b) 𝑣 = −6𝑖̂ − 7𝑗̂,

d) 𝑣 = −3𝑖̂ + 9𝑗̂.

v (m/s)

-1

2 4

6

8 t (s)

a (m/s2)
2
2

4

6

t (s)

8

Figure 1: Diagram for Problem 1
Problem 3 (25 points) – Rock Drop
A rock is dropped (from rest) from the top of a 60-m-tall building (Figure 2, left). How far
above the ground is the rock 1.5 s before it reaches the ground?
Problem 4 (25 pts) – Projectile
A person throws a ball with a speed of v0 = 12 m/s at a target that is at height h = 5 m above
the ball’s level (Fig. 2, right). You want the ball’s velocity to be horizontal (vy = 0 m/s) at
the instant it reaches the target. At what angle θ above the ground must you throw the ball?

y

v

v0

60 m

h=?

q=?

5m

0

Figure 2: Diagrams for Problem 3 (left) and Problem 4 (right)

x

[2020] Physics I. Mechanics

Quiz 1 - Kinematics
Problem 1 (25 pts) – Velocity and Acceleration
Plot the velocity of the object whose acceleration is shown in Fig. 1.

v (m/s)

2 4

6

8 t (s)

4 6 8

t (s)

a (m/s2)
2
1
2
-3
Figure 1: Diagram for Problem 1
Problem 2 (25 points) – Ball Drop
A ball is tossed vertically to a height H. To what height must the ball be tossed if it is to
spend twice as much time in the air?
Problem 3 (25 pts) – Car Velocities
A vehicle car moving with constant acceleration covered the distance between two points
60 m apart in 6 s (Figure 2, left). Its speed v1 as it passed the second point was 15.0 m/s.
What was the speed v0 at the first point?
Problem 4 (25 pts) – Projectile
A shot is fired with an initial speed v0 = 30 m/s from the ground at a target that is at distance
R = 20 m, as shown in Fig. 2, right. What are the (a) least low and (b) greatest high launch
angles that will allow the projectile to hit the target?

y
v0

v1
x
60 m

High shot

v0

v0

Low shot

low = ?
0 high = ?

R

Figure 2: Diagrams for Problem 3 (left) and Problem 4 (right)

x

### Physics 1 Quiz 3 2020.pdf
[2020] Physics I. Mechanics

Quiz 3 – Energy and Work
Unless specified otherwise, assume g = 9.81 m/s2.
Problem 1 (25 pts) – Energy
A father running after his daughter has half the kinetic energy of the daughter, who has half
the mass of the father. The father speeds up by 1 m/s and then has the same kinetic energy as
the daughter. What are the original speeds of (a) the father and (b) the daughter?
Problem 2 (25 pts) – Force and Work
A 3-kg body is at rest on a frictionless surface when a constant horizontal force 𝐹⃗ acting in
the positive direction of an 𝑥 axis along the track is applied to the body at 𝑡 = 0 s. A graph of
the position of the object is shown below. How much work is done on the body by the
applied force 𝐹⃗ between 𝑡 = 0 and 𝑡 = 2 s?

t=0

0

t=1s

0.2
t = 0.5 s

t = 1.5 s

0.4

0.6

t=2s

0.8

x (m)

Problem 3 (25 pts) – Potential Energy
The spring of 𝑘 = 10 N/m is compressed by 5.5 cm and used to propel a 3.8 g cork from the
gun. What is the speed of the cork if it is released as the spring passes through its relaxed
position? Assume zero energy losses.
Problem 4 (25 pts) – Work Done by External Forces
An object is sliding on a horizontal surface, attached to one end of a spring with stiffness
coefficient of 𝑘 = 400 N/m. The object has a kinetic energy of 𝐾0 = 20 J as it passes through
the spring’s equilibrium position. As the object slides, a constant frictional force of
magnitude 10.0 N acts on it. Answer the following:
(a) How far (∆𝑥) will the object slide to the right from the equilibrium position before
coming momentarily to rest? (15 pts)
(b) What will be the kinetic energy of the object as it slides back through the equilibrium
position? (10 pts)

v

Ffr
x=0

Dx

[2020] Physics I. Mechanics

Quiz 3 – Energy and Work
Unless specified otherwise, assume g = 9.81 m/s2.
Problem 1 (25 pts) – Energy
How fast is a 1.5 kg ball traveling when it hits the ground 3.5 meters below its original
position, given it starts from rest? Assume zero drag.
Problem 2 (25 pts) – Force and Work
A sled and its rider (total mass of 85 kg) are moving on a horizontal surface with an initial
speed of 37 m/s. If a force slows them to a stop at a constant rate of 4 m/s2, answer the
following:
(a) What magnitude 𝐹 is required for the force? (5 pts)
(b) What distance 𝑑 do they travel while slowing? Use the concept of work (20 pts)
Problem 3 (25 pts) – Potential Energy
A 60 kg skier starts from rest at height 𝐻 = 20 m above the end of a ski-jump ramp and
leaves the ramp at angle 𝜃 = 28°. Neglecting the effects of air resistance and assuming
the ramp is frictionless, find the maximum height ℎ of her jump above the end of the ramp.
Skier
H

h

q

Problem 4 (25 pts) – Work Done by External Forces
A 520-kg object slides from rest down a ramp that is 500 m long and 300 m high. The
coefficient of kinetic friction between the object and the surface is 0.25. Answer the
following:
(a) Assuming the gravitational potential energy 𝑈 of the object–Earth system is zero at the
bottom of the ramp, what is the value of 𝑈 just before the slide? (5 pts)
(b) How much energy is transferred to thermal energy during the slide? (15 pts)
(c) What is the kinetic energy of the object as it reaches the bottom of the ramp? (5 pts)

300 m

500 m

[2020] Physics I. Mechanics

Quiz 3 – Energy and Work
Unless specified otherwise, assume g = 9.81 m/s2.
Problem 1 (25 pts) – Energy
An 85-kg roller coaster cart is traveling 4 m/s at the top of a hill 50 meters off the ground.
How fast is it traveling at the top of a second hill 20 meters off the ground? Assume zero
friction
Problem 2 (25 pts) – Force and Work
A 5-kg block moves in a straight line on a horizontal frictionless surface under the influence
of a force that varies with position as shown in figure below. How much work is done by the
force as the block moves from the origin to 𝑥 = 8.0 m?

F (N)
10
2 4

6

8 x (m)

-10

Problem 3 (25 pts) – Potential Energy
A spring-loaded air gun fixed to a table shoots a ball at a target located on the floor. The
horizontal distance is 𝐷 = 2.50 m from the edge of the table, as shown below. When you
compress the spring by 1.1 cm, the projectile falls 25 cm short of the target. How far should
you compress the spring to score a direct hit? Assume zero friction and air drag.

D

Problem 4 (25 pts) – Work Done by External Forces
A 60-kg skier jumps from a ramp with a velocity of 24 m/s directed 25° above the horizontal.
Suppose that as a result of air drag the skier returns to the horizontal ground with a speed of
22 m/s, landing 14 m vertically below the end of the ramp. By how much is the mechanical
energy of the skier – Earth system reduced because of air drag?

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)

---
type: regulation
title: "Первый отборочный этап — contest-en"
resource: "https://lk-dovuz.innopolis.university/public/files/contest-en.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/contest-en.pdf"
    id: "7a75ccdde34a"
    title: "Первый отборочный этап — contest-en"
    last_modified: "2026-11-01T23:17:20+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:20+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Первый отборочный этап — contest-en

Innopolis Open Robotics ,

Problem A. Maximum Gear Ratio in a Gear System

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

Engineer Vasya has an experimental setup consisting of n gears arranged in a straight line. Each gear is characterized by its number of teeth.

The gear ratio between two adjacent gears is calculated as the ratio of the number of teeth of the driving gear to the number of teeth of the driven gear. For a system of multiple gears, the gear ratio is calculated as the product of the gear ratios between adjacent gears.

Help Vasya find a contiguous subsequence of gears that gives the maximum output gear ratio when the leftmost gear in the subsequence is rotated.

Input

The first line contains an integer n (1 < n ≤ 105) — the number of gears. The second line contains an array a of n integers (1 ≤ ai ≤ 109) — the number of teeth on each gear.

Output

The maximum gear ratio that can be obtained from any subsequence of the system, expressed in the form P Q. Output two numbers separated by a space P and Q.

Scoring

| № | Constraints | Points |
| --- | --- | --- |
| 1 | n ≤ 100 | 20 |
| 2 | n ≤ 2000 | 20 |
| 3 | n ≤ 105;ai ≤ 100 | 30 |
| 4 | n ≤ 105 | 30 |

Example

| standard input | standard output |
| --- | --- |
| 5 6 3 8 4 2 | 4 1 |

Problem B. Improvement of the Gear System

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

Engineer Vasya has an experimental setup consisting of n gears arranged in a straight line. Each gear is characterized by its number of teeth.

The gear ratio between two adjacent gears is calculated as the ratio of the number of teeth on the driving gear to the number of teeth on the driven gear. For a system of multiple gears, the overall gear ratio is calculated as the product of the gear ratios between adjacent gears.

Vasya discovered that the total gear ratio from the first to the last gear depends only on the number of teeth on the first and last gears. Help Vasya find the minimum number of operations to swap two gears necessary to achieve the maximum overall gear ratio of the system.

Input

The first line contains an integer n (1 < n ≤ 105) — the number of gears. The second line contains an array a of n integers (1 ≤ ai ≤ 109) — the number of teeth on each gear in the original order.

Output

In the first line, output an integer k — the minimum number of swap operations. In each of the following k lines, output two integers i and j (1 ≤ i,j ≤ n) — the positions of the gears that need to be swapped.

Scoring

| № | Constraints | Points |
| --- | --- | --- |
| 1 | n ≤ 10 | 20 |
| 2 | n ≤ 1000 | 20 |
| 3 | n ≤ 105; all ai are distinct | 30 |
| 4 | n ≤ 105 | 30 |

Examples

| standard input | standard output |
| --- | --- |
| 2 974365976 715806713 | 0 |
| 3 3 1 2 | 1 2 3 |
| 3 2 3 1 | 1 1 2 |

Problem C. Meeting on a Sleeper Train

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

Kamil and Vadim entered the sleeper train from opposite ends. The train consists of n cars, numbered from 1 to n. For each car, its degree of fullness ai is known — an integer (the more people in the car, the harder it is to pass through).

There are n + 1 vestibules in the train:

- • vestibule 0 — in front of the first car;

- • vestibule i — between cars i and i + 1 (for 1 ≤ i ≤ n − 1);

- • vestibule n — after the last car.

Kamil enters the train through vestibule 0 and goes to the right. Vadim enters through vestibule n and goes to the left. They want to meet in the same vestibule (with the same number).

Path complexity — is the sum of the values ai of all the cars that need to be passed through to get from the starting vestibule to the chosen one.

- • To get from vestibule 0 to vestibule k (1 ≤ k ≤ n), one must pass through cars 1,2,...,k.

- • To get from vestibule n to vestibule k (0 ≤ k ≤ n−1), one must pass through cars n,n−1,...,k+1.

It is required to choose the vestibule number where the absolute difference in the path complexities of Kamil and Vadim will be minimal.

If there are several such vestibules, the vestibule with the smallest number should be chosen.

Input

The first line contains one integer n (1 ≤ n ≤ 105) — the number of cars. The second line contains n integers a1,a2,...,an (0 ≤ ai ≤ 1000) — the degrees of fullness of the cars.

Output

Output one integer — the vestibule number from 0 to n, where Kamil and Vadim should meet. If several vestibules give the same minimal difference in complexities, output the vestibule with the smallest number.

Scoring

| № | Additional Constraints | Points |
| --- | --- | --- |
| 1 | n ≤ 1000 | 40 |
| 2 | all values ai are the same | 20 |
| 3 | no additional constraints | 40 |

Examples

| standard input | standard output |
| --- | --- |
| 5 1 2 3 4 5 | 3 |
| 4 5 5 5 5 | 2 |

Note

In the first example, the total fullness of all cars is 15.

- • Vestibule 0: Kamil’s path has a complexity of 0, Vadim’s path — 15, difference 15.

- • Vestibule 1: Kamil passes car 1 (1), Vadim — cars 2...5 (14), difference 13.

- • Vestibule 2: Kamil passes cars 1 and 2 (3), Vadim — cars 3...5 (12), difference 9.

- • Vestibule 3: Kamil passes cars 1...3 (6), Vadim — cars 4 and 5 (9), difference 3.

- • Vestibule 4: Kamil passes cars 1...4 (10), Vadim — car 5 (5), difference 5.

- • Vestibule 5: Kamil’s path — 15, Vadim’s path — 0, difference 15.

Problem D. Optimal Trip

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

Petya is driving a car on a straight road that is S kilometers long. At the beginning of the journey, his speed is a kilometers per hour. At any moment, Petya can choose his current speed v, which must always satisfy a ≤ v ≤ a + d.

The energy he expends while driving depends on the chosen speed. It is known that for any segment of the road of length L, which Petya travels at a constant speed v, he expends energy

Eseg = k · v · L, where k is a given coefficient, and v is the speed on that segment.

The total energy that Petya can expend for the entire trip is limited by the value E. It is guaranteed that there is always enough energy to travel the entire distance at the minimum possible speed: the inequality

E ≥ k · a · S holds.

Petya wants to travel the entire distance of S kilometers in the minimum possible time. Among all methods that yield the same minimum time, he is interested in the one where the total energy expended is minimal.

You need to find:

- • the time T that Petya will spend on the trip;

- • the energy En that he will expend.

The answer is considered correct if the absolute or relative error of each of the numbers T and En does not exceed 10−6.

Input

The first line contains five integers: a,d,S,k,E (1 ≤ a ≤ 106, 0 ≤ d ≤ 106, 1 ≤ S ≤ 106, 1 ≤ k ≤ 106, 1 ≤ E ≤ 1018). It is also guaranteed that E ≥ k · a · S and k · (a + d) · S ≤ 1018.

Output

Output two real numbers:

- • T — the time (in hours) that Petya spends on the trip;

- • En — the total energy that he will expend.

Your answer will be accepted if the absolute or relative error of each number does not exceed 10−6.

Scoring

In all subtasks, the constraints from the statement are satisfied, including E ≥ k · a · S.

| № | Additional Constraints | Points |
| --- | --- | --- |
| 1 | d = 0 | 30 |
| 2 | E ≥ k · (a + d) · S | 30 |
| 3 | no additional constraints | 40 |

Examples

| standard input | standard output |
| --- | --- |
| 10 10 100 1 2000 | 5.0000000000 2000.0000000000 |
| 10 20 100 1 1500 | 6.6666666667 1500.0000000000 |

Problem E. Optimal Elevator Rides

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

Sergey has been tasked with optimizing the operation of an elevator in a high-rise business center. The building has one elevator and several employees who want to descend to the first floor after work.

For each test, the number of employees m, the limit on the number of stops per elevator ride k, and the floors where the employees are located a1,a2,...,am are given. Elevator Operation Rules:

- • The elevator always starts its ride on the first floor and ends on the first floor.

- • In one ride, the elevator can make no more than k stops (excluding the first floor).

- • There can be multiple employees on the same floor—the elevator picks up all of them in one stop.

- • In one ride, the elevator can stop at any floors in any order, but the total number of stops in that

ride must not exceed k.

- • It is important that in the end, all employees are on the first floor, meaning that every floor where

someone is located must be visited at least once during the rides.

The player’s task is to create a plan for the elevator rides such that the total number of rides is as small as possible.

The route is described as follows: for each ride, the number of floors the elevator will stop at and the list of those floors are specified.

Format for describing one test (file inputX.txt):

- • The first line: two integers m and k — the number of employees and the maximum number of stops

per ride.

- • The second line: m integers a1,a2,...,am — the floors where the employees are located.

It is guaranteed that 1 ≤ m ≤ 20, 1 ≤ k ≤ 100, 2 ≤ ai ≤ 109. Format for the answer for one test:

- • The first line: one integer r — the number of rides the elevator will make.

- • The next r lines describe each ride:

- – at the beginning of the line, the number ti is written — the number of stops in the i-th ride

(1 ≤ ti ≤ k);

- – followed by ti integers xi,1,xi,2,...,xi,ti — the floor numbers where the elevator will stop in

this ride.

Floors in one ride can be specified in any order. It is important that each floor with at least one employee is included in at least one ride.

If you do not know the solution for a test, you can output the single number 0 — in this case, you will receive 0 points for that test.

There are four test files for which a ride plan is required: input1.txt, input2.txt, input3.txt, input4.txt. If you do not know the answer for any test, output 0 for it.

As an answer to this problem, attach a txt-file.

- • If you are sending a txt-file, it should contain the answers for tests 1, 2, 3, and 4 in the specified

order. For each test:

- – first a line with the number r — the number of rides,

- – then r lines with the description of the rides in the format specified above.

You may leave empty lines between the answers for different tests.

Tests Below is the content of the four files inputX.txt.

Test 1 (input1.txt): 6 2

9 10 2 3 5 8 Test 2 (input2.txt):

10 3 2 2 5 5 8 8 10 10 7 3

Test 3 (input3.txt): 15 4 2 4 6 8 10 12 14 16 18 20 3 5 7 9 11

Test 4 (input4.txt):

20 3 100 50 75 60 90 80 110 120 55 65 95 85 130 140 150 160 170 180 190 200

Each test is scored from 0 to 25 points according to the formula 25 · rbest rparticipant

, where rparticipant is the number of rides in your plan for that test, rbest is the minimum number of rides in the jury’s reference solution. The value of the fraction does not exceed 1, as the reference solution is optimal.

If the answer for a test is incorrect (format is violated, there is a ride with ti > k, floors outside the range are specified, or not all required floors are covered at least once), then 0 points will be awarded for that test.

Problem F. Drone Testing

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

An engineering laboratory is conducting tests of an autonomous navigation drone in a two-dimensional environment. The environment is characterized by a vector field that changes over time and affects the drone’s movement. At each step, the drone can choose its own direction and speed, but its capabilities are limited.

Let (vx,vy) be the chosen speed of the drone relative to the environment, and (qx,qy) be the vector field at the current moment in time. Then the actual displacement of the drone in one second is (vx +qx,vy +qy).

The drone starts from point (Sx,Sy) and must reach point (Ex,Ey) exactly after k seconds. During the experiment, the vector field changes n times. Each of these intervals is characterized by a duration of ti seconds and a constant value of the field (qxi,qyi). The sum of all durations equals the total time of the test: t1 + t2 + ··· + tn = k.

It is necessary to determine whether there exists a control strategy that allows reaching the goal in exactly k seconds. If possible, a valid trajectory of the drone must be outputted — its coordinates after each second.

Input

The first line contains four integers: Sx, Sy, Ex, Ey (−104 ≤ Sx,Sy,Ex,Ey ≤ 104) — the coordinates of the starting and ending points.

The second line contains three integers: n, k, vmax (1 ≤ n,k,vmax ≤ 105) — the number of intervals, the total flight time, and the maximum own speed of the drone.

Each of the following n lines contains three integers: ti, qxi, qyi — the duration ti seconds during which the vector field equals (qxi,qyi). It is guaranteed that: t1 + t2 + ··· + tn = k, qx2i + qy2i ≤ vmax.

Output

Output the string «Yes» if the drone can reach the goal exactly in k seconds, or «No» if it is impossible. If the answer is «Yes», output k lines, the i-th of which should contain two real numbers xi,yi — the coordinates of the drone after the i-th second of movement.

A plan is considered correct if:

- • for each step, a speed (vx,vy) can be chosen such that |vx2 + vy2|1/2 ≤ vmax, so that after accounting

for the field, the deviation from the specified coordinates does not exceed 10−5;

- • the distance between the final point (xk,yk) and the target (Ex,Ey) is no more than 10−5.

Scoring

| Subtask | Constraints | Points |
| --- | --- | --- |
| 1 | fxi = fyi = 0 for all i (no field) | 15 |
| 2 | n = 1 (field constant over time) | 20 |
| 3 | n ≤ 1000, k ≤ 1000 | 25 |
| 4 | no additional constraints | 40 |

Innopolis Open Robotics , Example

| standard input | standard output |
| --- | --- |
| 1 1 7 4 2 3 13 1 3 2 2 1 2 | Yes 4.3333333333 2.0000000000 5.6666666667 3.0000000000 7.0000000000 4.0000000000 |

Problem G. Robot and Delivery

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

Engineers at MechaPost are testing an autonomous courier robot that must deliver a package through an urban grid. The city consists of L rows and C columns of cells. Each cell represents a district, for which a certain amount of energy is required to traverse.

If the value in a cell is −1, that district is inaccessible (for example, destroyed or closed for repairs), and the robot cannot pass through it. In other cells, an integer pi,j indicates the base cost of moving through that district.

The robot starts at point A (row L1, column C1) and must reach the destination point B (row L2, column C2). Before starting its journey, it receives a package weighing W kilograms. The heavier the package, the more energy it consumes: crossing a district with a difficulty of p requires p · W units of energy.

The robot can only move to adjacent cells — up, down, left, and right — and cannot go outside the map boundaries. Energy is consumed when leaving the current district; arriving at the destination point

B does not require energy.

The battery reserve is limited — it cannot expend more than E units of energy. You need to determine the maximum weight of the package W that the robot can deliver from A to B without exceeding the energy limit.

It is guaranteed that there is at least one route connecting A and B that does not pass through inaccessible districts.

Input

The first line contains three integers: L, C, E (2 ≤ L,C ≤ 100;1 ≤ E ≤ 109) — the dimensions of the map and the maximum energy reserve.

The next L lines contain C numbers pi,j (1 ≤ pi,j ≤ 104 or pi,j = −1) — the energy costs of moving through the districts (pi,j = −1 means that the district is inaccessible).

The following line contains two numbers: L1, C1 (1 ≤ L1 ≤ L,1 ≤ C1 ≤ C) — the coordinates of the robot’s starting position A.

The last line contains two numbers: L2, C2 (1 ≤ L2 ≤ L,1 ≤ C2 ≤ C) — the coordinates of the destination point B.

It is guaranteed that (L1,C1) ̸= (L2,C2).

Output

Output a single integer — the maximum weight of the package W that the robot can deliver without exceeding the available energy reserve E.

Scoring

| № | Additional Constraints | Points |
| --- | --- | --- |
| 1 | L = C = 2, E ≤ 100, no inaccessible districts, A = (1,1), B = (2,2) | 22 |
| 2 | All accessible districts have the same difficulty pi,j = k | 27 |
| 3 | There is a unique accessible path between A and B | 20 |
| 5 | No additional constraints | 31 |

| standard input | standard output |
| --- | --- |
| 4 4 94 2 3 -1 2 1 -1 5 4 1 1 1 3 9 2 2 1 4 1 1 4 | 4 |

Problem H. Observer Robots

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

In a research center, there is a network of N identical observer robots. Each robot measures a certain environmental parameter (for example, the level of vibrations or noise) and sends its load to the server — a non-negative real number.

The robot must send data every Z minutes for M days. Thus, at every moment in time t = 0,Z,2Z,...,(M · 24 · 60 − Z) each robot must forward one load value.

Due to communication interference, some messages from the robots were lost, resulting in "gaps"in the data on the server. Based on the available measurements, it is necessary to restore all the missing values.

Engineers noticed that the operating mode of the robot at the same time of day is similar from day to day. Therefore, they proposed the following recovery rule.

Consider robot number b and a certain moment in time t (in minutes from the start of observations) when the load value is missing.

**1.** Let D = 24 · 60 be the number of minutes in a day.

**2.** For each i from 1 to P, consider the moment in time ti = t − i · D, which is the same moment of the day, but from the i-th previous day. For each such ti, the load of robot b is known.

**3.** For each ti, calculate the average load for the previous hour: take all moments ti − Z, ti − 2Z, ..., ti − 60 (there are exactly 60/Z of them, since 60 is a multiple of Z), for each of them the load of robot b is known, and compute the arithmetic mean of these values.

**4.** Define the relative load at moment ti as the ratio of the load at moment ti to the average load for the previous hour for the same robot.

**5.** Find the average relative load over all P previous days for this time of day.

**6.** Now, for the current day and moment t, calculate the average load for the previous hour of robot b using the same rules: take the moments t − Z, t − 2Z, ..., t − 60 and find the arithmetic mean of the loads.

**7.** The restored load value of robot b at time t is equal to the product of the average relative load (over the P previous days) and the average load for the previous hour on the current day.

It is known that:

- • at all moments of the first hour of each day (that is, for all t from 0 to 60 − Z inclusive for

each day) data from all robots is available;

- • in the first P days of observations there are no "gaps"in the data for any robot;

- • the input data contains all measurements that could be obtained from the robots, and the gaps need

to be restored in the described manner;

- • it is guaranteed that the described recovery method is correctly defined for all required moments.

Based on the data obtained from the robots over the last M days, it is required to restore all the missing load values.

Input

The first line contains five integers N, M, K, P, and Z (1 ≤ N ≤ 100, 1 ≤ M ≤ 100, 1 ≤ K ≤ 100000, P ≤ 7, 15 ≤ Z ≤ 60). It is guaranteed that 60 is a multiple of Z.

It is assumed that observations are conducted from the moment of time t = 0 (the start of the first day) to the moment t = M · 24 · 60 minutes, and each robot must send data at all moments t = 0,Z,2Z,...,M · 24 · 60 − Z.

Following this, there are K lines, each containing three integers L, b, and t:

- • L (0 < L ≤ 1000) — the load of robot b at time t,

- • b (1 ≤ b ≤ N) — the robot number,

- • t (0 ≤ t < M · 24 · 60) — the time in minutes from the start of observations.

It is guaranteed that each specified time t in the input data is a multiple of Z and no pair (b,t) appears in the input data more than once.

Output

In the first line, output an integer R — the number of restored values (the number of "gaps"in the data). In the following R lines, output three values separated by spaces:

- • the restored load (a real number),

- • the robot number b,

- • the moment in time t in minutes from the start of observations.

The lines should be sorted first by increasing time t, and for equal times, by increasing robot number b. The load must be output with a precision of at least 10−4 (the answer is accepted if the absolute or relative error does not exceed 10−4).

Scoring

In the problem, each test is evaluated separately.

Example

| standard input | standard output |
| --- | --- |
| 1 2 25 1 60 5 1 0 5 1 60 5 1 120 5 1 180 5 1 240 5 1 300 5 1 360 5 1 420 5 1 480 5 1 540 5 1 600 5 1 660 5 1 720 5 1 780 5 1 840 5 1 900 5 1 960 5 1 1020 5 1 1080 5 1 1140 5 1 1200 5 1 1260 5 1 1320 5 1 1380 3 1 1440 | 23 3.0000 1 1500 3.0000 1 1560 3.0000 1 1620 3.0000 1 1680 3.0000 1 1740 3.0000 1 1800 3.0000 1 1860 3.0000 1 1920 3.0000 1 1980 3.0000 1 2040 3.0000 1 2100 3.0000 1 2160 3.0000 1 2220 3.0000 1 2280 3.0000 1 2340 3.0000 1 2400 3.0000 1 2460 3.0000 1 2520 3.0000 1 2580 3.0000 1 2640 3.0000 1 2700 3.0000 1 2760 3.0000 1 2820 |

Problem I. Balance on the Axis

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

Consider a straight axis passing through point 0. On the left ray of this axis, there are L integer positions marked: 1,2,...,L. On the right ray, there are also L integer positions marked: 1,2,...,L.

Two objects with coefficients A and B, respectively, must be placed on this axis. The object with coefficient A is placed on the left ray at position x (x is an integer, 1 ≤ x ≤ L). The object with coefficient B is placed on the right ray at position y (y is an integer, 1 ≤ y ≤ L).

The axis is in equilibrium if the following equality holds: A · x = B · y. Determine whether there exist such integer positions x and y (one on each ray, 1 ≤ x,y ≤ L) for which the axis will be balanced.

Input

The only line of input contains three integers A, B, and L (1 ≤ A,B,L ≤ 1018) — the coefficients of the objects and the number of positions on each ray, respectively.

Output

Print YES if the desired positions exist. Otherwise, print NO.

Scoring

Each group of tests will be evaluated only if all mandatory groups of tests are passed. Points are awarded only if all tests in the group are passed. Examples are not evaluated. All tests are divided into groups with the following constraints:

| Subtask | Constraints | Mandatory Groups | Points |
| --- | --- | --- | --- |
| 1 | A,B ≤ 105 |  | 20 |
| 2 | A,B ≤ 109 | 1 | 30 |
| 3 | A,B ≤ 1018 | 2 | 50 |

Examples

| standard input | standard output |
| --- | --- |
| 2 4 5 | YES |
| 10 6 4 | NO |

Note

In the first example, one possible solution is to choose x = 4 and y = 2, then the equality 6 · 4 = 12 · 2 will hold.

Problem J. Arseniy’s Sequence

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

The hamster Arseniy invented a sequence of fractions:

1 + 1

1 + p2

1 + p3

1 + p1 p1 =

, p3 =

, p4 =

, ...

, p2 = that is, for all i ≥ 2, the recurrence relation holds

1 + pi−1 pi =

.

Arseniy is not good at calculations, so he asks you to help him find the n-th fraction pn. The value of pn can be expressed as a fraction ab, where a and b are coprime. You are required to find the corresponding fraction pn for several given values of n. If you do not know the answer for a test, you can write -1.

As an answer to this problem, attach a txt file. When submitting the txt file, the first line should contain the expression corresponding to the answer for the first test, the second line for the second test, and so on.

Each test is worth 25 points. No more than three files will be accepted for this problem. For each test, output the answer either as a and b (two numbers separated by a space) or as -1.

| Test Number | Value of n | Answer |
| --- | --- | --- |
| 1 | 3 | (answer field) |
| 2 | 6 | (answer field) |
| 3 | 10 | (answer field) |
| 4 | 15 | (answer field) |

# Citations

1. [Первый отборочный этап — contest-en](https://lk-dovuz.innopolis.university/public/files/contest-en.pdf), file 7a75ccdde34a

---
type: regulation
title: "Первый отборочный этап — reshenie en"
resource: "https://lk-dovuz.innopolis.university/public/files/reshenie_en.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/reshenie_en.pdf"
    id: "37294e8a399b"
    title: "Первый отборочный этап — reshenie en"
    last_modified: "2026-11-01T23:17:24+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:24+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Первый отборочный этап — reshenie en

Innopolis Open Robotics ,

Problem A. Maximum Gear Ratio in a Gear System

Given n gears with the number of teeth ai. It is necessary to find a contiguous subsequence of gears al,al+1,...,ar, such that the product of the ratios of adjacent gears aal

· aal+1

··· ara−1 is maximized. After simplification, this product equals aal r l+1 l+2

. Thus, the problem reduces to finding indices l ≤ r that maximize r al ar .

Solution Idea

Note that for a fixed l, the maximum value of aal is achieved with the minimum ar among all r ≥ l. Therefore, for each index l, it is sufficient to consider the minimum element in the suffix [l,n − 1]. It remains to iterate through all l and select the maximum ratio minal r ar . To efficiently find the minimum in the suffix, we can precompute the suffix minimums: sufMin[i] = min(a[i],sufMin[i + 1]), sufMin[n − 1] = a[n − 1] After finding the maximum ratio, the fraction is simplified by the GCD of the numerator and denominator. r≥l

Problem B. Improvement of the Gear System

Given n gears with the number of teeth ai. The overall gear ratio from the first to the last gear is equal to aa1

··· ana−1

= aa1

· aa2

. The goal is to maximize this ratio with the minimum number of swaps of any two gears. In one swap, you can exchange the gears at positions i and j. n n

Solution Idea

Since the gear ratio is equal to aa1

, to maximize it, we need to: n

**1.** Make the numerator a1 as large as possible.

**2.** Make the denominator an as small as possible.

Thus, we need to place the maximum element of the array in the first position and the minimum element in the last position. Consider the cases:

**1.** Case 1: If a1 = max(a) and an = min(a) — the answer is 0.

**2.** Case 2: If a1 = max(a) but an ̸= min(a) — only 1 swap is needed: swap the minimum element with the last one.

**3.** Case 3: If an = min(a) but a1 ̸= max(a) — only 1 swap is needed: swap the maximum element with the first one.

**4.** Case 4: If a1 = min(a) and an = max(a) — only 1 swap is needed: swap the first and last elements.

**5.** Case 5: In all other cases, 2 swaps are needed: first place the maximum at the first position, then the minimum at the last (or vice versa).

Problem C. Meeting on a Sleeper Train

Given a train of n cars with fullness ai. Kamil starts in vestibule 0 and goes right, Vadim starts in vestibule n and goes left. When they meet in vestibule k:

- • Kamil’s path: sum a1 + a2 + ··· + ak (denote it as Pk)

- • Vadim’s path: sum an + an−1 + ··· + ak+1 (this is S − Pk, where S = ni=1 ai)

We need to find k (from 0 to n) that minimizes |Pk −(S −Pk)| = |2Pk −S|, and in case of equality, choose the smallest k.

Solution Idea

Let us denote:

- • S = ni=1 ai — the sum of all fullness

- • Pk = ki=1 ai — the prefix sum up to the k-th car (for k = 0: P0 = 0)

Then:

- • Kamil’s path complexity to vestibule k: Ckam = Pk

- • Vadim’s path complexity to vestibule k: Cvad = S − Pk

- • Difference: |Ckam − Cvad| = |Pk − (S − Pk)| = |2Pk − S|

Thus, the problem reduces to finding k ∈ [0,n] that minimizes |2Pk − S|.

Key Observation: When increasing k by 1, the value of Pk increases by ak+1 ≥ 0, therefore 2Pk − S is monotonically non-decreasing. Thus, the minimum of the absolute value will be reached at the point where 2Pk − S changes sign from negative to positive, or where it equals zero. Optimization: It is not necessary to store all prefix sums; it is sufficient to accumulate the current sum in a variable.

Problem D. Optimal Trip

Petya is traveling a distance of S km. His speed v is limited: a ≤ v ≤ a + d. The energy for a segment of length L at speed v: Eseg = k · v · L. The total energy reserve: E, and it is guaranteed that E ≥ k · a · S. The goal is to minimize the travel time, and in case of equal time, minimize the expended energy.

Solution Idea

Note that at a constant speed v:

- • Time taken: T =

S v

- • Energy expended: En = k · v · S

The time T decreases as v increases, while the energy En increases as v increases. Key Observation: The optimal strategy is to drive at a constant speed equal to the maximum allowed under the constraints. We will show this:

**1.** To minimize time, speed must be maximized.

**2.** Constraints:

- • By condition: a ≤ v ≤ a + d

- • By energy: k · v · S ≤ E, i.e., v ≤

E k · S

**3.** Therefore, the maximum allowable speed:

E k · S vopt = min a + d,

E k · S

If vopt = a + d, then the time is minimized, and energy does not exceed E. If vopt =

, then the time is longer, but the energy is exactly equal to E (the limit).

Algorithm

**1.** Calculate the maximum speed based on physical constraints: vmax_speed = a + d

**2.** Calculate the maximum speed based on energy constraints: vmax_energy = E k · S

**3.** Optimal speed: vopt = min(vmax_speed,vmax_energy)

**4.** Time: T = S vopt

**5.** Energy: En = k · vopt · S

Problem E. Optimal Elevator Rides

There are m employees located on floors a1,...,am. The elevator:

- • Starts and ends on the 1st floor

- • Can make no more than k stops per ride (excluding the 1st floor)

- • Can pick up all employees from a floor in one stop

- • The order of stops is arbitrary

- • All floors with employees must be visited at least once

The goal is to minimize the number of rides.

Solution Idea

Notice the key points:

**1.** Since there can be multiple employees on one floor, it is sufficient to visit each floor with employees at least once. The order of visits within a ride does not matter.

**2.** The elevator always returns to the 1st floor, so each ride is independent.

**3.** The problem reduces to partitioning the set of unique floors into groups of size no more than k (stops per ride).

Thus, if U is the number of unique floors, the minimum number of rides is: rmin =

U k where ⌈x⌉ is the ceiling function.

Problem F. Drone Testing

The drone starts from point S = (Sx,Sy) and must reach E = (Ex,Ey) in exactly k seconds. At each step:

- • The drone chooses its speed (vx,vy) such that vx2 + vy2 ≤ vmax

- • The vector field at second i is (qxi,qyi)

- • The actual displacement: (vx + qxi,vy + qyi)

The field is defined by n intervals of constant value, and the sum of the durations equals k.

Solution Idea

Let us denote:

- • Di = (qxi,qyi) — the vector field at second i

- • Vi = (vxi,vyi) — the speed of the drone at second i (relative to the environment)

Then the displacement in one second is: Di + Vi. Over k seconds, the total displacement is: k k

(Di + Vi) =

Di + i=1 i=1 k

Vi = E − S i=1

Let Q = ki=1 Di — the total influence of the field. Then it is necessary to have: k

Vi = (E − S) − Q = ∆ i=1

The condition for each second: ∥Vi∥ ≤ vmax. Key Observation: If ∥∆∥ ≤ k · vmax, then it is possible to choose all Vi to be the same:

∆ k

Vi =

In this case, ∥Vi∥ = ∥∆k∥ ≤ vmax, which satisfies the constraint.

Algorithm

**1.** Calculate the total influence of the field Q = ki=1 Di

**2.** Calculate the required total contribution of the drone: ∆ = (E − S) − Q

**3.** If ∥∆∥ > k · vmax, output "No"(impossible)

**4.** Otherwise, output "Yes"and the trajectory:

- • Start: p0 = S

- • At each step: pi = pi−1 + Di + ∆k

Correctness Proof

**1.** If ∥∆∥ ≤ kvmax, then ∥∆k ∥ ≤ vmax

**2.** After k steps: pk = S + k i=1 Di + k i=1 ∆ k = S + Q + ∆ = S + Q + ((E − S) − Q) = E

**3.** All constraints are satisfied:

- • Drone speed: Vi = ∆k , ∥Vi∥ ≤ vmax

- • Time is exactly k seconds

- • Final point is exactly E

Problem G. Robot and Delivery

Given a two-dimensional maze L × C with a base cost pi,j ≥ 1 or −1 (inaccessible). The robot starts at (L1,C1) and must reach (L2,C2). The energy required to move from cell (i,j) to an adjacent cell is pi,j ·W, where W is the weight of the package. The total energy limit is E. You need to find the maximum integer W for which there exists a path within the energy limit E.

Solution Idea

Let us denote:

- • P = (i,j)∈path pi,j — the sum of base costs along the chosen path

- • Then the total energy: Etotal = P · W

For a fixed W, the problem reduces to finding the shortest path in a graph where the weight of the edge (transition from cell (i,j)) is pi,j · W. Since W is a constant for a specific test case, Dijkstra’s algorithm can be used.

A key observation: as W increases, the cost of any path increases proportionally. Therefore, there is monotonicity: if there is a path for W that is ≤ E, then there is also a path for any W′ < W (possibly a different path). This allows for binary search over W.

Algorithm

**1.** Read the data, convert coordinates to 0-indexing.

**2.** Perform binary search over W in the range [0,2 · 109] (the upper bound is overestimated for reliability).

**3.** For each Wmid, run Dijkstra:

- • The weight of the transition from (x,y) to an adjacent cell: px,y · W

- • Find the minimum energy required to reach the target

**4.** If the minimum energy ≤ E, try to increase W, otherwise decrease it.

**5.** Output the maximum W for which a path exists.

Problem H. Observer Robots

There are N robots measuring load every Z minutes for M days. Data for some moments is missing. It is necessary to restore the missing values using the algorithm:

For robot b and time t (a multiple of Z):

**1.** For each of the P previous days, find the moment ti = t − i · D (where D = 24 · 60)

**2.** For each ti, calculate the average load for the previous hour: the arithmetic mean for moments ti − Z,ti − 2Z,...,ti − 60

**3.** Calculate the relative load: ri = average forloadtheatpreviousti hour

**4.** Find the average relative load over all P days: R = P1 Pi=1 ri

**5.** For the current day, calculate the average load for the previous hour: A (using the same rules)

**6.** Restored value: R · A

Guarantees: data is available for the first hour of each day, and for the first P days, all data is available.

Solution Idea

Key points:

**1.** Time is discrete with a step of Z minutes. Total slots: totalSlots = M · (24 · 60/Z)

**2.** Restoration can be performed in chronological order, as only earlier data is needed to compute the average for the previous hour

**3.** After restoring the value, it needs to be saved for use in restoring subsequent values

Data Structure

- • val[slot][robot] — load value (known or restored)

- • has[slot][robot] — flag indicating the presence of original data

- • Slots are numbered from 0 to totalSlots − 1, time t = slot · Z

Algorithm

**1.** Initialization: read all known values, set flags

**2.** Iterate over all slots in increasing order of time

**3.** For each robot in the current slot:

- • If data is available — skip

- • Otherwise, compute the restored value using the formula

- • Save the value in the val array for use in future calculations

- • Add the answer to the list

**4.** Output the answers in the required order

Problem I. Balance on the Axis

Given coefficients A, B, and the limit L. It is necessary to determine whether there exist integers x and y (1 ≤ x,y ≤ L) such that:

A · x = B · y

Solution Idea

Rewrite the equation:

A · x = B · y Divide both sides by gcd(A,B):

A gcd(A,B) · x =

B gcd(A,B) · y Let:

A gcd(A,B)

B gcd(A,B) a′ =

, b′ =

Then a′ and b′ are coprime. The equation takes the form: a′ · x = b′ · y Since a′ and b′ are coprime, from the equality it follows that:

- • x must be divisible by b′

- • y must be divisible by a′

Let x = b′ · k, y = a′ · k for some integer k ≥ 1. Then the original equation holds for any k. The constraints are:

From this:

Thus, a solution exists if and only if:

1 ≤ x = b′ · k ≤ L

1 ≤ y = a′ · k ≤ L

L a′

L b′, k ≤ k ≥ 1, k ≤ max(a′,b′) ≤ L

Problem J. Arseniy’s Sequence

Given the sequence of fractions:

1 + 1 p1 =

1 + pi−1 pi =

You need to find pn = ab, where a and b are coprime.

= for i ≥ 2

Solution Idea

Let’s compute the first few terms of the sequence: p1 =

p2 =

1 + 12 =

=

p3 =

1 + 23 =

=

p4 =

1 + 35 =

=

p5 =

1 + 58 =

=

p6 =

1 + 138

=

=

Notice the pattern: the fractions correspond to consecutive ratios of Fibonacci numbers:

Fn Fn+1 pn = where F1 = 1,F2 = 1,F3 = 2,F4 = 3,F5 = 5,F6 = 8,... We will prove this by induction:

**1.** Base case: p1 = 12 = FF1

**2.** Induction hypothesis: pn−1 = Fn−1 Fn

**3.** Step:

1 + pn−1 pn =

=

1 + Fn−1

=

Fn

=

Fn+Fn−1 Fn

Fn Fn + Fn−1

Fn Fn+1

=

# Citations

1. [Первый отборочный этап — reshenie en](https://lk-dovuz.innopolis.university/public/files/reshenie_en.pdf), file 37294e8a399b

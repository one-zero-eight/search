---
type: regulation
title: "1st-round-tutorial-en-ioinformatics25"
resource: "https://lk-dovuz.innopolis.university/public/files/1st-round-tutorial-en-ioinformatics25.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/1st-round-tutorial-en-ioinformatics25.pdf"
    id: "3259fe95b063"
    title: "1st-round-tutorial-en-ioinformatics25"
    last_modified: "2026-11-01T23:17:18+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:18+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# 1st-round-tutorial-en-ioinformatics25

Innopolis Open 2024. Qualification Round 1 Russia, Innopolis, November, 24, 2024

Problem A. CosmoTile

General Observations

**1.** It is convenient to consider that the floor increases by a factor of x, rather than the tiles and their pieces decreasing by a factor of x;

**2.** If lcm(a,b) ≤ a · k, then the answer is 0. a · b gcd(a,b) b

Since lcm(a,b) = gcd(a,b) ≤ k. In the inequalities above, lcm(a,b) is the least common multiple of the numbers a and b, and gcd(a,b) is the greatest common divisor of the numbers a and b.

, the inequality lcm(a,b) ≤ a · k is equivalent to the inequality

Subgroups 1 and 2

In subgroup 1, the number b is odd. Therefore, the pieces after the cut will be of different sizes. Consequently, it will not be possible to use both pieces obtained after cutting one tile.

In subgroups 1 and 2, we can afford to model the tiling for each x and each row of tiles. The tiling continues until the total length of the tiles in the row reaches the length of the floor. The asymptotic complexity of such a solution is O(k3 · a). Pseudocode:

1 for x = 1 .. k

2 sum = 0

3 rem = 0

4 for i = 1 .. x

5 cur = 0

6 while cur < a * x

7 cur += b

9 if (cur - a * x) * 2 != b

10 sum += cur - a * x

11 else if rem > 0

12 sum -= cur - a * x

13 rem -= 1

14 else

15 sum += cur - a * x

16 rem += 1

18 ans = min(ans , sum)

Subgroup 3

Notice that the rows of tiles are absolutely identical. Therefore, it is sufficient to model the tiling process in the first row and multiply the obtained result by the number of rows. The asymptotic complexity of such a solution is O(k2 · a). Pseudocode:

1 for x = 1 .. k

2 cur = 0

3 while cur < a * x

4 cur += b

6 if (cur - a * x) * 2 != b

7 sum = (cur - a * x) * x

8 else

9 sum = (cur - a * x) * (x % 2)

11 ans = min(ans , sum)

Subgroup 4

Notice that for a fixed x, the last tile in the first row has either dimensions a by a, if a · x mod b = 0, where mod is the modulo operation; or a by a · x mod b, if a · x mod b = 0. In the first case, there will be no unused pieces of tile left after laying the row, and in the second case, there will be a piece of size a by b − a · x mod b, which may be used in another row.

The asymptotic complexity of such a solution is O(k). Pseudocode:

1 for x = 1 .. k

2 cur = a * x % b

3 if cur != 0

4 cur = b - cur

6 if cur * 2 != b

7 sum = cur * x

8 else

9 sum = cur * (x % 2)

11 ans = min(ans , sum)

Subgroup 5 and Complete Solution b

We will use the observation that the answer is 0 when gcd(a,b) ≤ k, and obtain a solution with an asymptotic complexity of O(b). Pseudocode:

1 if b / gcd(a, b) <= k

2 ans = 0

3 else

4 for x = 1 .. k

5 cur = a * x % b

6 if cur != 0

7 cur = b - cur

9 if cur * 2 != b

10 sum = cur * x

11 else

12 sum = cur * (x % 2)

14 ans = min(ans , sum)

Solutions that encounter overflow of 64-bit data types, for example, when calculating a · k, pass the tests of subgroup 5.

Problem B. Exponentiator-2025

Note that the result of the exponentiator’s work is always a number of the form awi i for some 1 ≤ i ≤ n and some natural wi. Therefore, we want to determine for each ai the maximum wi such that the result of the exponentiator equals awi i, and check divisibility by x only for these n numbers of the form awi i. Also, note that since x in the queries is up to 106, each prime factor appears in the factorization of x to no more than the 20th power. Therefore, if wi ≥ 20, we are not interested in the specific value, as the 20th power is sufficient to cover all possible prime factors from the factorization of x. Thus, we need to know the exact value of wi only if it is less than 20. Additionally, if ai = 1, we are not interested in the value of wi, as one raised to any power is still one. Therefore, we only consider wi for interesting ai > 1. The complete solution is divided into several cases:

- • For n = 2 and n = 3, in this case, it is necessary to explicitly enumerate all results of

the exponentiator’s work calculated modulo x for each query. The total number of ways the exponentiator can work will be n! · (n − 1)!···1!, which for n = 3 equals only 12, and easily fits within the time limit. For n = 3, it is important not to take both numbers modulo x after the first iteration of the exponentiator, as one of the numbers will later be the exponent. To avoid calculating a huge exponent completely, it is necessary to write a function bounded_pow(a, b) that returns min(20,ab), since again, passing numbers greater than 20 to the exponent does not make sense in the context of this problem.

- • If all numbers in the array are equal to 1, the answer is Yes only for x = 1.

- • If all numbers except one ai are equal to 1, then the result of the exponentiator’s work will either

be 1 or ai.

- • For n ≥ 4, there are at least two non ones in the array...

It turns out that if n ≥ 4 and there are at least two numbers greater than 1 in the array, then for all i, wi can always be greater than 20. We will demonstrate this with the example of n = 4 and the array [x,y,1,1]. The sequence of operations: [x,y,1,1] → [yx,x,1] → [x(yx),yx] → [y(x·x(y x))]. Substituting x = y = 2 into the exponent, we get the number 32. It is clear that when x,y ≥ 2, the exponent can only increase, similarly for increasing the number of elements both equal to 1 and greater than 1.

Thus, in this case, the problem reduces to "is there a number ai in the array a such that B ∈ A, where A is the set of prime divisors of the number ai, and B is the set of prime divisors of the number x."By writing the Sieve of Eratosthenes, we can compute the set of prime divisors for all numbers from 1 to

**106.** After that, each x can be transformed into x = ”theproductoftheuniqueprimedivisorsofx”, and for this number, we simply need to check if there is a number in the array a that is divisible by it. This can be done in O(xA ) by simply enumerating all possible numbers ≤ A that are divisible by x . By remembering and reusing answers for identical x , the asymptotic complexity of such a solution will be O(A1 + A2 + ... + AA) = O(Alog A), where A = 106, which comfortably fits within the limit.

Problem C. Bunny 3.1

Working title "Fractal Bunny"

General Idea of the Solution

We will count dp[i] — the number of ways to reach the step with number i. The recalculation of such dp[i] can be done by considering the last step before the bunny reaches step i. Then dp[i] = dp[i−step], where STEP — the set of possible last moves of the bunny. In other step ∈ STEP words, the number of ways to reach step i is equal to the sum of the number of ways to reach the steps one step before it.

Definition of Allowed Jumps

A step step is considered nice if the number step − 1 does not contain the digit 1 in its ternary representation. We will learn to check if a step step is nice. For this, we will write a function check, in which we will check the representation of the number step − 1 (how many steps the bunny jumped over) in the ternary numeral system.

1 bool check(int step) {

2 step --;

4 while (step) {

5 if (step % 3 == 1) {

6 return false;

7 }

8 step /= 3;

9 }

10 return true;

11 } The function check works in O(log n).

Subgroup 1. n ≤ 2000

We will recalculate dp[i] in a loop over i. We will go through all possible step. We recalculate only from the allowed ones. When recalculating, we update the value modulo: dp[i] = dp[i] % MOD.

1 #define ll long long

2 const ll MOD = 998244353;

1 for (int i = 1; i <= n; i++) {

2 for (int step = 1; step <= i; step++) {

3 if (check(step)) {

4 dp[i] += dp[i - step];

5 dp[i] %= MOD;

6 }

7 }

8 } We get a solution in O(n2 log n). This solution passes the first subgroup.

Subgroup 2. n ≤ 2 · 104

Notice that checking if each step is nice every time is slow. Instead, we can precompute for each step whether it is nice.

1 vector <bool > is_nice(n + 1, false);

3 for (int step = 1; step <= n; step++) {

4 is_nice[step] = check(step);

5 }

7 for (int i = 1; i <= n; i++) {

8 for (int step = 1; step <= i; step++) {

9 if (is_nice[step]) {

10 dp[i] += dp[i - step];

11 dp[i] %= MOD;

12 }

13 }

14 } This solution works in O(nlog n + n2), passes the second subgroup of tests, and earns 45 points.

Subgroup 3. n ≤ 2 · 105 Notice that there are relatively few nice steps among all steps from 1 to n. Specifically, there are 2log3 n = nlog23 ≈ n0.63, which is about 2000 when n = 2 · 105.

Using this fact, we will modify the solution. First, we will find a list of all allowed steps, after which we will recalculate dp only through them.

1 vector <int > nice_steps;

3 for (int step = 1; step <= n; step++) {

4 if (check(step)) {

5 nice_steps.push_back(step);

6 }

7 }

9 for (int i = 1; i <= n; i++) {

10 for (int step: nice_steps) {

11 if (i - step < 0) {

12 break;

13 }

14 dp[i] += dp[i - step];

15 dp[i] %= MOD;

16 }

17 }

This solution already works faster, but may not pass subgroup 3 — in this case, we can, for example, notice that we often perform the heavy operation of division by modulo, while we can perform it just once after summation.

1 for (int i = 1; i <= n; i++) {

2 for (int step: nice_steps) {

3 if (i - step < 0) {

4 break;

5 }

6 dp[i] += dp[i - step];

7 }

8 dp[i] %= MOD;

9 } This code works in O(n · nlog3 2), passes subgroup 3, and earns 60 points.

Subgroup 4. n ≤ 106 Let’s consider the set of steps from which we could reach the i-th step.

1 last_j = "#*#"

2 digit0 = "012"

4 last_j = "#*#***#*#"

5 digit0 = "012012012"

6 digit1 = "000111222"

8 last_j = "#*#***#*#*********#*#***#*#"

9 digit0 = "012012012012012012012012012"

10 digit1 = "000111222000111222000111222"

11 digit2 = "000000000111111111222222222"

Notice that this set of points when n = 3k does not contain allowed steps in the middle third of the steps. We want to calculate for each i the sum in such a structure ending at point i − 1.

It is clear that the sum over all # on a segment of length 3k, ending at point i, is recalculated as follows: sumk[i] = sumk−1[i − 2 · 3k−1] + sumk−1[i].

Then we can store sumk[i] at each point for all k such that 0 ≤ k ≤ log3 n. We will recalculate sumk[i] in increasing order of k. Then the next sum will be recalculated through the previous one.

This solution works in O(nlog n), passes subgroup 4, and earns 85 points.

Subgroup 5. n ≤ 2 · 106

Notice that the solution in the previous subgroup results in Memory Limit Exceeded. Therefore, we need to reduce memory consumption.

We will store our sumk[i] as int32t instead of int64t (long long). It is also worth noting that vector < vector < int >> can take more memory than we expect. We can use a two-dimensional array, vector < array < int,MAXK >>, or store everything in a one-dimensional vector, obtaining values as follows: sumk[i] = dpsum[MAXK · i + k].

This solution receives full points.

Problem D. Metro Repair

We will solve the problem immediately for the case α = 1.5. Let Rsum be the sum of ri for the completed works. Let Lsum be the sum of li for the completed works. Then, if both conditions are met, we can write the following chain of inequalities: m ≥ Rsum ≥ α · Lsum → mα ≥ Lsum → 23m ≥ Lsum This means that m − Lsum ≥ m − 23m = m3 . In other words, to satisfy the second condition, it is necessary for all works with rj ≤ m3 to be included in the plan, since m − Lsum ≥ m3 is guaranteed. At the same time, it will be possible to complete at most two works with rj > m3 , since Rsum cannot exceed m. After this observation, it is not difficult to count all work plans that include 0 or 1 work with rj > m3 by simply enumerating all such plans. The counting of plans with 2 works with rj > m3 , after some simple transformations, reduces to a similar problem: «Given two arrays x1 ...xn and y1 ...yn, as well as two constants X and Y . Count the number of 1 ≤ i < j ≤ n such that xi + xj ≥ X;yi + yj ≤ Y simultaneously»

After sorting the array x in non-decreasing order and iterating over i, such a problem reduces to queries of the form «how many numbers in the prefix of the array ≤ k», which can be answered, for example, using a MergeSortTree data structure, with a total asymptotic complexity of O(nlog2 n). However, it can also be solved with a sweep line and a Fenwick tree, with an asymptotic complexity of O(nlog n). Both solutions should have scored full points, but the solution with MergeSortTree might have needed some adjustments, depending on the efficiency of your implementation.

Problem E. MAX MEX MEX

Subgroup 2. ci = 0

In this subgroup, we cannot change the sets of numbers in the baskets. Therefore, we can calculate MEXi for all baskets, after which we can compute the MEX of the resulting set.

Such a solution passes the second subgroup and earns 10 points.

Obtaining the set of valid MEXi

Let’s learn how to obtain the set of valid values MEXi for each basket, which can be achieved by performing several (possibly zero) actions in the i-th basket.

To achieve MEXi = m for some m, we need all numbers [0,1,2,...,m − 1] to be present in the basket. Additionally, the number m itself must not be present in the basket.

Consequently, if a certain number 0 ≤ x ≤ m − 1 is not present in the basket, we need to obtain it from a smaller number through several increment actions.

We will go through all numbers from 0 to ni and check if we can achieve them as MEXi. We will maintain a set of "free"smaller numbers and, if necessary, place the largest of them in an empty spot (it can be proven that this is optimal). We will also keep track of how many actions we have left and check for each value whether it is possible to move all numbers equal to m at least one position to the right (for MEXi to equal m, it is necessary that the number m does not appear in the set).

Subgroup 1. ni ≤ 15, k ≤ 1000

Let’s define the set of valid MEXi. The answer depends on which specific values of MEXi we choose for each basket. Essentially, we are interested in what sets of values we can obtain before the final action of counting MEX(MEX1,MEX2,...,MEXk).

So let’s simply enumerate all possible subsets of values. In this subgroup, ni ≤ 15, thus MEXi ≤ 15. Therefore, there are a total of 216 possible subsets.

Let’s obtain all achievable subsets. This can be done by maintaining dp[i][mask] equal to 1 if we can obtain the set mask, and 0 otherwise. We recalculate the valid masks through the i-th set MEXi as follows:

1 for (int i = 0; i < k; i++) {

2 for (int mask = 0; mask < (1 << 16); mask++) {

3 for (int m: possible[i]) {

4 dp[i + 1][mask | (1 << m)] |= dp[i][mask];

5 }

6 }

7 }

Subgroups 3 and 4

Let’s assume we have obtained the set of valid values MEXi for each basket. We then get a bipartite graph between the baskets and the MEX values. The left part contains the set of baskets, and the right part contains the set of MEXi values.

We want the first m elements on the right to be "covered"by baskets. Essentially, we are looking for a matching that covers the first m vertices in the right part.

Blue baskets and red MEX values

Such a matching can be found in the following ways:

- • The Kuhn algorithm can be run sequentially from the vertices of the right part.

- • A binary search on the answer along with a maximum flow search or the Kuhn algorithm also solves

the problem and passes all tests.

Why does such a solution work quickly: First, from a basket of size ni, we can achieve a maximum of MEXi = ni, but not more. Therefore, the total number of edges in the graph does not exceed s, which is equal to 106. Second, the answer to the problem cannot be too large. Let the answer to the problem be M. Then the baskets have achieved MEX values equal to 0,1,2,...,M − 1. To achieve MEXi = j, it is necessary that there are at least j numbers in the ith basket. Therefore, to obtain an answer equal to M, it is necessary that the total number of numbers in the baskets is at least

M−1

√2 · s+1. Therefore, the answer does not exceed 1000, which explains the speed of the algorithm.

(M − 1) · M

(M − 1) · M

. That is, s ≥

, hence M ≤ m = m=0

Subgroup 5. bi — any, k ≤ 1000,s ≤ 3 · 104

In the last subgroup, there is an added complication—now each number aj appears with a frequency of bj. This changes the approach to finding valid values MEXi—now, when traversing from left to right, we will maintain a set of "free"numbers along with their frequencies.

Due to bi, the restriction on MEXi no longer works as in subgroup 4.

Note that the answer does not exceed k, so it is sufficient to consider values MEXi ≤ k. Thus, there will be no more than 106 edges in the graph, while the answer does not exceed k. Therefore, the Kuhn algorithm or the flow search algorithm with binary search will also solve the problem in this subgroup.

# Citations

1. [1st-round-tutorial-en-ioinformatics25](https://lk-dovuz.innopolis.university/public/files/1st-round-tutorial-en-ioinformatics25.pdf), file 3259fe95b063

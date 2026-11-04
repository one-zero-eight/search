---
type: regulation
title: "Второй отборочный этап — uslovia zadach 2 tur en"
resource: "https://lk-dovuz.innopolis.university/public/files/uslovia_zadach_2_tur_en.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/uslovia_zadach_2_tur_en.pdf"
    id: "a174edf10892"
    title: "Второй отборочный этап — uslovia zadach 2 tur en"
    last_modified: "2026-11-01T23:17:27+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:27+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Второй отборочный этап — uslovia zadach 2 tur en

Innopolis Open 2025-2026 Second qualification round Innopolis, December 28, 2025

Information

Memory limit

The limit is 256 MiB for each problem.

Source code limit

The size of each solution source code can’t exceed 256 KiB.

Submissions limit

You can submit at most 50 solutions for each problem. You can submit a solution to each task at most once per 30 seconds. This restriction does not apply in the last 15 minutes of the contest round.

Scoring

Each problem consists of several subtasks. The subtask score is awarded if all tests in the subtask are passed.

The number of points scored for the problem is the total number of points scored on each of its subtasks. The score for the subtask is the maximum number of points earned for this subtask among all the solutions submitted.

Feedback

To get feedback for your solution, go to “Runs” tab in PCMS2 Web Client and use “View Feedback” link. In each problem of the contest you will see the score for each subtask, or the verdict for the first failed test.

Scoreboard

The contestants’ scoreboard is available during the contest. Use “Monitor” link in PCMS2 Web Client to access the scoreboard. The standings provided in PCMS2 Web Client are not final.

Problem A. Non-trivial Energy of Crystals

Time limit: 1 second Hamster Shustrik and Hedgehog Shurshik are conducting a risky experiment.

They have n magical crystals, each with an integer energy level. The crystals must be placed into two chambers for further observation. In order for the experiment not to fail, the following rule must be satisfied: two crystals whose energies sum to a prime number must not be placed in the same chamber.

Help the hamster and the hedgehog find such a distribution of the crystals into two chambers that no pair of crystals violates the rule described above.

Shustrik and Shurshik remind that a prime number is a natural (positive integer) number that has exactly two distinct natural divisors — one and itself.

Input

The first line of input contains an integer n—the number of magical crystals (1 ≤ n ≤ 105). The second line of input contains n integers ai—the energies of all magical crystals (2 ≤ ai ≤ 1012).

Output

If it is impossible to distribute the crystals into two chambers while adhering to the described rule, output −1 − 1 (two minus one numbers separated by a space) in a single line. If it is possible to distribute the crystals, then:

In the first line, output the numbers n1 and n2—the number of crystals in the first and second chambers, respectively.

In the second line, output the energies of the magical crystals from the first chamber in any order, separating the elements with spaces.

In the third line, output the energies of the magical crystals from the second chamber in any order, also separating the elements with spaces.

If there are multiple distributions, output any of them.

Scoring

The tests for this problem consist of seven groups. Points for each group are awarded only if all tests of the group, all tests of the necessary groups, and tests from the problem statement are passed.

| Group | Points | Additional Constraints | Necessary Groups |
| --- | --- | --- | --- |
| 1 | 20 | n ≤ 10,ai ≤ 100 | – |
| 2 | 15 | n ≤ 200,ai ≤ 200 | 1 |
| 3 | 20 | n ≤ 200,ai ≤ 3 · 106 | 1, 2 |
| 4 | 15 | n ≤ 3000,ai ≤ 3 · 106 | 1, 2, 3 |
| 5 | 5 | n ≤ 10000,ai ≤ 5 · 107 | 1–4 |
| 6 | 10 | ai ≤ 109 | 1–5 |
| 7 | 15 | – | 1–6 |

Innopolis Open 2025-2026 Second qualification round Innopolis, December 28, 2025 Examples

| standard input | standard output |
| --- | --- |
| 2 2 3 | 1 1 2 3 |
| 6 7 14 30 91 15 74 | 3 3 7 14 74 30 91 15 |

Note

In the first example, the magical crystals with energies 2 and 3 cannot be in the same chamber, as 2+3 = 5, and the number 5 is a prime number.

In the second example, multiple distributions may be suitable as answers, including the distribution into (30,15) and (7,14,91,74) and the distribution into (30,14,74) and (7,91,15).

Problem B. Selling Apartments

Time limit: 1 second

Boris the Beaver is selling apartments at a very favorable (for him) price. Help him earn as much as possible in t days!

There are n apartments, numbered from 1 to n in the order given in the input data. Apartment i has a price of ai and is located in district bi. The sales days are numbered from 1 to t. Each day, Boris can:

- • sell exactly one apartment that he has not sold before; or

- • not sell anything.

Each time he sells, Boris claims that he has lived in the apartment for the last few years (this argument helps sell the apartment for a higher price), so in one district for K consecutive days, he can sell at most one apartment (otherwise, the residents of that district would notice that Boris has several apartments).

Input

The first line contains three integers n, K, t (1 ≤ n ≤ 105, 1 ≤ K ≤ 105, 1 ≤ t ≤ 105). The next n lines contain pairs of integers ai, bi (0 ≤ ai ≤ 109, 1 ≤ bi ≤ n) — the price of the apartment and the district number in which it is located.

Output

In the first line, output a single integer — the maximum possible revenue for Boris over t days. In the second line, output t integers. The d-th number should be the number of the apartment sold on day d, or −1 if Boris does not sell an apartment on that day. If there are multiple optimal answers, output any.

Scoring

| Group | Points | Additional Constraints | Required Groups |
| --- | --- | --- | --- |
| 1 | 7 | k = 1 | – |
| 2 | 19 | k = t | – |
| 3 | 17 | All ai are equal | – |
| 4 | 17 | All bi are equal | – |
| 5 | 40 | – | 1, 2, 3 |

| standard input | standard output |
| --- | --- |
| 6 2 4 10 1 15 1 8 2 14 3 14 3 14 3 | 53 5 1 6 2 |
| 6 3 8 10 1 10 1 10 1 20 2 20 2 20 2 | 90 4 1 -1 5 2 -1 6 3 |

Problem C. Arseniy’s Problem

Time limit: 1 second

Arseniy the hamster was too bored in school lessons, so he came up with an interesting problem for himself. Arseniy wants to find the smallest n-digit number x such that there exist k n-digit numbers not exceeding x with the same sum of digits. Help the hamster solve this problem.

An n-digit number is a non-negative integer whose representation in decimal consists of exactly n digits and does not contain leading zeros.

Input

The first line contains a single integer n (1 ≤ n ≤ 106). The second line contains a single integer k (1 ≤ k ≤ 1018).

Output

Output x. If x does not exist, output “−1” (without quotes).

Scoring

The tests for this problem consist of nine groups. Points for each group are awarded only if all tests of the group, all tests necessary for it, and tests from the statement are passed.

| Group | Points | Additional constraints | Necessary groups |
| --- | --- | --- | --- |
| 1 | 12 | n ≤ 3, k ≤ 100 | – |
| 2 | 15 | n ≤ 9, k ≤ 109 | 1 |
| 3 | 11 | n ≤ 18 | 1, 2 |
| 4 | 13 | n ≤ 1000 | 1, 2, 3 |
| 5 | 12 | k ≤ 20 | – |
| 7 | 10 | k ≤ 106 | 5, 6 |
| 8 | 14 | k ≤ 109 | 5, 6, 7 |
| 9 | 30 | – | 1–9 |

Examples

| standard input | standard output |
| --- | --- |
| 3 18 | 271 |
| 1 1 | 0 |

Note

In the first example, the following 18 three-digit numbers not exceeding 271 with the same sum of digits are suitable: 109, 118, 127, 136, 145, 154, 163, 172, 181, 190, 208, 217, 226, 235, 244, 253, 262, 271.

Problem D. Elephant Filimon and the Digit Three

Time limit: 2 seconds

Everyone knows that the Indian Elephant Filimon is a big fan of the digit 3. The elephant considers a number to be beautiful if it consists only of digits not exceeding 3, that is, digits 0, 1, 2, and 3.

Filimon has a positive integer n. In one operation, he can add to the current value of the number n any positive integer whose decimal representation consists exclusively of his favorite digit 3 (for example, 3, 33, 333, 3333, and so on).

Help Elephant Filimon determine the minimum number of operations needed to make n beautiful.

Input

Each test consists of several test cases. The first line contains one integer t (1 ≤ t ≤ 1000) — the number of sets of input data. The description of the sets of input data follows.

The only line of the test case contains the number n (1 ≤ n < 10107). Let len(n) denote the number of digits in the decimal representation of the number n. It is guaranteed that the sum of len(n) across all test cases does not exceed 107.

Output

For each test case, output one number: the answer to the problem. It can be shown that under the problem constraints, the answer always exists and does not exceed 263.

Scoring

The tests for this problem consist of ten groups. Points for each group are awarded only if all tests in the group and all tests necessary for it are passed. The symbol denotes the sum over all test cases.

| Group | Points | Additional Constraints | Necessary Groups |
| --- | --- | --- | --- |
| 1 | 6 | t ≤ 10;n ≤ 3000 | – |
| 2 | 7 | n ≤ 3 · 105 | 1 |
| 3 | 11 | t ≤ 10;n < 109 | 1 |
| 4 | 9 | n < 109 | 2, 3 |
| 5 | 5 | The answer does not exceed 2 | – |
| 6 | 13 | len(n) ≤ 60 | 1 |
| 7 | 17 | len(n) ≤ 300 | 3, 6 |
| 8 | 12 | len(n) ≤ 3000 | 7 |
| 9 | 11 | len(n) ≤ 106 | 4, 8 |
| 10 | 9 | – | 5, 9 |

Example

| standard input | standard output |
| --- | --- |
| 10 9 34 76 91 132 337 904 2009 64557444555 1913161522101310141615 | 1 2 2 3 0 2 3 1 5 15 |

Note

In the first test example, you can add the number 3, and 9 + 3 = 12 will be a beautiful number. In the second example, you can add 33 and 33, resulting in the number 100. In the third example, you can add 3 and 33, resulting in the number 112.

Problem E. Shustrik and Boxes

Time limit: 2 seconds

Shustrik the hamster has a set of n numbered boxes. These boxes can be nested within each other, forming a kind of hierarchy. Box number 1 is the outermost (the root of the hierarchy). For each other box, it is precisely known which parent box it is inside.

Inside each box (along with all the boxes nested within it) are «rods» (edges). Each rod connects two «points» (vertices). All points are numbered. The contents of each box u can be represented as a graph Gu, which is obtained by collecting all edges from box u and from all boxes inside it.

For each box u, Shustrik wants to compute the value of F(Gu).

F(G) = |A|=k f(A), where F(G) is a function of the graph, equal to the sum of functions f from all possible sets of vertices A of size k ( is the summation sign). f(A) is a function of a set of vertices, its value is equal to the product of ai (where ai is the weight at vertex i) for all i ∈ A, if all vertices in A are pairwise reachable from each other†, and 0 otherwise.

The number k takes only integer values from 1 to 4 (k = 1,2,3,4). For example, for k = 3, it is necessary to calculate the sum of products ai over all connected triples of vertices in the graph. Help Shustrik tackle this problem and calculate the value of F(Gu) for all boxes. † Two vertices of a graph are considered reachable if there is a path connecting them.

Input

The first line of input contains one integer k (1 ≤ k ≤ 4) — the size of the sets for which F(Gu) needs to be calculated.

The second line of input contains two integers n and m(n,m ≤ 500000) — the number of boxes and the number of vertices in the graph under consideration.

The next line contains n − 1 integers — for all boxes from 2 to n, information about which box this box is nested in pi < i. The following n lines describe the boxes. First, the number e is given — the number of edges in this box. Then follow e pairs of numbers describing the edges u,v (1 ≤ u,v ≤ m). In the last line, m integers ai (0 ≤ ai ≤ 107) are given — the values assigned to the vertices of the graph. It is guaranteed that the sum of values e across all boxes does not exceed 500000.

Output

In one line, output the value of the function F(u) for all u in ascending order of box numbers. Since this number can be very large, output it modulo 232.

Scoring

| Group | Points | Additional Constraints | Required Groups |
| --- | --- | --- | --- |
| 1 | 5 | k = 1, n,m ≤ 1000, e ≤ 2000 | – |
| 2 | 4 | k = 1, n,m ≤ 500000, e ≤ 500000 | 1 |
| 3 | 10 | k = 2, n,m ≤ 1000, e ≤ 2000 | – |
| 4 | 17 | k = 2, n,m ≤ 500000, e ≤ 500000 | 3 |
| 5 | 10 | k = 3, n,m ≤ 1000, e ≤ 2000 | – |
| 6 | 17 | k = 3, n,m ≤ 500000, e ≤ 500000 | 5 |
| 7 | 10 | k = 4, n,m ≤ 1000, e ≤ 2000 | – |
| 8 | 27 | k = 4, n,m ≤ 500000, e ≤ 500000 | 7 |

Examples

| standard input | standard output |
| --- | --- |
| 2 6 6 1 1 3 2 2 2 5 1 3 5 0 1 2 6 2 4 3 5 1 1 1 4 0 1 2 3 4 5 6 | 71 4 29 17 4 0 |
| 1 1 3 3 3 2 3 1 1 3 2 3 1 | 6 |
| 3 4 4 1 1 3 2 2 3 3 2 0 1 3 2 1 4 2 5 3 6 7 | 126 0 126 0 |
| 4 6 6 1 2 1 1 2 1 4 3 1 3 2 3 3 1 4 3 2 3 0 0 1 2 4 9421632 35415 3345712 8926302 3397495 1 | 390523 2825910272 2825910272 2825910272 0 0 0 |

Note

Consider the first example. A hierarchy of boxes is given, where box 1 is the outer box, and each box u > 1 is nested in box pu. For each box, a set of edges between the vertices of the graph is specified.

For k = 2, the value of the function F(Gu) is equal to the sum of the products of the weights of all pairs of vertices that belong to the same connected component of the graph Gu. The graph Gu is obtained by combining all edges contained in box u and in all boxes nested within it.

Box 6. In box 6 and in all boxes nested within it, there are no edges, so all vertices are isolated and there are no connected pairs.

F(G6) = 0. Box 5. The graph contains one edge (1,4) connecting vertices 1 and 4. The only connected pair contributes 1 · 4 = 4.

Thus,

F(G5) = 4.

Box 4. The graph contains edges (4,3) and (5,1). Connected components:

{3,4}, {1,5}. The total contribution is

3 · 4 + 1 · 5 = 12 + 5 = 17, from which it follows that

F(G4) = 17.

Box 2. Box 2 has no edges of its own, but it includes edges from nested box 5, namely (1,4). The only connected pair contributes 1 · 4 = 4, therefore, F(G2) = 4.

Box 3. The graph contains edges (2,6), (4,3), and (5,1). Connected components: {2,6}, {3,4}, {1,5}.

The total contribution is

2 · 6 + 3 · 4 + 1 · 5 = 12 + 12 + 5 = 29, therefore,

F(G3) = 29.

Box 1. The graph contains all edges from all boxes. Connected components:

{1,3,4,5}, {2,6}. The sum over all connected pairs is

(1 · 3 + 1 · 4 + 1 · 5 + 3 · 4 + 3 · 5 + 4 · 5) + (2 · 6) = 59 + 12 = 71. Thus,

F(G1) = 71.

The final values of the function F(Gu) for boxes 1,...,6 are: 71 4 29 17 4 0.

# Citations

1. [Второй отборочный этап — uslovia zadach 2 tur en](https://lk-dovuz.innopolis.university/public/files/uslovia_zadach_2_tur_en.pdf), file a174edf10892

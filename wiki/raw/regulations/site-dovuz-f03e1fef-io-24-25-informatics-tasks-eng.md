---
type: regulation
title: "io 24 25 informatics tasks eng"
resource: "https://lk-dovuz.innopolis.university/public/files/io_24_25_informatics_tasks_eng.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/io_24_25_informatics_tasks_eng.pdf"
    id: "62da90b0a3fa"
    title: "io 24 25 informatics tasks eng"
    last_modified: "2026-11-01T23:17:22+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:22+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# io 24 25 informatics tasks eng

Innopolis Open 2024. Qualification Round 1 Russia, Innopolis, November, 24, 2024

Problem A. CosmoTile

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 256 megabytes

In the year 3030, hamsters decided to improve their spaceship. Specifically, they wanted to lay tiles on the floor.

The floor is square with a side length of a meters. Rectangular tiles will be laid on it, and:

- • the sides of the tiles must be parallel to the sides of the floor;

- • all tiles must be oriented the same way;

- • the tiles will be laid tightly against each other;

- • the first tile will be laid tightly against the “top left” corner of the floor.

For a better understanding of the tile arrangement, see the illustration in the example. The hamsters have at their disposal:

- • a 3D blueprint of the rectangular tile with dimensions a meters by b meters (the thickness is so

small that it can be neglected);

- • a 3D printer that can print any number of tiles;

- • an ultra-thin and ultra-precise laser that can cut tiles without leaving any waste;

- • a reducing laser that can reduce any tile by any integer x times, but the value of x must be at least

1 and at most k;

- • boundless energy to lay the tiles as described above.

The hamsters’ plan is as follows:

- • Choose a number x;

- • Print the minimum necessary number of tiles;

- • Cut some tiles so that using the resulting pieces of tile (considering further reduction) they can

cover the entire floor. Each tile can be cut no more than once, only along a straight line parallel to the side of length a, and if cut at a distance of r meters from the side of length a, two pieces of tile will result: one with dimensions a by r meters and the other with dimensions a by b−r meters. The resulting pieces cannot be cut further;

- • The pieces of tile that will ultimately be laid on the floor should be reduced by x times (that is,

both the length and the width of the piece of tile will be reduced exactly by x times);

- • Lay the tiles as described above.

The hamsters are economical but maintain symmetry in the pattern. Therefore, if cutting a tile into two pieces results in pieces of the same size, both pieces are used (for better understanding, see the illustration in the example when x = 3).

The hamsters have tasked you with choosing x in such a way that the total area of the unused pieces of tile is minimized. What is this minimum total area?

Input

The first line contains the integer a—the length of the side of the floor and the first side of the tile (1 ≤ a ≤ 2 · 106).

The second line contains the integer b—the length of the second side of the tile (1 ≤ b ≤ 2 · 106). The third line contains the integer k—the maximum value of the parameter x for the reducing laser (1 ≤ k ≤ 2 · 1018).

Output

Output a single number—the minimum total area of the unused pieces.

Scoring

| Subtask | Points | Additional Constraints | Required Groups | Comment |
| --- | --- | --- | --- | --- |
| 0 | 0 | – | – | Tests from the statement. |
| 1 | 20 | a,b,k ≤ 200; b — odd | – | – |
| 2 | 15 | a,b,k ≤ 200 | 0–1 | – |
| 3 | 15 | a,b,k ≤ 2000 | 0–2 | – |
| 4 | 20 | k ≤ 2 · 106 | 0–3 | – |
| 5 | 10 | k ≤ 2 · 1012 | 0–4 | – |
| 6 | 20 | — | 0–5 | – |

Examples

| standard input | standard output |
| --- | --- |
| 7 6 4 | 21 |
| 11 8 4 | 0 |

Explanation

Illustration for the first example for all possible x on the next page. x = 1 The side of the small square is 1 The required area is 5 · 7 = 35 x = 3 The side of the small square is

The required area is 3 · 7 = 21 x = 2 The side of the small square is The required area is 4 · 14 = 56

x = 4 The side of the small square is

The required area is 2 · 28 = 56

Note that the size of the small square in the illustration does not affect the required total area, as the reducing laser was not applied to the unused pieces of tile.

Problem B. Exponentiator-2025

Input file: standard input Output file: standard output Time limit: 2 seconds Memory limit: 256 megabytes

You are given an array a1,a2,...,an of positive integers. You have an exponentiator machine that can perform the following two-part operation on the array:

**1.** Shuffle the elements in the array a1,a2,...,an in any order.

**2.** Replace the array a1,a2,...,an with the array aa12,aa23,...,aann−1.

Thus, after each operation, the length of the array decreases by one. The exponentiator will apply n − 1 operations, after which there will be one element left in the array a. This number is called the result of the exponentiator’s work.

It is obvious that the result of the exponentiator’s work is not always uniquely defined. To study the properties of the exponentiator, you need to find answers to q questions of the form: can the result of the exponentiator’s work be divisible by the number x?

Input

The first line of input contains two integers n,q (2 ≤ n ≤ 2·105,1 ≤ q ≤ 2·105) — the length of the array a and the number of queries.

The second line of input contains n integers a1,a2,...,an (1 ≤ ai ≤ 106) — the elements of the array a. The next q lines contain queries, one per line, each query consists of a single number x (1 ≤ x ≤ 106).

Output

For each query, output one line: Yes or No. If the result of the exponentiator’s work can be divisible by x, output Yes, otherwise output No.

Scoring

The tests for this problem consist of eight groups. Points for each group are awarded only if all tests in the group and all tests in some of the previous groups are passed.

| Group | Points | Additional constraints |  | Required Groups | Comment |
| --- | --- | --- | --- | --- | --- |
| Group | Points | n,q | x | Required Groups | Comment |
| 0 | 0 | – | – | – | Tests from the statement. |
| 1 | 10 | n = 2 | – | – | – |
| 2 | 11 | n = 3 | – | – | – |
| 3 | 12 | n = 4 | – | – | – |
| 4 | 9 | n · q = 106 | x is square-free | – | – |
| 5 | 12 | n · q = 106 | – | 4 | – |
| 6 | 16 | – | x is square-free | 4 | – |
| 7 | 30 | – | – | 0-6 | – |

1A square-free number is a number that is not divisible by the square of any prime number. For example, 6 and 10 are square-free numbers, while 4 (divisible by 22) and 18 (divisible by 32) are not.

Examples

| standard input | standard output |
| --- | --- |
| 3 2 2 2 1 16 5 | Yes No |
| 7 20 1 2 3 4 5 6 7 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 | Yes Yes Yes Yes Yes Yes Yes Yes Yes No No Yes No No No Yes No Yes No No |

Problem C. Bunny 3.1

Input file: standard input Output file: standard output Time limit: 0.75 seconds Memory limit: 192 megabytes

The bunny stands in front of a staircase with n steps. The steps are numbered from 1 to n, and we can assume that the bunny is on step number 0. For better understanding, refer to the illustration in the example.

At a time, the bunny can only jump over a “beautiful” number of steps. The bunny considers a number of steps beautiful only if its representation in ternary (base 3) does not contain the digit 1. The bunny cannot jump backwards.

For example, the bunny can jump over 0 steps and thus move up one step, since 010 = 03 and the digit 1 was not used in the ternary representation of the number, or jump over 8 steps and move up nine steps (810 = 223), but not over 7 steps (710 = 213).

How many ways can the bunny reach the top (the n-th step)?

Input

The first line of input contains a single integer n (1 ≤ n ≤ 2 · 106).

Output

Output a single number—the number of ways to reach the top. Since this number can be very large, output it modulo 998244353.

Scoring

| Subtask | Points | Additional Constraints | Required Groups | Comment |
| --- | --- | --- | --- | --- |
| 0 | 0 | – | – | Tests from the statement. |
| 1 | 30 | n ≤ 2000 | 0 | – |
| 2 | 15 | n ≤ 2 · 104 | 0–1 | – |
| 3 | 15 | n ≤ 2 · 105 | 0–2 | – |
| 4 | 25 | n ≤ 106 | 0–3 | – |
| 5 | 15 | — | 0–4 | – |

Examples

| standard input | standard output |
| --- | --- |
| 7 | 10 |
| 5 | 4 |
| 10 | 36 |

Explanation

The illustration for the first example is on the next page. In this example, jumps could be made over 010 = 03, 210 = 23, and 610 = 203 steps.

Illustration for the first example

Problem D. Metro Repair

Input file: standard input Output file: standard output Time limit: 2 seconds Memory limit: 512 megabytes

The metro station has been closed for m days for repair work. You are responsible for organizing the work at the station.

There are a total of n planned tasks that can be completed within the allotted time. According to the workers’ estimates, the i-th task can take any number of days from li to ri. Since all tasks are technically complex and estimating their execution time is very difficult, it is guaranteed that ri li ≥ α for all i from

1 to n.

Your task is to create a repair plan: select some subset of tasks to complete. To avoid being fired for inefficient allocation of labor resources, the following conditions must be met:

- • You must ensure that all tasks can be completed within m days. In other words, the inequality

ri1 + ri2 + ... + rik ≤ m must hold, where i1,i2,...,ik are the indices of the tasks you have chosen to complete.

- • Let d be the number of days remaining until the station opens after all tasks have been completed.

Then there should not exist any uncompleted j-th task that could be guaranteed to be completed within d days. Formally, for all j, the inequality m − (li1 + li2 + ... + lik) < rj must hold, where i1,i2,...,ik are the indices of the tasks you have chosen to complete, and j is the index of the task that is not chosen for completion.

You want to know how many subsets of tasks exist that can be selected to satisfy both of these conditions. Since the answer can be quite large, find the remainder when divided by 109 + 7.

Input

The first line contains two integers n and m — the number of tasks and the total time for repair work (1 ≤ n ≤ 5 · 105, 1 ≤ m ≤ 109).

The second line contains a real number α — the parameter for estimating tasks (1.5 ≤ α ≤ 2). Each of the following n lines contains a pair of numbers li, ri (1 ≤ li ≤ ri ≤ m). It is guaranteed that ri li ≥ α.

Output

In a single line, output the number of possible subsets of tasks to be completed modulo 109 + 7.

Innopolis Open 2024. Qualification Round 1 Russia, Innopolis, November, 24, 2024 Scoring

| Group | Points | Additional Constraints |  | Necessary Groups | Comment |
| --- | --- | --- | --- | --- | --- |
| Group | Points | n | α | Necessary Groups | Comment |
| 0 | 0 | – | – | – | Tests from the statement. |
| 1 | 12 | n ≤ 18 | α = 1.5 | 0 | – |
| 2 | 13 | n ≤ 25 | α = 1.5 | 0–1 | – |
| 3 | 15 | n ≤ 2000 | α = 2 | – | – |
| 4 | 15 | n ≤ 2000 | α = 1.5 | 0–2 | – |
| 5 | 10 | – | α = 2 | 3 | – |
| 6 | 16 | n ≤ 105 | α = 1.5 | 0–2, 4 | – |
| 7 | 19 | – | α = 1.5 | 0–2, 4, 6 | – |

Examples

| standard input | standard output |
| --- | --- |
| 4 10 1.5 2 3 1 2 2 5 3 7 | 1 |
| 7 20 2 1 3 2 4 6 12 9 20 5 12 5 13 6 13 | 2 |

Explanation

In the first example, the only suitable subset consists of the first three tasks.

Problem E. MAX MEX MEX

Input file: standard input Output file: standard output Time limit: 3.5 seconds Memory limit: 256 megabytes

The hamster Ilnur gifted Alice k baskets with numbers. Each basket has a number ci written on it. Alice can perform the following action several times (possibly zero):

**1.** Choose i such that ci > 0.

**2.** Choose exactly one number from the i-th basket.

**3.** Increase the chosen number from the i-th basket by 1, and decrease the number ci by 1.

This means that in the i-th basket, this action can be performed no more than ci times. Alice likes the sequence 0,1,2,.... For each basket, she can calculate the smallest missing element needed to continue such a sequence. More specifically, Alice can find MEX† in each basket. Alice became curious—what is the maximum value of MEX of all MEX that can be obtained by performing several (possibly zero) of the above actions? Note the constraint on k and ni in the last subgroup. †MEX (minimum excluded) of an array is the smallest non-negative integer that does not belong to the array. For example:

MEX of the array [2,2,1] is 0, since 0 does not belong to the array.

MEX of the array [3,1,0,1] is 2, since 0 and 1 belong to the array, but 2 does not. MEX of the array [0,3,1,2] is 4, since 0, 1, 2, and 3 belong to the array, but 4 does not. Input The first line of input contains three numbers—k (1 ≤ k ≤ 105), s (1 ≤ s ≤ 106), t (1 ≤ t ≤ 2). The following 2 · k lines contain the description of the baskets with numbers. The description of each basket depends on the value of t and looks as follows:

For t = 1: The first line contains two numbers—ni (0 ≤ ni ≤ s, ni = s, i.e., the sum ni = s), ci (0 ≤ ci ≤ 1012). The second line contains ni numbers aij (−106 ≤ aij ≤ 106)—the contents of the i-th basket.

For t = 2: The first line contains two numbers—ni (0 ≤ ni ≤ s, ni = s), ci (0 ≤ ci ≤ 1012).

The second line contains 2·ni numbers—ni pairs of numbers aij (−106 ≤ aij ≤ 106) bij (1 ≤ bij ≤ 106)—the contents of the i-th basket.

Here, bij indicates that the number aij is repeated bij times. Note that if ni = 0, the next line will be empty.

Output

Output a single number—MAX(MEX(MEX)) of all baskets with numbers after performing the necessary actions.

The tests for this problem consist of nine groups. Points for each group are awarded only if all tests of the group and all tests of some of the previous groups are passed.

| Subtask | Points | Additional Constraints | Required Groups | Comment |
| --- | --- | --- | --- | --- |
| 0 | 0 | – | – | Tests from the statement. |
| 1 | 10 | t = 1,ni ≤ 15,k ≤ 1000 | – | – |
| 2 | 10 | t = 1,ci = 0 | – | – |
| 3 | 15 | t = 1,aij are distinct in one basket | – | – |
| 4 | 35 | t = 1 | 1–3 | – |
| 5 | 30 | t = 2,k ≤ 1000,s ≤ 3 · 104 | – | – |

Examples

| standard input | standard output |
| --- | --- |
| 4 5 2 1 5 -4 1 1 0 -1000000 1000000000 1 3 0 3 2 100 10 3 -4 2 | 4 |
| 4 8 1 1 5 -4 0 10 3 3 0 0 0 4 1000000000000 100 -1000000 -1 957 | 4 |

Note

In the first set of input data, Alice can perform the following actions:

Basket 1 [−4] ⇒ [−3] ⇒ [−2] ⇒ [−1] ⇒ [0].

Basket 2 is empty [].

Basket 3 [0,0,0] ⇒ [0,0,1] ⇒ [0,1,1] ⇒ [0,1,2]

Basket 4 [100,−1000000,−1,957] ⇒ ... ⇒ [100,0,1,957] Then MEX1 = 1,MEX2 = 0,MEX3 = 3,MEX4 = 2. Thus, MEX([MEX1,MEX2,MEX3,MEX4]) = MEX([1,0,3,2]) = 4. In the second set of input data, Alice can perform the following actions:

Basket 1 [−4] ⇒ [−3] ⇒ [−2] ⇒ [−1] ⇒ [0].

Basket 2 [−1000000,−1000000,...,−1000000] will remain unchanged.

Basket 3 [0,0,0] ⇒ [0,0,1] ⇒ [0,1,1] ⇒ [0,1,2]

Basket 4 [10,10,10,−4,−4] ⇒ ... ⇒ [10,10,10,0,1] Then MEX1 = 1,MEX2 = 0,MEX3 = 3,MEX4 = 2. Thus, MEX([MEX1,MEX2,MEX3,MEX4]) = MEX([1,0,3,2]) = 4.

# Citations

1. [io 24 25 informatics tasks eng](https://lk-dovuz.innopolis.university/public/files/io_24_25_informatics_tasks_eng.pdf), file 62da90b0a3fa

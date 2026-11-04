---
type: regulation
title: "Первый отборочный этап — contest-30457-en"
resource: "https://lk-dovuz.innopolis.university/public/files/contest-30457-en%282%29.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/contest-30457-en%282%29.pdf"
    id: "45fc8bb8d038"
    title: "Первый отборочный этап — contest-30457-en"
    last_modified: "2026-11-01T23:17:20+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:20+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Первый отборочный этап — contest-30457-en

Innopolis Open 2022-2023 First qualification round Russia, Innopolis, October 23, 2022

Information

Memory limit

The limit is 512 MiB for each problem.

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

Problem A. Lebron and the multiverse

Input file: standard input Output file: standard output Time limit: 1 second Memory limit: 512 megabytes

Lebron is so good at basketball that he started traveling across the multiverse to play their version of basketball. Lebron in the universe «42» has already played a match in which he scored r three-point and t two-point shots. Unfortunately, in this world, if a player scores more than or equal to k points during the game, then k points are subtracted from his result until the number of points scored is less than k.

Lebron is confused in calculations, help him count the number of points scored in this universe.

Input

The first line contains one integer r (0 ≤ r ≤ 1017) — the number of three-point shots scored. The second line contains one integer t (0 ≤ t ≤ 1017) — the number of two-point shots scored. The third contains a single integer k (1 ≤ k ≤ 1017) — the number of points deducted from Lebron’s result during the game. Note that the input data and the answer can be quite large, so you should use a 64-bit data type, for example long long in C/C++, long in Java, int64 in Pascal.

Output

Print the total number of points scored by Lebron.

Scoring

Points for each subtask are awarded only if all tests for this subtask and the required subtasks are successfully passed.

| Subtask | Score | Constraints | Required subtasks |
| --- | --- | --- | --- |
| 0 | 0 | Sample tests |  |
| 1 | 25 | 0 ≤ t,r ≤ 100, 1 ≤ k ≤ 100 |  |
| 2 | 25 | 0 ≤ t,r ≤ 1012, 106 ≤ k ≤ 1012 | 1 |
| 3 | 50 | No additional constraints | 1, 2 |

Example

| standard input | standard output |
| --- | --- |
| 6 5 7 | 0 |

Problem B. Lebron and the problem

Input file: standard input Output file: standard output Time limit: 2 seconds Memory limit: 512 megabytes

Lebron knows that basketball — is a very intellectual game, so to play it well, you need to train your mind. One day he came across a very interesting problem.

There is a rectangle with a width of n and a height of m units. At the point (0;0) is the lower-left corner of the rectangle. It is necessary to find the number of triangles in which one of the sides is parallel to the Ox axis, and the second is parallel to the Oy axis. Also, these triangles should only be inside the rectangle(It is acceptable that the sides of the rectangle contain the vertices of triangles).

Lebron was able to solve this problem, but can you?

Input

The first line contains a single integer n (1 ≤ n ≤ 103) — the width of the rectangle. The second line contains one integer m (1 ≤ m ≤ 103) — the height of the rectangle.

Output

Print one number — the number of triangles that match the condition of the problem. Note that the input data and the answer can be quite large, so you should use a 64-bit data type, for example long long in C/C++, long in Java, int64 in Pascal.

Scoring

Points for each subtask are awarded only if all tests for this subtask and the required subtasks are successfully passed.

| Subtask | Score | Constraints | Required subtasks |
| --- | --- | --- | --- |
| 0 | 0 | Sample tests |  |
| 1 | 30 | 1 ≤ n,m ≤ 10 |  |
| 2 | 30 | 1 ≤ n,m ≤ 50 | 1 |
| 3 | 40 | No additional constraints | 1, 2 |

Examples

| standard input | standard output |
| --- | --- |
| 1 1 | 4 |
| 2 2 | 36 |
| 2 4 | 120 |

Note

Explanation for example 1

Problem C. Gift to Lebron

Input file: standard input Output file: standard output Time limit: 2 seconds Memory limit: 512 megabytes

After winning the match, Lebron received as a gift an array of integers a of length n. Lebron wanted for each prefix of length i(1 ≤ i ≤ n) find out if there are exactly two different elements in it that occur the same number of times.

The prefix of an array of length i is the first i elements of this array.

Input

The first line contains a single integer n (1 ≤ n ≤ 105) — the number of elements in the array. The second line contains n integers ai (1 ≤ ai ≤ 105) — elements of the array.

Output

For each prefix of the array, print YES if there are exactly two different elements on this prefix that occur the same number of times, otherwise print NO.

Scoring

| Subtask | Score | Constraints | Required subtasks |
| --- | --- | --- | --- |
| 0 | 0 | Sample tests | — |
| 1 | 25 | 1 ≤ n ≤ 100, 1 ≤ ai ≤ 100 | — |
| 2 | 15 | 1 ≤ n ≤ 105, 1 ≤ ai ≤ 2 | — |
| 3 | 25 | 1 ≤ n ≤ 1000, 1 ≤ ai ≤ 1000 | 1 |
| 4 | 35 | No additional constraints | 1, 2, 3 |

Examples

| standard input | standard output |
| --- | --- |
| 5 1 2 1 2 3 | NO YES NO YES YES |
| 6 1 2 3 4 4 3 | NO YES NO NO NO YES |

Problem D. Lebron and dominoes

Input file: standard input Output file: standard output Time limit: 2 seconds Memory limit: 512 megabytes

Lebron has n dominoes laid out in a row. Each dice consists of two halves, an integer is written on each of the halves. Lebron can rotate the domino by 180 degrees, i.e. swap halves. He wants to use such actions to get the maximum length of a sequence of consecutive dominoes touching with the same numbers.

Input

The first line contains a single integer n (0 ≤ n ≤ 105) — the number of dominoes.

The following n rows consist of two integers li and ri(1 ≤ li,ri ≤ 105) — the numbers on the left and right half of the domino, respectively.

Output

Print a single integer — the maximum length of a sequence of consecutive dominoes.

Scoring

Points for each subtask are awarded only if all tests for this subtask and the required subtasks are successfully passed.

| Subtask | Score | Constraints | Required subtasks |
| --- | --- | --- | --- |
| 0 | 0 | Sample tests |  |
| 1 | 20 | n ≤ 20 | 0 |
| 2 | 20 | m ≤ li,ri ≤ m + 1(2 ≤ m + 1 ≤ 105) |  |
| 3 | 30 | n ≤ 103 | 0, 1 |
| 4 | 30 | No additional constraints | 0, 1, 2, 3 |

Example

| standard input | standard output |
| --- | --- |
| 3 3 4 5 4 5 6 | 3 |

Note

Explanation of the first example: [3,4], [5,4], [5,6] After turning the second domino: [3,4], [4,5], [5,6]

Problem E. Circles and basketball

Input file: standard input Output file: standard output Time limit: 2 seconds Memory limit: 512 megabytes

Lebron and Westbrook decided to paint the basketball court on a Cartesian plane. It is known that they color only those integer points (x,y) that satisfy at least one of the n inequalities of the form (x − xi)2 + (y − yi)2 ≤ ri2.

Westbrook decided to calculate how many points will be colored in the end. Help him with this task.

Input

The first line contains a single integer n (1 ≤ n ≤ 50) — number of inequalities.

Each of the following n lines contains three integers xi, yi and ri (|xi|,|yi|,|ri| ≤ 104) — coefficients of inequalities.

Output

Print one positive integer — the number of colored points.

Scoring

Points for each subtask are awarded only if all tests for this subtask and the required subtasks are successfully passed.

| Subtask | Score | Constraints | Required subtasks |
| --- | --- | --- | --- |
| 0 | 0 | Sample tests |  |
| 1 | 25 | /xi/,/yi/,/ri/ ≤ 100 |  |
| 2 | 15 | n = 1 |  |
| 3 | 25 | n = 2 |  |
| 4 | 35 | No additional constraints | 1, 2, 3 |

Example

| standard input | standard output |
| --- | --- |
| 3 0 0 2 2 3 1 -1 -3 2 | 29 |

Note

Illustration of colored points by Lebron and Westbrook.

# Citations

1. [Первый отборочный этап — contest-30457-en](https://lk-dovuz.innopolis.university/public/files/contest-30457-en%282%29.pdf), file 45fc8bb8d038

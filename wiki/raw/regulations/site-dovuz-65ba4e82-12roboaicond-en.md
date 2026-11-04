---
type: regulation
title: "Первый отборочный этап. 2 тур — 1-2-roboai-cond en"
resource: "https://lk-dovuz.innopolis.university/public/files/1-2-roboai-cond_en.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/1-2-roboai-cond_en.pdf"
    id: "b1f149fc43cf"
    title: "Первый отборочный этап. 2 тур — 1-2-roboai-cond en"
    last_modified: "2026-11-01T23:17:18+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:18+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Первый отборочный этап. 2 тур — 1-2-roboai-cond en

Innopolis Open in AI and Robotics. Second Qualifying Round. 2023-2024. Russia, December, 24, 2023

Problem A. Triangles

Time limit: 1 second

Today in math class, the teacher gave the following problem to the students. You are given five sticks of different lengths: 1,2,3,4,5. Find the number of ways to choose three different sticks so that they can form a valid triangle. Solve this problem and prove to the math teacher that you can solve combinatorial problems.

In addition, your teacher has offered you several more difficult variations of this problem: when given ten sticks, fifteen sticks, and twenty sticks. In each case, the lengths of the sticks are consecutive natural numbers starting from one. You are required to solve the problem for all cases.

The answer to this problem is four numbers listed separated by spaces: the answer for the set of five sticks, for ten sticks, for fifteen sticks, and for twenty sticks. If you do not know the answer for any of the sets, write zero as the answer. Attach the code or a txt file as the answer to this problem.

No more than four files will be accepted for this problem.

Scoring

Correct answers for the sets will be scored 10, 20, 30, and 40 points respectively.

Problem B. Paper Sheets

Time limit: 1 second

Maria, on the eve of the new year, decided to give cards to her friends. She wants the cards to be of size x × y, where the width is x and the height is y. Maria cuts them out of a sheet of size w by h, all the cards are arranged in one position vertically or horizontally. The sides of the cards must be parallel to the edges of the sheet. Maria wants to know the maximum number of cards she can make.

Input

The first line of the input file contains two integers w and h (1 ≤ w · h ≤ 1018) separated by a space — the dimensions of the sheet of paper.

The second line of the input file contains two integers x and y (1 ≤ x · y ≤ 1018) separated by a space — the dimensions of the card.

Output

Output a single number, the maximum number of cards Maria can make.

Scoring

Points for each subtask are awarded only if all the tests for this subtask and the necessary subtasks are successfully passed.

| Subtask | Points | Constraints | Necessary subtasks | Testing information |
| --- | --- | --- | --- | --- |
| 0 | 0 | Tests from the statement | — | full |
| 1 | 30 | x = 1,y = 1 | — | first error |
| 2 | 30 | x = y | 1 | first error |
| 4 | 40 | No additional constraints | 1 — 2 | first error |

Example

| standard input | standard output |
| --- | --- |
| 3 6 1 2 | 9 |

Note two ways of making cards

Problem C. Basketball Tournament

Time limit: 1 second

In the basketball tournament, there were n teams. Arseny knows how many victories each team has achieved, but he does not know the format of the championship. Arseny has two assumptions about how the competitions took place. The teams played in a round-robin system or an Olympic system.

In the round-robin system, each team played against each other, while in the Olympic system, a participant is eliminated from the tournament after the first loss, based on the outcome of a single game or a series of games between two participants, allowing for the unambiguous determination of the absolute winner. It is necessary to determine which format was used.

Input

The first line of the input file contains an integer n (3 ≤ n ≤ 105) — the number of teams. In each of the following n lines, the name of the team and the number of victories are given. It is guaranteed that there were no tied matches and the total length of the team names does not exceed 3 · 105.

Output

Output Round-robin if the teams played in a round-robin tournament, otherwise output Olympic.

Scoring

The problem has 20 tests, each test is worth 5 points.

Examples

| standard input | standard output |
| --- | --- |
| 3 aba 1 abc 2 rty 0 | Round-robin |
| 4 a 0 b 0 c 1 d 2 | Olympic |

Problem D. Elevator

Time limit: 1 second

Timur has arrived at the final of the IO competition at the Innopolis University. He needs to go up to the floor number n, and he can only enter the elevator on the first floor.

There are two types of elevators in the Innopolis University building:

**1.** The elevator stops only at even floors, excluding the first floor

**2.** The elevator stops only at odd floors

Each elevator can accommodate c people.

There are a total of k elevators initially located on the first floor. Each elevator has a queue of people already lined up, and for each person, we know the floor they need to go to. c people enter each elevator (if the queue length is less than c, then the remaining queue enters). The elevator then goes from the first floor to the highest floor where someone currently in the elevator needs to go, stopping at all intermediate floors where someone in the elevator needs to exit.

After all passengers have exited the elevator, it descends to the first floor without stopping anywhere. People enter the elevator instantly on the first floor.

Timur can choose an elevator and join the queue for that elevator. He has 4 strategies:

**1.** Walk to floor n.

**2.** Join the queue for the elevator going to floor n and ride it.

**3.** Join the queue for the elevator going to floor n − 1, ride it, and go up one floor.

**4.** Join the queue for the elevator going to floor n + 1, ride it, and go down one floor.

The elevator moves one floor in lift_time seconds. If it stops at a floor, the stop lasts h seconds (during this time, all people who want to exit at that floor leave the elevator).

Timur can go up one floor in timur_up_time seconds or go down one floor in timur_down_time seconds. Output the minimum time required for Timur to reach floor n.

Input

The first line of the input file contains two integers k and n (1 ≤ k ≤ 105) separated by a space - the number of elevators and the floor Timur needs to reach.

The second line of the input file contains a single number c (1 ≤ c ≤ 109) - the capacity of the elevators. The third line of the input file contains two integers lift_time and h (0 ≤ lift_time,h ≤ 109) - the time it takes for the elevator to go up or down one floor and the time it takes for people to exit the elevator.

The fourth line of the input file contains two integers timur_up_time and timur_down_time (0 ≤ timur_up_time,timur_down_time ≤ 109) - the time it takes for Timur to go down and up one floor.

The fifth line of the input file contains k integers lift_typei (lift_typei ∈ {1,2}) - the type of each elevator.

Each of the following k lines contains a description of the queues. Each queue is contained in a separate line.

Each line begins with an integer cnti (0 ≤ cnti ≤ 105) - the number of people in the queue for elevator i. Then, cnti positive integers f1,f2,...,fcnti (2 ≤ fj ≤ 108) follow in the line - fj is the floor number needed by the jth person in the queue.

It is guaranteed that the total number of people is not more than 105, and the people in the queue for a specific elevator need a floor of the same parity as the elevator itself.

Output

Output the minimum time required for Timur to reach floor n.

Scoring

Points for each subtask are awarded only if all tests for that subtask and any necessary subtasks are passed successfully.

| Subtask | Points | Constraints | Necessary Subtasks | Testing Information |
| --- | --- | --- | --- | --- |
| 0 | 0 | Tests from the statement | — | full |
| 1 | 15 | k = 1 | — | first error |
| 2 | 15 | k = 2 | — | first error |
| 3 | 15 | h = 0 | — | first error |
| 4 | 15 | timur_up_time = timur_down_time | — | first error |
| 5 | 10 | c = 1 | — | first error |
| 6 | 30 | No additional constraints | 1 — 5 | first error |

Example

| standard input | standard output |
| --- | --- |
| 3 5 3 3 1 4 6 1 1 2 1 4 6 2 4 4 2 4 6 2 3 7 | 14 |

Problem E. Triangles

Time limit: 1 second

Today in math class, the teacher gave the following problem to the students. You are given five sticks of different lengths: 1,2,3,4,5. Find the number of ways to choose three sticks from them such that they can form a triangle.

You found this problem trivial, so you decided to generalize it: given n(1 ≤ n ≤ 109) sticks of different lengths 1,2,...,n. You need to find the number of ways to form a triangle from them. Since the answer can be very large, you need to output it modulo 109 + 7.

Input

The input consists of a single natural number n (1 ≤ n ≤ 109) - the number of sticks.

Output

Output the number of ways to form a triangle modulo 109 + 7 in a single line.

Scoring

Points for each subtask are awarded only if all tests for that subtask and the necessary subtasks are successfully passed.

| Subtask | Points | Constraints | Necessary subtasks | Verification information |
| --- | --- | --- | --- | --- |
| 0 | 0 | Tests from the statement | — | full |
| 1 | 10 | n ≤ 200 | — | first error |
| 2 | 20 | n ≤ 2000 | 1 | first error |
| 3 | 30 | n ≤ 2 · 105 | 1, 2 | first error |
| 4 | 40 | No additional constraints | 1 — 3 | first error |

Examples

| standard input | standard output |
| --- | --- |
| 4 | 1 |
| 6 | 7 |

# Citations

1. [Первый отборочный этап. 2 тур — 1-2-roboai-cond en](https://lk-dovuz.innopolis.university/public/files/1-2-roboai-cond_en.pdf), file b1f149fc43cf

---
type: regulation
title: "Заключительный этап — usloviya en"
resource: "https://lk-dovuz.innopolis.university/public/files/usloviya_en.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/usloviya_en.pdf"
    id: "44caa127c4a3"
    title: "Заключительный этап — usloviya en"
    last_modified: "2026-11-01T23:17:27+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:27+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Заключительный этап — usloviya en

Innopolis Open 2025-2026 Final round Russia, Innopolis, February 14, 2026

Information

Memory limit

Here is the translation:

- • In problem A: 256 megabytes

- • In problem B: 256 megabytes

- • In problem C: 256 megabytes

- • In problem D: 256 megabytes

- • In problem E: 512 megabytes

- • In problem F: 256 megabytes

Source code limit

The size of each solution source code can’t exceed 256 KiB.

Submissions limit

You can submit at most 75 solutions for each problem. You can submit a solution to each task at most once per 30 seconds. This restriction does not apply in the last 15 minutes of the contest round.

Scoring

Each problem consists of several subtasks. The subtask score is awarded if all tests in the subtask are passed.

The number of points scored for the problem is the total number of points scored on each of its subtasks. The score for the subtask is the maximum number of points earned for this subtask among all the solutions submitted.

Feedback

To get feedback for your solution, go to “Runs” tab in PCMS2 Web Client and use “View Feedback” link. In each problem of the contest you will see the score for each subtask, or the verdict for the first failed test.

Scoreboard

The contestants’ scoreboard is available during the contest. Use “Monitor” link in PCMS2 Web Client to access the scoreboard. The standings provided in PCMS2 Web Client are not final.

Problem A. Forgetful Shustrik and the Remote Control

Time limit: 1 second

The hamster Shustrik received an unusual calculator as a gift from the hedgehog Shurshik. Initially, the number A is displayed on the calculator screen.

The instructions for the calculator specify a fixed number M. All arithmetic operations are performed with this number. Additionally, Shurshik has thought of numbers N and B and informed Shustrik about them.

The calculator can perform only four operations, and in one step, one of the following operations can be applied:

- • Operation «+»: replace the current value A with A + M.

- • Operation «-»: replace the current value A with A − M.

- • Operation «*»: replace the current value A with A · M.

- • Operation «%»: replace the current value A with the remainder of the division A by M. After this

operation, the condition 0 ≤ A < M holds.

After performing some (possibly empty) sequence of operations, the number A′ will be obtained. The hedgehog Shurshik became curious whether Shustrik can obtain such a number A′ that

A′ ≡ B (mod N).

In other words, the numbers A′ and B must have the same remainders when divided by N. Your task is to help the hamster find any sequence of operations of the smallest length, after which the specified condition will be satisfied, or determine that it is impossible to obtain such a number.

Input

In a single line, four integers are given separated by spaces: A, M, B, and N (|A| ≤ 109,1 ≤ M ≤ 109,0 ≤ B < N ≤ 2 · 106).

Output

If the desired sequence of operations does not exist, output «-1» in a single line.

Otherwise, in the first line, output the length x of the minimal suitable sequence. In the second line, output a string of length x consisting of the characters «+», «-», «*», and «%» — the sequence of operations that transforms the initial A into such A′ that A′ ≡ B (mod N).

If there are multiple such sequences, output any of them. It can be proven that the length of the answer does not exceed N.

Scoring

Points for each subtask are awarded only if all tests for that subtask and necessary subtasks are successfully passed.

| Group | Points | Additional constraints | Required groups |
| --- | --- | --- | --- |
| 1 | 7 | /A/,M,N ≤ 8 | – |
| 2 | 6 | M = 1 | – |
| 3 | 8 | M = N | – |
| 4 | 12 | M ≡ 0 (mod N) | 3 |
| 5 | 15 | N ≡ 0 (mod M) | 2–3 |
| 6 | 16 | N · M ≤ 2 · 106 | 1–2 |
| 7 | 18 | A = 0 | – |
| 8 | 18 | – | 1–7 |

Examples

| standard input | standard output |
| --- | --- |
| 1 3 2 5 | 2 +* |
| 6 7 2 4 | 0 |
| -1 3 2 4 | 1 + |
| 5 6 1 6 | -1 |
| 0 6 3 7 | 3 --- |
| 5 9 1 8 | 3 *%+ |

Note

Consider the answer to the first example of the input data:

- • Initially, A = 1.

- • Operation «+»: replace A with A + 3 = 1 + 3 = 4.

- • Operation «*»: replace A with A · 3 = 4 · 3 = 12.

- • We get A′ = 12. At the same time, A′ ≡ B (mod N) holds true, since 12 ≡ 2 (mod 5).

It can be proven that in this example there is no sequence of zero or one operation that results in a suitable A′. A sequence of two operations «++» is also suitable: 1 + 3 + 3 = 7 ≡ 2 (mod 5).

Problem B. Grand Renaming

Time limit: 2 seconds On the monorail line, there are n stations, numbered in order from 1 to n. Each station i has a name si — a string of no more than 20 Latin letters. Each letter is written on a separate nameplate.

As part of the urban infrastructure upgrade project, it was decided to rename all the stations to some new names. The order for renaming has already been signed and will take effect tomorrow. However, there is a problem: no one has had time to replace the names on the nameplates at the stations. Now it is your task.

Unfortunately, there is no time to make new nameplates. Therefore, the only possible option is to move the nameplates from one station to another.

Formally, in one operation, you can choose two indices 1 ≤ i,j ≤ n, as well as any letter from the string si, and move that letter to any position in the string sj. This operation takes 1 + |i − j| precious units of time.

For example, if si = ab and sj = cd, then in one operation of moving a letter from i to j, you can do:

- • si = a; sj = bcd or sj = cbd or sj = cdb.

- • si = b; sj = acd or sj = cad or sj = cda.

Note that it is also allowed to choose i = j in the operation.

You need to replace the nameplates with names at each station as quickly as possible so that they correspond to the new names. Determine whether this is possible, and if so, the minimum necessary amount of time.

Input

The first line of the test contains a single integer n (1 ≤ n ≤ 105) — the number of stations on the line. The second line of the test contains n strings: s1,s2,...,sn (1 ≤ |si| ≤ 20) — the original names of the stations. The third line of the test contains n strings: t1,t2,...,tn (1 ≤ |ti| ≤ 20) — the desired new names of the stations. It is guaranteed that all strings in the test consist of lowercase Latin letters, characters from ’a’ to ’z’.

Output

If there is no way to rename all the stations, output −1 in a single line. Otherwise, output a single number: the minimum possible total time required for the renaming operations.

Scoring

| Group | Points | Additional constraints | Required groups |
| --- | --- | --- | --- |
| 1 | 14 | n = 1 | – |
| 2 | 17 | sorted(si) = sorted(ti) | – |
| 3 | 25 | si and ti have no common letters | – |
| 4 | 13 | n ≤ 1000;/si/,/ti/ ≤ 10 | – |
| 5 | 11 | /si/ = 1, /ti/ = 1 | – |
| 6 | 11 | All strings consist of the letter a | – |
| 7 | 9 | – | 1–6 |

Here, sorted(si) denotes the string si sorted in alphabetical order. For example, sorted(abacaba) = aaaabbc

Examples

| standard input | standard output |
| --- | --- |
| 3 no iislop nepon inno polis open | 10 |
| 3 eleven plus two twelve plus one | 12 |
| 1 evil live | 3 |
| 2 a b ba ab | -1 |
| 2 indian cat init canada | -1 |
| 4 aaaa aaa aa a a aa aaa aaaa | 14 |
| 7 s e a s i d e d i s e a s e | 22 |

Problem C. Olympiad Schedule

Time limit: 1.5 seconds

Persik — a shark in the world of programming — decided to create a schedule for all tracks of the Innopolis Open olympiad.

There are D days in the academic year, numbered from 1 to D. In total, n olympiads are held.

The olympiads are numbered from 1 to n in non-decreasing order of their initially scheduled dates. Each olympiad takes place on exactly one day. For each olympiad, its initially scheduled date and its benefit for the younger generation are known.

You may change the date of any olympiad, but only to a later day within the same academic year (that is, the new date cannot be earlier than the original one and cannot exceed D).

After all changes, the olympiads must remain in non-decreasing order of their scheduled dates.

The total benefit of the olympiad season is defined as follows. For each day, consider all olympiads scheduled on that day. If at least one olympiad is scheduled on a given day, the benefit of that day is the maximum benefit among those olympiads. If no olympiads are scheduled on that day, the benefit of that day is 0.

The benefit of the season is the sum of the benefits over all D days. For the benefit of the students, determine the maximum possible total benefit of the season.

Input

The first line contains three integers n, D, and t — the number of olympiads and the number of days in the academic year, as well as the type of answer (1 ≤ n ≤ 3 · 105; 1 ≤ D ≤ 2 · 109; 1 ≤ t ≤ 2).

In the i-th of the following n lines, two integers di and bi are given — the scheduled date (day number) of the i-th olympiad and its benefit (1 ≤ di ≤ D; 1 ≤ bi ≤ 2 · 109).

It is guaranteed that di ≤ dj for all i and j such that i < j.

Output

If t = 1, output a single integer — the maximum possible benefit of the olympiad season.

If t = 2, then in the first line output a single integer — the maximum possible benefit of the olympiad season; and in the second line output the schedule of the olympiads — n integers, where the i-th is the final date of the i-th olympiad. The specified final dates must achieve the maximum possible benefit of the olympiad season. Scoring

The tests for this problem consist of thirteen groups. Points for each group are awarded only if all tests of the group and all tests necessary for it are passed.

| Group | Points | Additional constraints | Necessary groups |
| --- | --- | --- | --- |
| 1 | 10 | n,D ≤ 20; bi ≤ 20 for all i; t = 1 | – |
| 2 | 7 | n,D ≤ 20; bi ≤ 20 for all i | 1 |
| 3 | 11 | n,D ≤ 100; bi ≤ 100 for all i | 1, 2 |
| 4 | 9 | n,D ≤ 800; bi ≤ 800 for all i | 1, 2, 3 |
| 5 | 5 | n,D ≤ 2500; bi ≤ 2500 for all i; t = 1 | 1 |
| 6 | 4 | n,D ≤ 2500; bi ≤ 2500 for all i | 1–5 |
| 7 | 5 | bi = bj for all i, j | – |
| 8 | 5 | di = dj for all i and j, such that i = j | – |
| 9 | 5 | di = 1 for all i; t = 1 | – |
| 10 | 5 | di = dj for all i, j | 9 |
| 11 | 8 | D ≤ 2 · 106 | 1–6 |
| 12 | 10 | t = 1 | 1, 5, 9 |
| 13 | 16 | – | 1–12 |

̸ ̸

Examples

| standard input | standard output |
| --- | --- |
| 3 10 1 1 3 1 5 1 2 | 10 |
| 3 10 2 1 3 1 5 1 2 | 10 1 2 3 |
| 5 6 2 1 7 2 6 5 8 5 9 6 4 | 30 1 3 5 6 6 |

Note

Note that the answer for the second test will not be suitable as an answer for the first, as for t = 1 only one number needs to be output.

In the second example, the benefit of the first day is 3, the benefit of the second is 5, the third is 2, and the benefits of days from the 4th to the 10th are 0. Thus, the benefit of the olympiad season is

3 + 5 + 2 + 0 + ... + 0 = 10. Note that the schedule of olympiads [2,1,3] is not possible, as the olympiads must remain in non-decreasing order of their scheduled dates.

In the third example, a schedule of olympiads [1,2,5,6,6] is also suitable, but [1,2,3,5,6] is not suitable, as the third olympiad cannot take place before the 5th day

Problem D. Tower of Boxes

Time limit: 2 seconds This is an interactive problem.

Cyber-shark Zubastik† works in a warehouse and stacks boxes into a single vertical tower. The height of the tower is unlimited, but the shark can only remove and place the top box on the tower. There is also a buffer nearby — a free area where boxes can be temporarily held (any number of boxes can be in the buffer).

Boxes are numbered in the order they arrive, starting from 1. For each box, the moment in time tj when it needs to be extracted from the warehouse is known.

During the work, there are two types of events:

- • + t — a new box has arrived, which needs to be extracted at time t (1 ≤ t ≤ T). All values of t are

distinct.

- • - j — the moment tj has arrived, and box number j needs to be extracted.

Actions. During the processing of an event, the shark can perform the following operations:

- • 1 j — place box j on top of the tower (allowed only if box j is in the buffer).

- • 2 j — place box j in the buffer (allowed only if box j is on top of the tower).

Rules for processing events.

- • At the event + t, the new box is immediately placed in the buffer. By the end of processing this

event, the buffer must be empty.

- • At the event - j, by the end of processing this event, there must be exactly one box left in the

buffer — box j. After this, box j is considered extracted and removed from the system.

Your task is to output a set of operations for each event that correctly processes that event. † see fig.

Cyber-shark Zubastik

Input

The first line contains T — the number of moments in time to consider. In the i-th of the subsequent T lines, the description of the next event occurring at time i is given in the following format:

- • + t — a new box has arrived, which needs to be removed at time t (1 ≤ t ≤ T). (Boxes are numbered

in the order of arrival). After processing this event, the buffer must be empty.

- • - j — it is time to extract box j. After processing this event, box j must remain in the buffer.

Output

For each event, you need to output a sequence of operations that will process it. First, an integer K — the number of operations. Then a list of K operations — for each, two numbers:

- • The type of operation (1 or 2).

- • Then the number of the box with which the operation is performed.

The total number of operations output across all events must not exceed 106. If this limit is violated, the solution will receive a verdict of Wrong Answer.

Interaction Protocol

First, your program must read an integer T — the number of events. Then for each i = 1,2,...,T, the interactor outputs a line with the description of the event occurring at time i:

- • + t — a new box has arrived, which needs to be extracted at time t (1 ≤ t ≤ T). The box receives

the next sequential number. By the end of processing the event, the buffer must be empty.

- • - j — box j needs to be extracted. By the end of processing this event, exactly one box j must

remain in the buffer.

After receiving the next event, your program must output the response for it in the following format:

- • In the first line, an integer K — the number of operations to process the current event;

- • Then K lines, each with two integers: the type of operation (1 or 2) and the number of box j.

To receive the next event, you must output a correct response for the current event and end the line with a newline character.

After outputting the response, be sure to flush the output buffer:

- • fflush(stdout) or cout.flush() in C++;

- • System.out.flush() in Java;

- • flush(output) in Pascal;

- • stdout.flush() in Python.

Note that for faster output, it is advisable to call flush (or endl) after outputting all K operations, rather than after each operation.

The interactor in this problem is non-adaptive: within a single test, the sequence of events is fixed and does not change based on your responses.

Scoring

In this problem, there are two types of tests.

The first type of test — an array [1, 1, 2, 2, ..., N, N] is generated and shuffled randomly, resulting in an array [a1,a2,...,aT] of size T, where T = 2N. A box is added at time t1 and taken out at time t2, if t1 < t2 and a[t1] = a[t2].

The second type of test — it is guaranteed that the boxes are taken out in the same order they are added. For each value of N (the number of boxes), one test of each type is generated.

| Group | Tests | Values of N | Points | Cumulative Sum | Dependencies |
| --- | --- | --- | --- | --- | --- |
| 1 | 1-2 | Tests from the statement | 0 per test | 0 | - |
| 2 | 3-10 | 100, 200, 330, 420 | 1 per test | 8 | - |
| 3 | 11-18 | 480, 720, 820, 1080 | 1 per test | 16 | 1 |
| 4 | 19-26 | 1240, 1420, 1630, 1870 | 1 per test | 24 | 1-2 |
| 5 | 27-30 | 2150, 2470 | 1 per test | 28 | 1-3 |
| 5 | 31-34 | 2840, 3260 | 2 per test | 36 | 1-3 |
| 6 | 35-42 | 3740, 4300, 4940, 5680 | 2 per test | 52 | 1-4 |
| 7 | 43-50 | 6530, 7500, 8620, 9910 | 2 per test | 68 | 1-5 |
| 8 | 51-58 | 11390, 13090, 15050, 17300 | 2 per test | 84 | 1-6 |
| 9 | 59-66 | 17500, 18000, 18500, 19000 | 2 per test | 100 | 1-7 |

Examples

| standard input | standard output |
| --- | --- |
| 4 + 3 + 4 - 1 - 2 | 1 1 1 3 2 1 1 2 1 1 1 2 1 1 2 2 |
| 8 + 8 + 3 - 2 + 7 + 6 - 4 - 3 - 1 | 1 1 1 1 1 2 1 2 2 1 1 3 1 1 4 1 2 4 1 2 3 1 2 1 |

Problem E. Cheng Shi and the Collection of Bamboo

Inscriptions

Time limit: 2 seconds

Elephant Filimon decided to visit his panda-friend Cheng Shi from Chengdu, China. Cheng Shi loves bamboo and showed her collection of bamboo inscriptions. Each inscription is a string of lowercase Latin letters.

Cheng Shi’s collection is a dynamic multiset of strings. Initially, it is empty. The panda can perform operations of two types:

- • + s — add the string s to the multiset.

- • - s — remove one copy of the string s from the multiset.

Elephant Filimon became curious about the minimum number of actions required after each operation to make all strings in the current multiset identical.

Allowed actions on one string from the collection:

**1.** Remove the last character of the string — Cheng Shi carefully bites off a piece of bamboo.

**2.** Add any character to the end of the string — the panda plants bamboo, and it grows, adding one character to the end.

An unlimited number of actions can be performed on each string (bamboo). The string to which all others are brought can be any (including empty) and does not have to be present in the multiset.

Note: The strings in the multiset are not actually changed. After each query, it is only necessary to compute the minimum number of actions required to make all strings identical. For subsequent operations, the multiset remains unchanged.

Help Cheng Shi quickly respond to Filimon’s question after each change.

Input

The first line contains a single integer q (1 ≤ q ≤ 5 · 105) — the number of operations. Each of the following q lines describes one operation and has the form:

+ s or - s where s is a non-empty string consisting of lowercase Latin letters.

- • The operation + s means adding the string s to the multiset.

- • The operation - s means removing one copy of the string s from the multiset. It is guaranteed that

the string s is present in the multiset at the time of removal.

In all queries, 1 ≤ |s| ≤ 5 · 105. The total length of all strings in all operations does not exceed 5 · 105.

Output

After each operation, output a single integer — the minimum number of actions required to make all strings in the current multiset identical.

If the multiset is empty after the operation, output 0.

Innopolis Open 2025-2026 Final round Russia, Innopolis, February 14, 2026 Scoring

| Subgroup | Points | Additional constraints |  |  | Required subgroups |
| --- | --- | --- | --- | --- | --- |
| Subgroup | Points | q | /si/ | Type of operations | Required subgroups |
| 1 | 10 | q ≤ 100 | /si/ ≤ 1000 | + and - | – |
| 2 | 10 | q ≤ 1000 | /si/ ≤ 104 | + and - | 1 |
| 3 | 15 | q ≤ 50000 | /si/ ≤ 105 | + and - | 1,2 |
| 4 | 10 | q ≤ 5 · 105 | /si/ ≤ 5 · 105, /si/ ≤ 10 | + | – |
| 5 | 10 | q ≤ 5 · 105 | /si/ ≤ 5 · 105, /si/ ≤ 10 | + and - | 4 |
| 6 | 20 | q ≤ 5 · 105 | /si/ ≤ 5 · 105 | + | 4 |
| 7 | 25 | – | – | + and - | 1–6 |

Example

| standard input | standard output |
| --- | --- |
| 5 + abc + ab + a - ab + b | 0 1 2 2 4 |

Problem F. Nimesweeper!

Time limit: 3 seconds

Alexander and Babin live on an abandoned island. Their only entertainment consists of trees, stones, and bombs (don’t ask where they came from). They are very bored and want to play a game. Alexander suggested playing "Minesweeper while Babin suggested "Nim". As a compromise, they decided to play Nimesweeper!

With no other choice, the guys chose a tree as the game board. Recall that a tree is a connected undirected graph without cycles.

In the course of the overall game, Alexander starts playing the subgame "Minesweeper". Initially, none of the vertices of the tree contain bombs. On his turn, Alexander chooses any vertex without a bomb and places a bomb in it. After that, in each vertex that does not contain a bomb, a number of stones equal to the number of bombs in its neighboring vertices is placed.

Babin can interrupt Alexander after any of his moves. Once this happens, they start playing "Nim"with the resulting piles of stones, with Babin going first.

If Babin does not interrupt Alexander, Alexander makes the next move (places another bomb), after which the piles of stones are updated, and so on, until Babin starts the game of "Nim".

The player who cannot make a move in "Nim"loses. Babin really wants to win, so he will interrupt Alexander at the earliest possible moment when he can guarantee his victory.

Alexander, well aware that he cannot win this game, decided instead to maximize his enjoyment, so he wants to place as many bombs as possible before Babin starts the game of "Nim". Please help Alexander find the maximum number of bombs he can place!

Recall that in the game of "Nim the first player wins if and only if the bitwise XOR of the sizes of the piles is non-zero.

Recall that XOR or Exclusive OR is a binary operation that is applied to each pair of bits in the same position in the binary representations of numbers such that the result at that position is 0 if the bits are equal, and 1 otherwise. For example, 3 XOR 5 = 6, since 310 = 0112, 510 = 1012, and therefore after applying the operation, the second and third bits become equal to 1, while the first bit becomes 0, resulting in 1102 = 610.

Input

The first line of the input contains a single integer n (2 ≤ n ≤ 369) — the number of vertices in the tree. The following n − 1 lines contain pairs of integers ai,bi (1 ≤ ai,bi ≤ n) — the edges of the tree. It is guaranteed that these edges indeed form a tree.

Output

In a single line, output a single number — the maximum number of bombs that can be placed.

| Group | Points | Additional Constraints | Required Groups |
| --- | --- | --- | --- |
| 1 | 8 | n ≤ 8 | – |
| 2 | 11 | n ≤ 18 | 1 |
| 3 | 20 | n ≤ 45 | 1–2 |
| 4 | 19 | n ≤ 128 | 1–3 |
| 5 | 18 | n ≤ 243 | 1–4 |
| 6 | 20 | Degrees of all vertices ≤ 3 | – |
| 7 | 4 | – | 1–6 |

Examples

| standard input | standard output |
| --- | --- |
| 3 1 2 1 3 | 2 |
| 9 1 2 2 3 3 4 4 5 5 6 6 7 5 8 8 9 | 5 |
| 13 7 6 7 5 7 4 7 3 7 2 7 1 1 12 2 11 3 10 4 9 5 8 6 13 | 8 |

# Citations

1. [Заключительный этап — usloviya en](https://lk-dovuz.innopolis.university/public/files/usloviya_en.pdf), file 44caa127c4a3

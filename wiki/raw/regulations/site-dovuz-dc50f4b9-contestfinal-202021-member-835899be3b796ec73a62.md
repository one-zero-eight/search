---
type: regulation
title: "Финальный этап — contest-final 2020-21 — problems/parking-problem/statements/.pdf/english/problem.pdf"
resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
archive_member: "problems/parking-problem/statements/.pdf/english/problem.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
    id: "46b7dfd9c8dd"
    title: "Финальный этап — contest-final 2020-21 — problems/parking-problem/statements/.pdf/english/problem.pdf"
    last_modified: "2026-11-04T02:52:48+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-04T02:52:48+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Финальный этап — contest-final 2020-21 — problems/parking-problem/statements/.pdf/english/problem.pdf

Parking Problem

Input file: standard input Output file: standard output Time limit: 2 seconds Memory limit: 512 megabytes

Paulina wants to visit the conference in file fragmentation that takes place in Innopolis University, so she has driven her car all the way to Innopolis. The University parking is a line of width n meters where the vehicles are parked in the way that they are parallel to each other. This parking is built for cars and motorcycles. The parking is divided into n zones each of width 1 meter. The drivers and riders are very respectful to each other, so they use the zoning: motorcycles occupy exactly one zone of 1 meter width, and cars occupy exactly two adjacent zones of total width of 2 meters.

Paulina wants to enter the parking area. Currently some of the zones of the parking are occupied by the vehicles. There are also a queue of m vehicles that try to enter the parking area apart from Paulina’s car. All vehicles will enter the parking in the queue order, and will occupy any vacant place: one zone for motorcycle, and two adjacent zones for car. If there is no place for the vehicle, the driver or rider leaves Innopolis, not occupying any zone.

Paulina’s conference presentation time is coming, and as the Innopolis people are very polite, everyone offers Paulina to enter the parking before them, so that she won’t be late for her presentation. Paulina doesn’t want to abuse her position, but she is worried that if she didn’t find a place for her car, she wouldn’t make it to the presentation. As an expert in data fragmentation Paulina understands that people can choose places for their vehicles poorly leaving no place for her car. She could easily understand, when she is supposed to enter the parking area to ensure a place for her car.

You are given which of the n parking zones are occupied. You are also given the queue of m motorcycles and cars apart from Paulina’s car. You are required to compute for each i from 0 to m, will Paulina be able to park her car, if she enters the parking area after the first i vehicles in the queue, no matter what zones they occupy.

Input

You are required to solve several tests. The first line contains single integer t — the number of tests in the input (1 ≤ t ≤ 50000). Then the description of t tests follows. Each of the tests consists of two lines. The first of these two lines consists of n characters ‘.’ and ‘X’, the i-th of which denotes the i-th zone: ‘.’ for vacant, and ‘X’ for occupied (1 ≤ n ≤ 105).

The second of these two lines consists of m uppercase English letters ‘C’ and ‘M’, denoting cars ‘C’, and motorcycles ‘M’ (1 ≤ m ≤ n). The first letter corresponds to the head of the queue, and the last — to the tail.

The total sum of n over all t tests doesn’t exceed 5 · 105.

Output

Print t lines: one line for each test.

The line should contain m + 1 uppercase English letters ‘Y’ and ‘N’, for each i from 0 to m print ‘Y’, if Paulina will be able to find a place for her car, entering after first i vehicles from the queue, no matter which zones they occupy, and ‘N’ otherwise.

Scoring

| Subtask | Score | Constraints |
| --- | --- | --- |
| 1 | 31 | parking has no occupied zones |
| 2 | 22 | at most one zone is occupied on the parking |
| 3 | 23 | the queue consists of motorcycles only |
| 4 | 24 | no additional constraints |

Examples

| standard input | standard output |
| --- | --- |
| 1 X..X MM | YNN |
| 5 ...... MMMC ...... CCCM .X..X. MMM XXXXXX CMMCM ...... MM | YYYNN YYNNN YNNN NNNNNN YYY |

Note

In the first sample Paulina can park her car in two vacant zones, if she enters the parking area before everyone in the queue. Otherwise, one or no vacant zone left, so she won’t be able to park her car.

In the first test of the second sample, after the first three motorcycles enter the parking are, they could park in the following way: “M.M.M.”, then Paulina won’t be able to find two adjacent zones to park her car.

# Citations

1. [Финальный этап — contest-final 2020-21 — problems/parking-problem/statements/.pdf/english/problem.pdf](https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip), file 46b7dfd9c8dd

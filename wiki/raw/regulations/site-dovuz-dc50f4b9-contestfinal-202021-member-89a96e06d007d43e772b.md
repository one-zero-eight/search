---
type: regulation
title: "contest-final 2020-21 — problems/rps-string/statements/.pdf/english/problem.pdf"
resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
archive_member: "problems/rps-string/statements/.pdf/english/problem.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
    id: "84187b8e51da"
    title: "contest-final 2020-21 — problems/rps-string/statements/.pdf/english/problem.pdf"
    last_modified: "2026-11-04T02:52:48+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-04T02:52:48+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# contest-final 2020-21 — problems/rps-string/statements/.pdf/english/problem.pdf

RPS string

Input file: standard input Output file: standard output Time limit: 2 seconds Memory limit: 512 megabytes

The robots battle in rock-paper-scissors takes place in Innopolis. All advanced robots are engaged in full-fledged work, so the simplest bots participate in the battles. Each of them always play the same shape: a rock, or scissors, or a paper.

The robots stand in a line. Then the judge can choose two neighboring robots, and make them play one round of rock-paper-scissors. If one of them beats the other, the loser is eliminated from the game and is removed from the sequence of robots, the sequence of the remaining ones doesn’t change. There are two versions of the rules. In the first of them, if the robots played the same shape, the judge can independently choose which one to remove from the game. In the second version, if the robots played the same shape, both robots remain. The robot wins if all other robots are eliminated from the game.

However, the judge has become very bored with the competition, so he wants to find out for each robot whether the judge can choose pairs in each round so that this robot wins. Help him!

Input

You will need to solve several testcases. The first line contains an integer t (t ≥ 1) — the number of tests in the input. Next, t tests are given, each consisting of an integer and a string. The integer d denotes the version of the rules that is used in the current robot layout d ∈ {1,2}.

Then the string s follows, it contains n (1 ≤ n ≤ 5·105) lowercase English letters ‘r’, ‘p’ and ‘s’, describing the list of robots. More precisely, the characters ‘r’, ‘p’ and ‘s’ denote robots that play rock, paper, and scissors, respectively.

The total sum of n for t given tests does not exceed 5 · 105.

Output

Output t lines: one for each test. The line should contain n digits ‘0’ and ‘1’, for each i from 1 to n print ‘1’ if the judge can choose such pairs for each round that the i-th robot wins, and ‘0’ otherwise.

Scoring

| Subtask | Score | Constraints |
| --- | --- | --- |
| 1 | 7 | d = 1, n ≤ 20 |
| 2 | 9 | d = 1, n ≤ 200 |
| 3 | 10 | d = 1, n ≤ 5000 |
| 4 | 11 | d = 1, n ≤ 5 · 105 |
| 5 | 7 | n ≤ 20 |
| 6 | 13 | n ≤ 200 |
| 7 | 10 | n ≤ 5000 |
| 8 | 33 | n ≤ 5 · 105 |

Example

| standard input | standard output |
| --- | --- |
| 4 1 rpspp 2 pps 1 rpsps 2 rpssprsrr | 10111 001 10101 110010001 |

Note

First test example: “rpspp”, d = 1. Let’s identify the robots with integers from 1 to 5 from left to right.

**1.** In order for the robot 1 to win, the judge can act as follows:

- • The judge chooses robots 4 and 5, they play the same shape, so the judge decides that the 5th

robot is eliminated. Robots {1, 2, 3, 4} remain.

- • The judge chooses robots 2 and 3, the 2nd one is eliminated. Robots {1, 3, 4} remain.

- • The judge chooses robots 3 and 4, the 4th one is eliminated. Robots {1, 3} remain.

- • The judge chooses robots 1 and 3, the 3rd one is eliminated. The robot 1 wins.

**2.** For the robot 2, the judge can’t get rid of the 1st robot without removing the 2nd, so the 2nd can’t win.

**3.** In order for the robot 3 to win, the judge can act as follows:

- • The judge chooses robots 4 and 5, they play the same shape, so the judge decides that the 5th

robot is eliminated. Robots {1, 2, 3, 4} remain.

- • The judge chooses robots 1 and 2, the 1st one is eliminated. Robots {2, 3, 4} remain.

- • The judge chooses robots 2 and 3, the 2nd one is eliminated. Robots {3, 4} remain.

- • The judge chooses robots 3 and 4, the 4th one is eliminated. The robot 3 wins.

**4.** In order for the robot 4 to win, the judge can act as follows:

- • The judge chooses robots 4 and 5, they show the same shape, so the judge decides that the

5th robot is eliminated. Robots {1, 2, 3, 4} remain.

- • The judge chooses robots 2 and 3, the 2nd one is eliminated. Robots {1, 3, 4} remain.

- • The judge chooses robots 1 and 3, the 3rd one is eliminated. Robots {1, 4} remain.

- • The judge chooses robots 1 and 4, the 1st one is eliminated. The robot 4 wins.

**5.** In order for the robot 5 to win, the judge can act as follows:

- • The judge chooses robots 4 and 5, they show the same shape, so the judge decides that the

4th robot is eliminated. Robots {1, 2, 3, 5} remain.

- • The judge chooses the robots 2 and 3, the 2nd one is eliminated. Robots {1, 3, 5} remain.

- • The judge chooses robots 1 and 3, the 3rd one is eliminated. Robots {1, 5} remain.

- • The judge selects robots 1 and 5, the 1st one is eliminated. The robot 5 wins.

Second test example: “pps”, d = 2. Let’s identify the robots with integers from 1 to 3 from left to right.

**1.** For the robot 1 the judge can’t get rid of the 2nd robot without removing the 1st, so the 1st can’t win.

**2.** For the robot 2, the judge can’t get rid of the 1st robot without removing the 2nd, so the 2nd can’t win.

**3.** In order for the robot 3 to win, the judge can act as follows:

- • The judge selects robots 2 and 3, the 2nd one is eliminated. Robots {1, 3} remain.

- • The judge selects robots 1 and 3, the 1st one is eliminated. The robot 3 wins.

# Citations

1. [contest-final 2020-21 — problems/rps-string/statements/.pdf/english/problem.pdf](https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip), file 84187b8e51da

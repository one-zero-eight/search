---
type: regulation
title: "Первый отборочный этап — statements-1 (en)"
resource: "https://lk-dovuz.innopolis.university/public/files/statements-1%20%28en%29.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/statements-1%20%28en%29.pdf"
    id: "6560bebaf39a"
    title: "Первый отборочный этап — statements-1 (en)"
    last_modified: "2026-11-01T23:17:26+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:26+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Первый отборочный этап — statements-1 (en)

Innopolis Open 2020-2021, qualification, contest 1 Russia, Innopolis, November, 22, 2020

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

Problem A. The Battle of Giants

Time limit: 1 second

The famous programming contest organizer decided to hold competition for champions “The Battle of Giants”. There are two teams competing in the battle. Several matches are organized for the competition.

Each match can end with a win for one of the teams, or with a draw. When a team wins the match it scores 3 points, in this case the opposite team doesn’t score any point. In the case of a draw, teams score 1 point each. After all the matches end, the final score a:b is calculated: a and b — the number of points scored by the first and second team, respectively.

For example, if the first match is won by the first team, the second match ended with a draw, and the third match is also won by the first team, the final score is 7:1.

You are given the final score. Find out whether the given score is possible, and what is the minimum number of matches could be. Print the number of matches won by the first team, the number of matches ended with a draw, and the number of matches won by the second team.

Input

The first line contains a single integer a — the number of points scored by the first team.

The first line contains a single integer b — the number of points scored by the second team. The given a and b are nonnegative and don’t exceed 109. Output If the given final score isn’t possible, print −1.

Otherwise, print three integers: the number of matches won by the first team, the number of matches ended with a draw, and the number of matches won by the second team, respectively. Find any solution with the minimum number of matches played.

Scoring

| Subtask | Score | Constraints |
| --- | --- | --- |
| 1 | 21 | 0 ≤ a ≤ 50; b = 0 |
| 2 | 23 | 0 ≤ a,b ≤ 50; a = b |
| 3 | 25 | 0 ≤ a,b ≤ 50 |
| 4 | 31 | 0 ≤ a,b ≤ 109 |

Examples

| standard input | standard output |
| --- | --- |
| 7 1 | 2 1 0 |
| 2 1 | -1 |

Problem B. Tetris Remastered

Time limit: 1 second

Mila likes to play Tetris. Today she learnt about a new game that is similar to Tetris. The new game has an infinite rectangular field with the bottom and width equal to n, divided into cells of size 1 × 1. Unlike real Tetris in this game horizontal pieces with height 1 and width x consisting of x cells — of size 1 × x, are used. Before the next piece starts to fall, a player can choose it’s size x as any integer between 1 and n, inclusive. Pieces can’t be rotated, but they can be moved left or right. A piece falls until it reaches an occupied cell under it or the bottom of the field.

Mile doesn’t like to leave empty cells under the pieces. Her goal is to fill lower rows of the field in the way that all occupied cells form a rectangle of width n.

You are given a field state: a1,a2,...,an, where ai — the number of occupied cells in the i-th column of the field. In the given field no empty cell is under the occupied one. For example, if sequence a is 3,2,4,2,2,4, the field looks like this:

Find the minimum number of pieces Mila needs to play to occupy the lower rows of the field forming a rectangle of width n.

Input

The first line contains a single integer n — the width of the field (1 ≤ n ≤ 2 · 105). The second line contains n integers a1,a2,...,an — the number of occupied cells in each column of the field (0 ≤ ai ≤ 109). At least on of the ai is strictly greater than 0.

Output

Print a single integer: the minimum number of pieces Mila will need to build a rectangle of width n.

Scoring

| Subtask | Score | Constraints |  |
| --- | --- | --- | --- |
| Subtask | Score | n | ai |
| 1 | 8 | n ≤ 10 | ai ≤ 5 |
| 2 | 13 | n ≤ 100 | ai ≤ 500 |
| 3 | 16 | n ≤ 1000 | ai ≤ 5000 |
| 4 | 17 | n ≤ 1000 | ai ≤ 109 |
| 5 | 25 | n ≤ 105 | ai ≤ 109 when n > 1000 sequence a is generated randomly |
| 6 | 21 | n ≤ 2 · 105 | ai ≤ 109 |

Example

| standard input | standard output |
| --- | --- |
| 6 3 2 4 2 2 4 | 4 |

Explanation

In the example Mile can use the following four pieces:

| 3 |  | 4 |
| --- | --- | --- |
|  | 2 | 1 |

Problem C. Optimal Truck

Time limit: 2 seconds

Peter is going to buy a truck and start a small transportation business. He studied the market and found out that there are n potential customers in his city. There are mi contract options for the i-th client. Each option is specified by two numbers: wij — the minimum capacity of the truck, which is required to fulfill the contract, and cij — the profit that Peter will receive if he concludes this contract. No more than one contract can be concluded with each client.

Now Peter is thinking which truck is better to buy in order to get the profit he needs. He has q options. In the i-th option, Peter wants his profit to be at least xi. Help him, for each of the options, find the minimum capacity of the truck with which you can make such a profit.

Input

The first line contains the integer n (1 ≤ n ≤ 105).

This is followed by n blocks describing contract options for each of the potential customers. Each such block begins with the number mi, followed by mi pairs of numbers wij,cij (1 ≤ mi, mi ≤ 5 · 105, 1 ≤ wij,cij ≤ 109).

Next comes the number q (1 ≤ q ≤ 105). This is followed by the q numbers xi (1 ≤ xi ≤ 109).

Output

Print q numbers, the minimum carrying capacity of the truck, with which you can get the required profit, for each of the options. If it is impossible to get the required profit, print −1 for the corresponding option.

Scoring

| Subtask | Score | Constraints |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Subtask | Score | n | mi | q | Additional |
| 1 | 7 | n ≤ 5 | mi ≤ 10 | q ≤ 10 | wi,ci,xi ≤ 100 |
| 2 | 15 | n ≤ 100 | mi ≤ 500 | q ≤ 10 | wi,ci,xi ≤ 100 |
| 3 | 21 | n ≤ 105 | mi ≤ 5 · 105 | q ≤ 10 | — |
| 4 | 24 | n ≤ 105 | mi ≤ 5 · 105 | q ≤ 105 | wi ≤ 100 |
| 5 | 33 | n ≤ 105 | mi ≤ 5 · 105 | q ≤ 105 | — |

Example

| standard input | standard output |
| --- | --- |
| 3 2 10 20 20 30 1 40 50 3 2 5 1 10 4 7 5 10 55 32 100 17 | 1 40 20 -1 10 |

Problem D. Bookshelf Sorting

Time limit: 2 seconds

Irma works in a library. Every day she watches visitors take a couple of books from the bookshelf, read them, and put books back in the same places they took them. Usually people mess up the order and swap two books they read. Let’s take a look at one specific bookshelf with n books in some order, numbered from 1 to n from left to right. The i-th visitor takes books from positions xi and yi and puts them back on the same positions, but in the wrong order. After the i-th visitor, the book that was at xi is now at position yi and vice versa.

In the evening, after the library is closed, Irma wants to put all the books back on their places. For each book there is a number pi — a position where that book should end up in the end. To rearrange books, Irma can take any book from the shelf and insert it in the beginning or in the end (so it ends up in the first or in the last place on the shelf).

What is the minimum number of moves Irma can do to put all books in order? Answer this question for some initial placement of books, determined by pi, and after each visitor that swapped places of some two books.

Input

The first line contains two integers n and q (2 ≤ n ≤ 2 · 105; 0 ≤ q ≤ 2 · 105) — the number of books on the shelf and the number of visitors. The next line contains n distinct integers pi (1 ≤ pi ≤ n), meaning that the book in the i-th position must end up in position pi.

Next q lines describe library’s visitors. Each line contains two integers xi, yi (1 ≤ xi < yi ≤ n), that mean that the i-th visitor swapped two books on positions xi and yi.

Output

Print q +1 integers — the minimum number of moves required to sort all books for the initial order, then for the order the after the first visitor, ..., after all q visitors.

Scoring

| Subtask | Score | Constraints |
| --- | --- | --- |
| 1 | 10 | n,q ≤ 8 |
| 2 | 15 | n,q ≤ 200 |
| 3 | 15 | n ≤ 2000; q = 0 |
| 4 | 15 | n,q ≤ 2000 |
| 5 | 20 | n ≤ 2 · 105; q = 0 |
| 6 | 25 | n,q ≤ 2 · 105 |

Example

| standard input | standard output |
| --- | --- |
| 5 2 5 1 2 4 3 4 5 1 4 | 2 1 3 |

Note

The initial order of books is (5,1,2,4,3). To sort these books out, first, put the book 4 in the end, then do the same with book 5. After the first visitor, the bookshelf now looks like (5,1,2,3,4); it’s enough to just move the book 5 to the end. After the second visitor the order of books is (3,1,2,5,4). For this order the minimum number of moves is 3, there are several ways to achieve the final order in 3 moves.

Problem E. Nice Shape

Time limit: 4 seconds You are given n rooks on the different cells of the infinite chessboard. The i-th of them is in the cell (ri,ci).

In one move you can move any rook to any cell in the same row/column. In other words, in one move you can choose any i and then either replace ri to any other integer or replace ci to any other integer. You can’t move a rook to the cell with some other rook.

Four different rooks a,b,c,d form a nice shape if you can find a rectangle such that a,b,c,d are its corners. In other words, if the set of cells {(ra,ca),(rb,cb),(rc,cc),(rd,cd)} is equal to the set of cells {(x1,y1),(x1,y2),(x2,y1),(x2,y2)} for some integers x1,x2,y1,y2 with x1 = x2 and y1 = y2.

For example, the white rooks in the following picture form a nice shape.

Your goal is to find the minimum number of moves that you can perform to get a nice shape. In other words, you need to find the minimum number of moves that you can perform, such that after them it will be possible to find a rectangle with four rooks in its corners.

Input

The first line of input contains one integer t (1 ≤ t ≤ 25000): the number of test cases. The description of t test cases follows. The first line contains one integer n (4 ≤ n ≤ 100000). The i-th of the next n lines contains two integers ri,ci (1 ≤ ri,ci ≤ 109) For each pair i,j with i = j, ri = rj or ci = cj. The total sum of n is at most 100000.

Output

For each test case, print one integer: the minimum number of moves you need to perform to obtain at least one nice shape among given rooks.

Scoring

| Subtask | Score | Constraints |
| --- | --- | --- |
| 1 | 10 | n ≤ 4 |
| 2 | 10 | n ≤ 50 |
| 3 | 10 | n ≤ 200 |
| 4 | 30 | n ≤ 2000 |
| 5 | 40 | n ≤ 105 |

Example

| standard input | standard output |
| --- | --- |
| 5 4 4 4 1 1 2 2 3 3 4 4 4 4 1 1 4 2 2 6 3 2 2 1 1 2 3 3 3 4 3 1 5 1 1 1 2 1 3 1 4 5 5 4 1000000000 1000000000 1000000000 1 2 2 1000000000 999999999 | 4 2 1 3 3 |

Note

One of the possible optimal solutions for the first test case of the example:

One of the possible optimal solutions for the second test case of the example:

# Citations

1. [Первый отборочный этап — statements-1 (en)](https://lk-dovuz.innopolis.university/public/files/statements-1%20%28en%29.pdf), file 6560bebaf39a

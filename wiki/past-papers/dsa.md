---
type: page
title: "Past exam papers: DSA"
description: "Past exams and tests of DSA at Innopolis University (11 papers, 2020–2026), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "dsa"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "DSA"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: DSA

Exams and tests of **DSA** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2026: Final Sample

Files: [DSA Final Sample 2026.pdf](https://glebpopov.notion.site/3fee746cceef8073b95fd6a47614a10d)


Group:

BS25

-

-

0

Name:

Email:

@innopolis.university

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

Dear student, this is a mock exam for practice.

s

Data Structures and Algorithms — Spring 2026
Mock Final Exam
Please read the following:

• This mock contains 25 questions. Actual final exam will have 8–12 questions.
• Format and style are similar to the actual final exam; content may be different.
• You may use it under exam-like conditions or for revision.

D

at
a

• Note that the actual final exam may contain questions that do not appear in this
mock exam.

This mock exam has 25 questions.

Page 1

IU DSA Spring 2026 — Mock Final Exam

Question A
Compute asymptotic worst case time complexity of the Solve procedure:
1. Express the running time T (n) as a recurrence relation.

1
2
3

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

s

2. Find the asymptotic complexity of T (n) using the master method. Specify which case applies and
give a brief justification.
/* A is a 1-indexed array; n is the number of elements in A */
Solve(A, n):
return Helper(A, 1, n)

4

7
8
9
10
11
12
13
14
15
16
17
18
19
20

Recurrence relation T (n) =

Asymptotic complexity T (n) =

at
a

6

Helper(A, l, r):
if r - l <= 50
return l
else
low := l; high := r
while low < high:
mid := ⌊(low + high) / 2⌋
count := 0
for i from l to r:
if A[i] > A[mid]: count := count + 1
if count > (r - l + 1) / 2 then high := mid else low := mid + 1
k := ⌈(r - l + 1) / 3⌉
a := Helper(A, l,
l + k - 1)
b := Helper(A, l + k,
l + 2*k - 1)
c := Helper(A, l + 2*k,
r)
return low

Case and justification

D

5

This mock exam has 25 questions.

Page 2

Group:

BS25

-

-

0

Name:

Email:

@innopolis.university

Question B

n · log2 n =



3/4

n





2
1+
n

n
=

2

n



In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

√

s

Use the most precise asymptotic notation ( O , Θ , Ω ) in the relations below.
If none applies, use X .

n1.001 =


n log2 n

log2(n!) =
√
4
n=

(n log2 n)
(log2 n)

3n + 2 n =
n2
=
log n
(n + 1)! =

(3n)
√ 
n n
(n!)

Question C

Given a set A of n integers and a target number k, consider the problem of finding a subset of A of
maximum size whose elements sum to exactly k. A brute-force algorithm enumerates all subsets of A,
checks the sum of each, and among those that sum to k, picks one with the largest number of elements.

at
a

1. Give pseudocode for such a brute-force algorithm (iterative or recursive), or a clear step-by-step
description.

D

2. What is the worst case time complexity of this algorithm in terms of n?
3. Brief justification for the time complexity:

4. What is the worst case space complexity (excluding the input) if we use an iterative enumeration
(e.g. a single array of length n to represent the current subset)?
This mock exam has 25 questions.

Page 3

IU DSA Spring 2026 — Mock Final Exam

Question D

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

s

We have n sorted lists containing m elements in total. We want to merge them into one sorted list of m
elements.
Fill in the table with the asymptotic worst case time complexity of merging, depending on how the
input lists and the output list are represented.
Input lists / Output list

Array

Singly-linked (with tail)

Doubly-linked

Array (each list contiguous)
Singly-linked (with tail)
Doubly-linked

Brief justification:

Question E

Consider a hybrid sorting algorithm that runs Quick-Sort but stops recursion when the current subarray
has size ≤ k; then applies Counting-Sort to each such small block (keys in a fixed range [0, R]) and
concatenates the results.
1. What is the worst case time complexity of this hybrid

at
a

in terms of n, k, and R?

2. If we choose k = Θ(log n) and R = O(n),

D

what is the overall worst case time complexity?

Brief justification:

This mock exam has 25 questions.

Page 4

Group:

BS25

-

-

0

Name:

Email:

@innopolis.university

Question F
Apply Bucket-Sort to the following numbers in [0, 1):

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

1. Show the contents of each bucket (before sorting inside buckets).

s

0.92, 0.21, 0.03, 0.55, 0.07, 0.41, 0.25, 0.12, 0.67, 0.05

2. Give the sorted sequence (after sorting each bucket and concatenating).

Question G

For each statement, write TRUE or FALSE.
1. n2 = O(n3/2 ).

2. In a binary search tree, the node with the maximum key has no left child.
3. Heap-Sort has O(n) worst case time complexity.

at
a

4. Radix-Sort (with a fixed digit range) sorts n integers

D

in Θ(n) time regardless of the number of digits.
5. In ArrayQueue, Enqueue(x) has Θ(n) worst case time complexity.
6. The height of an AVL tree with n nodes is Θ(log n).
7. For the recurrence T (n) = 2T (n/2)+n, the master theorem gives T (n) = Θ(n).
8. In dynamic programming, overlapping subproblems are solved at least twice.
9. Merge-Sort is a comparison-based sorting algorithm.
10. A red-black tree with n internal nodes has height at least 2 log2 (n + 1).
This mock exam has 25 questions.

Page 5

IU DSA Spring 2026 — Mock Final Exam

Question H
Consider a binary search tree stored in standard array representation. Start from an empty tree and
insert the following keys in order:

22,

4,

11,

19,

30,

2,

6,

25

s

8,

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

15,

1. Draw the constructed BST (after all insertions).

2. Fill in the array representation after all insertions (before any deletion).
0

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

9

10

11

12

13

14

15

3. Fill in the array representation after deleting key 30.
0

1

2

3

4

5

6

7

8

at
a

4. Fill in the array representation after deleting key 8 (from the tree that already had 30 deleted).
1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

D

0

5. Draw the final BST (after all insertions and both deletions).

This mock exam has 25 questions.

Page 6

Group:

BS25

-

-

Name:

0

Email:

@innopolis.university

Question I
Answer the following about the Longest Common Subsequence (LCS) problem. Given two sequences
X and Y , we want the length of an LCS and one such subsequence.

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

s

1. What is the worst case time and space complexity of computing the LCS length using dynamic
programming with tabulation (bottom-up), if |X| = m and |Y | = n?
Time:

Space:

2. Find the LCS length for X = ⟨A, B, C, A, B⟩ and Y = ⟨B, A, C, B, A⟩. Then give one LCS of that
length.
LCS length =

One LCS (e.g. as sequence):

3. Fill in the DP table C[i, j] (LCS length of X[1..i] and Y [1..j]). Row i = 0 and column j = 0 are
filled with 0.
C
i=0

j=0
0

i = 1 (A)

0

i = 2 (B)

0

i = 3 (C)

0

i = 4 (A)

0

i = 5 (B)

0

j = 1 (B)
0

j = 2 (A)
0

j = 3 (C)
0

j = 4 (B)
0

j = 5 (A)
0

at
a

Question J

D

The initial AVL tree is given in array representation. An empty slot is shown as –.
0

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

7

4

9

1

5

8

10

–

2

–

–

–

–

–

–

–

Key 3 is inserted using the usual BST insertion (without rebalancing).
1. Which rotation(s) are necessary to restore the AVL invariant? For each rotation, give the pair of
keys (parent, child ) where the rotation is performed. List at most two rotations.
Rotation 1 (parent, child):
Rotation 2 (parent, child):

This mock exam has 25 questions.

Page 7

IU DSA Spring 2026 — Mock Final Exam

Question K

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

s

The maximum subarray problem: given an array of n numbers, find a contiguous subarray with maximum sum.
For each of the three approaches below, state the worst case time complexity in terms of n and give
a brief justification.
Time complexity for Brute For

(the rest is in the file)

## 2026: Midterm

Files: [DSA Midterm 2026.pdf](https://glebpopov.notion.site/356e746cceef8029b023c93cee0d29d3)


Group:

BS25

-

-

0

Name:

Email:

@innopolis.university

Data Structures and Algorithms — Spring 2026
Midterm Exam
Dear student, welcome to the Midterm Exam!
Please, read carefully the following information about the exam:
• This is a closed book exam:
1. Notes, cheat sheets, or devices (including laptops, tablets, phones, smartwatches,
headphones, radios, TV-sets) are not allowed.
2. Cheating, attempts of cheating, assisting others in cheating, communicating
with other students during the exam will result in immediate removal from the
exam, without any opportunity of retake.
• Do not open the exam questions before the exam starts!
Reading questions before the o!cial start will be considered cheating.
• Keep your student ID card on the table next to you for the duration of the exam.
• Write your name, group number, and email address at the top of this page.
• When the exam starts, write your name, group number, and email address at the
top of every odd page.
• This exam contains 9 regular questions for 125 points total.
• Maximum total for the exam is 100 points, so you have some room for mistakes.
• While you wait for the exam to start, you may draw a doodle in the box below:

For full grade you need to score 100 out of 125 points in this Midterm Exam.

Page 1 of 6

IU DSA Spring 2026 — Midterm Exam

Question A, variant 1 (15 points)
Compute asymptotic worst case time complexity of the Solve procedure:
1. Express the running time of the Solve procedure T (n) as a recurrence relation.
2. Find the asymptotic complexity of T (n) using the master method. You must specify which case of
the master theorem is applied and provide complete justification for its use.
1
2
3
4

/* A is a 1-indexed array
* n is the number of elements in A */
Solve(A, n):
return Helper(A, 1, n)

5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21

Helper(A, l, r):
if r - l <= 100
return l
else
k := →(r - l + 1) / 6↑
a = Helper(A, l,
l + 2 * k) + Helper(A, l + k,
l + 3 * k)
b = Helper(A, l + 2 * k, l + 4 * k) + Helper(A, l + 3 * k, l + 5 * k)
c = Helper(A, l + 4 * k, r)
low := l; high := r
while low < high:
mid := ↓(low + high) / 2↔
count := 0
for i from l to r:
if A[i] > A[mid]: count := count + 1
if count > (r - l + 1) / 2 then high := mid else low := mid + 1
return low
Recurrence relation T (n) =
Asymptotic complexity T (n) =
Which case of the master theorem applies, if any?
Justification

For full grade you need to score 100 out of 125 points in this Midterm Exam.

Page 2 of 6

Group:

BS25

-

-

0

Name:

Email:

@innopolis.university

Question B, variant 1 (16 points)
Use the most precise asymptotic notation ( O , ” , # ) in the relations below.
In case none of the asymptotic notations is applicable, use

n

2026 =
(log2 n)

2026

=

log2 (nn) =
!
"n
1
1+
=
n

((n + 2026)!)
% 2026
↘ &
n

(log2(n!))
(n)

↗.
!

2026
2025

"n

=

n log2 n =
'
n log2 n =
2n + 2 n =

\# 2026 $
n 2025
! 2 "
n
log n
%↘ 2
↘ &
n · log2 n
(4n)

Question C, variant 1 (10 points)
Consider the recurrence relation T (n) = 8T (n/3) + 5n2 + 10. Applying the master theorem, we get:
1. T (n) = ”(n2 log n);
2. T (n) = ”(n3 );
3. the master theorem is not applicable;
4. none of the above.
Answer
Justify your answer. If the master theorem is applicable, specify which case and which conditions are
satisfied. Otherwise, explain why it is not applicable.
Justification

For full grade you need to score 100 out of 125 points in this Midterm Exam.

Page 3 of 6

IU DSA Spring 2026 — Midterm Exam

Question D, variant 1 (15 points)
Consider a collection A of n columns. Each column Ci is itself a collection of n elements. Consider
extending A with one more column Cn+1 that consists of the diagonal elements C1 [1], C2 [2], . . . , Cn [n]:




1 4 7
1 4 7 1
extend 2 5 8 = 2 5 8 5
3 6 9
3 6 9 9
(Columns are C1 = (1 2 3), C2 = (4 5 6), C3 = (7 8 9); the new column is the diagonal C4 = (1 5 9).)
Fill in the table below. Write the asymptotic worst case time complexity in each cell.
Rep. of A / Rep. of Ci

Array List

Singly-Linked (no tail)

Singly-Linked (with tail)

Array List
Singly-Linked (no tail)
Singly-Linked (with tail)
Brief justification:

Question E, variant 1 (15 points)
Consider sorting a collection of phrases using Radix-Sort, treating each word as a “digit” of a phrase:
• Each phrase is a list of at most w words.
• Each word is a list of at most s symbols.
• Each symbol comes from an alphabet of size a.
Assume that comparing symbols is ”(1), but comparing words or phrases is not.
What is the worst case time complexity for sorting p phrases in terms of p, w, s, and a, if
1. words are sorted using Insertion-Sort
2. words are sorted using Counting-Sort
3. words are sorted using Quick-Sort
For full grade you need to score 100 out of 125 points in this Midterm Exam.

Page 4 of 6

Group:

BS25

-

-

Name:

0

Email:

@innopolis.university

Question F, variant 1 (12 points)
Apply Counting-Sort to the following array. Each column is an element with a numeric key (top row)
and a letter data (bottom row). Sort by key only; preserve the data with each key.
key
data

3
I

1
E

2
D

0
R

2
S

1
A

4
E

0
I

2
H

1
N

0
S

3
N

1. Give the auxiliary array C after the cumulative step (ready to place elements).
k

0

1

2

3

4

C[k]
2. Give the output array (keys and data in sorted order).
key
data

Question G, variant 1 (10 points)
For each statement, write TRUE or FALSE in the corresponding box.
1. If log(f (n)) = ”(log(g(n))) then f (n) = ”(g(n)).
2. Incrementing a binary counter takes ”(log k) worst case time,
where k is the number of digits used in the counter.
3. In ArrayStack, Push(x) has ”(n) worst case time complexity.
4. Merge-Sort has ”(n log n) worst case time complexity.
5. Counting-Sort sorts n integers in the range [0, n2 ] in ”(n) worst case time.
6. If the master theorem does not apply to a recurrence,
the algorithm may loop indefinitely on some input.
7. Dynamic Programming is a technique that involves
a dynamically-typed programming language (e.g. Python).
8. Quick-Sort has ”(n log n) worst case time complexity.
9. In a binary search tree, the node with the minimum key
cannot have a right child.
10. The height of a red-black tree with n internal nodes is ”(log n).
For full grade you need to score 100 out of 125 points in this Midterm Exam.

Page 5 of 6

IU DSA Spring 2026 — Midterm Exam

Question H, variant 1 (12 points)
Consider a binary search tree T stored in the following array representation. An empty slot is shown as –.
0

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

8

4

12

2

6

10

–

–

–

–

–

9

11

–

–

–

What will the array look like after inserting into the initial tree T the keys 20, 5, 17 (in this order)?
0

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

13

14

15

13

14

15

What will the array look like after deleting key 10 from the initial tree T ?
0

1

2

3

4

5

6

7

8

9

10

11

12

What will the array look like after deleting key 8 from the initial tree T ?
0

1

2

3

4

5

6

7

8

9

10

11

12

Question I, variant 1 (20 points)
Answer the following about the Rod Cutting problem.
1. What is the worst case time complexity of computing the maximum revenue for a rod of length n?
Dynamic Programming with tabulation:
Dynamic Programming with memoization:
2. Find the maximum revenue for a rod of length 10 with the following price table:
length i
price pi

1
1

2
5

3
5

4
8

5
10

6
14

7
20

8
18

9
22

10
25

Maximum revenue =
Rod lengths (pieces) that achieve this revenue:
Present in the table the values of the solutions to subproblems used in DP for this problem:
0

1

2

3

4

5

6

7

8

9

For full grade you need to score 100 out of 125 points in this Midterm Exam.

10

Page 6 of 6

## 2026: Midterm Sample

Files: [DSA Midterm Sample 2026.pdf](https://glebpopov.notion.site/356e746cceef80b180cce894c6269b71)


Group:

BS25

-

-

0

Name:

Email:

@innopolis.university

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

Dear student, this is a mock exam for practice.

s

Data Structures and Algorithms — Spring 2026
Mock Midterm Exam
Please read the following:

• This mock contains 14 questions.

• Format and style are similar to the real midterm; content is varied.
• You may use it under exam-like conditions or for revision.

D

at
a

• Note that the midterm exam may contain questions that do not appear in this mock
exam.

This mock exam has 14 questions.

Page 1 of 9

IU DSA Spring 2026 — Mock Midterm Exam

Question A
Compute asymptotic worst case time complexity of the Solve procedure:
1. Express the running time T (n) as a recurrence relation.

1
2
3

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

s

2. Find the asymptotic complexity of T (n) using the master method. Specify which case applies and
give a brief justification.
/* A is a 1-indexed array; n is the number of elements in A */
Solve(A, n):
return Helper(A, 1, n)

4

7
8
9
10
11
12
13
14
15
16
17
18
19
20

Recurrence relation T (n) =

Asymptotic complexity T (n) =

at
a

6

Helper(A, l, r):
if r - l <= 50
return l
else
low := l; high := r
while low < high:
mid := ⌊(low + high) / 2⌋
count := 0
for i from l to r:
if A[i] > A[mid]: count := count + 1
if count > (r - l + 1) / 2 then high := mid else low := mid + 1
k := ⌈(r - l + 1) / 3⌉
a := Helper(A, l,
l + k - 1)
b := Helper(A, l + k,
l + 2*k - 1)
c := Helper(A, l + 2*k,
r)
return low

Case and justification

D

5

This mock exam has 14 questions.

Page 2 of 9

Group:

BS25

-

-

0

Name:

Email:

@innopolis.university

Question B

n · log2 n =



3/4

n





2
1+
n

n
=

2

n



In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

√

s

Use the most precise asymptotic notation ( O , Θ , Ω ) in the relations below.
If none applies, use X .

n1.001 =


n log2 n

log2(n!) =
√
4
n=

(n log2 n)
(log2 n)

3n + 2 n =
n2
=
log n
(n + 1)! =

(3n)
√ 
n n
(n!)

Question C

Given a set A of n integers and a target number k, consider the problem of finding a subset of A of
maximum size whose elements sum to exactly k. A brute-force algorithm enumerates all subsets of A,
checks the sum of each, and among those that sum to k, picks one with the largest number of elements.

at
a

1. Give pseudocode for such a brute-force algorithm (iterative or recursive), or a clear step-by-step
description.

D

2. What is the worst case time complexity of this algorithm in terms of n?
3. Brief justification for the time complexity:

4. What is the worst case space complexity (excluding the input) if we use an iterative enumeration
(e.g. a single array of length n to represent the current subset)?
This mock exam has 14 questions.

Page 3 of 9

IU DSA Spring 2026 — Mock Midterm Exam

Question D

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

s

We have n sorted lists containing m elements in total. We want to merge them into one sorted list of m
elements.
Fill in the table with the asymptotic worst case time complexity of merging, depending on how the
input lists and the output list are represented.
Input lists / Output list

Array

Singly-linked (with tail)

Doubly-linked

Array (each list contiguous)
Singly-linked (with tail)
Doubly-linked

Brief justification:

Question E

Consider a hybrid sorting algorithm that runs Quick-Sort but stops recursion when the current subarray
has size ≤ k; then applies Counting-Sort to each such small block (keys in a fixed range [0, R]) and
concatenates the results.
1. What is the worst case time complexity of this hybrid

at
a

in terms of n, k, and R?

2. If we choose k = Θ(log n) and R = O(n),

D

what is the overall worst case time complexity?

Brief justification:

This mock exam has 14 questions.

Page 4 of 9

Group:

BS25

-

-

0

Name:

Email:

@innopolis.university

Question F
Apply Bucket-Sort to the following numbers in [0, 1):

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

1. Show the contents of each bucket (before sorting inside buckets).

s

0.92, 0.21, 0.03, 0.55, 0.07, 0.41, 0.25, 0.12, 0.67, 0.05

2. Give the sorted sequence (after sorting each bucket and concatenating).

Question G

For each statement, write TRUE or FALSE.
1. n2 = O(n3/2 ).

2. In a binary search tree, the node with the maximum key has no left child.
3. Heap-Sort has O(n) worst case time complexity.

at
a

4. Radix-Sort (with a fixed digit range) sorts n integers

D

in Θ(n) time regardless of the number of digits.
5. In ArrayQueue, Enqueue(x) has Θ(n) worst case time complexity.
6. The height of an AVL tree with n nodes is Θ(log n).
7. For the recurrence T (n) = 2T (n/2)+n, the master theorem gives T (n) = Θ(n).
8. In dynamic programming, overlapping subproblems are solved at least twice.
9. Merge-Sort is a comparison-based sorting algorithm.
10. A red-black tree with n internal nodes has height at least 2 log2 (n + 1).
This mock exam has 14 questions.

Page 5 of 9

IU DSA Spring 2026 — Mock Midterm Exam

Question H
Consider a binary search tree stored in standard array representation. Start from an empty tree and
insert the following keys in order:

22,

4,

11,

19,

30,

2,

6,

25

s

8,

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

15,

1. Draw the constructed BST (after all insertions).

2. Fill in the array representation after all insertions (before any deletion).
0

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

9

10

11

12

13

14

15

3. Fill in the array representation after deleting key 30.
0

1

2

3

4

5

6

7

8

at
a

4. Fill in the array representation after deleting key 8 (from the tree that already had 30 deleted).
1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

D

0

5. Draw the final BST (after all insertions and both deletions).

This mock exam has 14 questions.

Page 6 of 9

Group:

BS25

-

-

Name:

0

Email:

@innopolis.university

Question I
Answer the following about the Longest Common Subsequence (LCS) problem. Given two sequences
X and Y , we want the length of an LCS and one such subsequence.

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

s

1. What is the worst case time and space complexity of computing the LCS length using dynamic
programming with tabulation (bottom-up), if |X| = m and |Y | = n?
Time:

Space:

2. Find the LCS length for X = ⟨A, B, C, A, B⟩ and Y = ⟨B, A, C, B, A⟩. Then give one LCS of that
length.
LCS length =

One LCS (e.g. as sequence):

3. Fill in the DP table C[i, j] (LCS length of X[1..i] and Y [1..j]). Row i = 0 and column j = 0 are
filled with 0.
C
i=0

j=0
0

i = 1 (A)

0

i = 2 (B)

0

i = 3 (C)

0

i = 4 (A)

0

i = 5 (B)

0

j = 1 (B)
0

j = 2 (A)
0

j = 3 (C)
0

j = 4 (B)
0

j = 5 (A)
0

at
a

Question J

D

The initial AVL tree is given in array representation. An empty slot is shown as –.
0

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

7

4

9

1

5

8

10

–

2

–

–

–

–

–

–

–

Key 3 is inserted using the usual BST insertion (without rebalancing).
1. Which rotation(s) are necessary to restore the AVL invariant? For each rotation, give the pair of
keys (parent, child ) where the rotation is performed. List at most two rotations.
Rotation 1 (parent, child):
Rotation 2 (parent, child):

This mock exam has 14 questions.

Page 7 of 9

IU DSA Spring 2026 — Mock Midterm Exam

Question K

In
St no
ru po
ct lis
Sp ure U
m rin s a niv
o c g nd e r
k 20 A sit
ex 2
y
l
am 6 go
rit
hm

s

The maximum subarray problem: given an array of n numbers, find a contiguous subarray with maximum sum.
For each of the three approaches below, state the worst case time complexity in terms of n and give
a brief justification.
Time complexity for Brute Force:
Brief justi

(the rest is in the file)

## 2025: Final Sample

Files: [DSA Final Sample 2025.pdf](https://glebpopov.notion.site/1f5e746cceef8036ac4fdb756ac7664f)


DSA final sample

3

TASK C

DSA Final Sample
1

Task A

Write all possible topological sortings for this graph.
A

B
C

D

E

2

F

Task B

Write recursive function for time complexity and calculate it using Master Theorem
1
2
3
4
5
6

function process(P):
Q1 = new priority queue (min-heap)
Q2 = new priority queue (max-heap)
count = 0
sum = 0
n = P.size()

7

while not P.empty():
element = P.extract()
count += 1

8
9
10
11

if element < 10:
sum += element * element

12
13
14

if count <= n/3:
Q1.insert(element)
else if count <= 2*n/3:
Q2.insert(element)

15
16
17
18
19

sum = sum + process(Q1) + process(Q2)
return sum

20
21

3

Task C

Compare functions by time complexity
f (n)
n2
nn
n+1 n
( n )
1
log n2
n log n
sin(n)

g(n)
2n
n!
1
0
log2 n
log n!
1

f (n) = o(g(n))

f (n) = O(g(n))

1

f (n) = ω(g(n))

f (n) = Ω(g(n))

f (n) = Θ(g(n))

4

Task D

Iterate Dijkstra algorithm with Priority Queue. For each iteration write array representation of
Binary-Heap (so you need to have 6 arrays).
5

E

B

6

8
9

A

5

7
F

8
4

5

C
D

5

4

Task E

Run Edmond-Karp algorithm. Write all pathes you came through. Show min-cut and residual network.
A

4

C
10

10
2

S

8

6

10

10
B

6

T

9

D

Task F

Consider sorting a collection of phrases using Radix-Sort, considering each word as a ”digit” of a
phrase:
• Each phrase is a list of at most w words.
• Each word is a list of at most s symbols.
• Each symbol comes from an alphabet of size a.
What is the time complexity for sorting p phrases in terms of p, w, s and a, if:
1. words are sorted using Bubble-Sort (worst case)
2. words are sorted using Bucket-Sort (average case, bucket distribution is O(s))
3. words are sorted using Radix-Sort (average case, symbols as tokens in inner Radix-Sort)

2

## 2025: Midterm

Files: [DSA Midterm 2025.pdf](https://glebpopov.notion.site/1b9e746cceef80f88763e49913fc3c3b)


Question A (variant 1, 15 points)
Compute asymptotic worst case time complexity of the solve procedure:
1. Express the running time of the solve procedure 7'(n) as a recurrence relation.

2. Find the asymptotic complexity of 7'(n) using the master method. You must specify which case of
the master theorem is applied and provide complete justification for its use.

2]

Fs

n

12

13

14

15

16

17

18

19

20

/* A is a 0-indezed array

* n is the number of elements in A */

solve(A, n):
return helper(A, 0, n - 1)

helper(A, 1, r):

ifr-1<=1
return 1
else

k:=[(x-1+1) /9]

helper(A, 1, min(l +
helper(4, 1 + 2 * k,
helper(4, 1 + 4 * k,
helper(A, 1 + 6 * Kk,

Qa0 o
n

for i from 1 to r:
for j from 1 to r:
if A[i] > A[j):
exchange A[i] with
return a

3 xk, r))

min(l + 5 * k, r))
min(l + 7 * k, 1))
r)

A[3]

Recurrence relation T'(n) =

Email: @innopolis.university

Question B (variant 1, 15 points)

Consider sorting a collection of phrases using RADIX-SORT, considering each word as a “digit” of a phrase:
e Each phrase is a list of at most w words.
e Each word is a list of at most s symbols.
e Each symbol comes from an alphabet of size a.

What is the worst case time complexity for sorting p phrases in terms of p, w, s and a, if

1. words are sorted using INSERTION-SORT

2. words are sorted using COUNTING-SORT

3. words are also sorted using RADIX-SORT,

considering each symbol as a “digit” of a word?

Question C (variant 1, 15 points)

Consider the intersection' of k non-empty sorted lists of integers. For each of the following representations
of List ADT specify whether it is possible to implement the intersection of k lists with total m clements
in all lists with O(m) time complexity, and provide a brief justiication.

Dynamic Array List

Singl

Doubly-Linked List

O(mk) algorthm possible? (vES orN0) ]

y-Linked List (no tail pointer) Ofmk) algorithm possbie? (vES orNO) |

O(mk) algorithm possible? (YES or NO)
Y

1U DSA Spring 2025 — Midterm Exam
Question D (variant 1, 15 points)

Indicate, for each pai of expressions (4, B) in the table below whether A = O(B), A= oB), 4 = 2(B),
A=w(B), or 4 =6(B). W

),
frite your answer, fillng in the following table with YES or NO in each box.
Please, mind that missing answers incur less penalty than incorrect ones, for this question.

A B |A=0(B)|A=o(B)|A=(B)|A=w(B) | A=6(B)
" n!
[ NG
log™n |
nlogyn
log, (n") | logs(n!)

Question E (variant 1, 10 points)

Consider recurrence relation T(n) = 64T (n/4) + 7n® + 49. Applying the master theorem, we get:
1. T(n) = O(n*logn);
2. T(n) = O(nt);
3. master theorem s not applicable;

4. none of the above.

Answer [

Justify your answer. If master theorem s applicable, specify which case and conditions are checked.
Otherwise, explain why the master theorenn is not epplicable.

Justification

Question F (variant 1, 12 points)

Consider the following hash table with 11 slots and the hash function h(k) = (k + 1) mod 11. ‘The
hashtable is constructed by inserting keys in some unknown order, resolving collisions by linear probing.

Index | 0 [ 1 | 2 (3| 4|5 |6 | 7] 8] 9|10
Key | - 23| -1352 |15 5 |13|-|—-|9

e Could key 9 have been inserted before 237

e Could key 23 have been inserted before 27

¢ Could key 13 have been inserted before 57

e Could key 15 have been inserted before 357

Question G (variant 1, 10 points)

In the following statements, o denotes the load factor of the corresponding hash table.
For each of the statements, put TRUE or FALSE in the corresponding box:

1. If log(f(n)) = ©(log(g(n))) then f(n) = ©(g(n)).

2. Incrementing a binary counter takes ©(1) amortized,

but ©(log k) worst case (where k is the number of digits used in the counter).

3. In a stack implemented using dynamic arrays,

PUsH operation has ©(n) worst case time complexity.

4. Inserting into a hash table with separate chaining is O (1 + «) average case.

5. Finding a value associated with key k in a hash table with load factor o

is ©(1) worst case as long as hash(k) can be computed in O(1).

6. If the master theorem is not applicable,

it means that the algorithm can loop indefinitely on some input.

10.

Dynamic Programming is an implementation of an algorithm

in a dynamically-typed programming language (e.g. Python)

QUICK-SORT has ©(nlogn) worst case time complexity.

Sorting n real numbers uniformly distributed in the range from 0 to &

using BUCKET-SORT takes ©(n) time average case.

PARTITION (used in QUICK-SORT) has quadratic worst case time complexity.

1U DSA Spring 2025 — Midterm Exam

Question H (variant 1, 20 points)
Augwer the following questions related to the Rod Cutting problem:

1. Using Dynamic Programming with tabulation, what is the worst caso time complexity of finding the
‘maximum revenue obtainable by cutting a rod of length n?

P \

2. Using Dynamic Programming with memoization, what is the worst case time complexity of finding
the maximum revenue obtainable by cutting a rod of length n, while finding the corresponding places
for the cuts as well?

i \

3. Find the maximun revene by cutting a rod of length 10, given the following table of prices:

lngthi 1 23 4 5 6 7 8 9 10
pricep [2 3 9 12 13 13 14 24 %5 38

[+1%extra credit | Consider a version of the Rod Cutting problem where we cannot do more than k
cuts. Provide pseudocode for an O(nk) algorithm that finds the maximum revenue obtainable by
cutting a rod of length n making at most k cuts.

## 2022: Retake 1

Files: [DSA Retake 1 2022.pdf](https://glebpopov.notion.site/d1985957a0f14796bd3880f44429ef0a)


F2epe,  Ud cpan et b0

O/hz)

=

The following algorithm takes as input an array, and returns the array

with all the duplicate elements removed. For example, if the input array is 2 ‘% ﬁ’ &
{1,3,3,2,4,2} then the algorithm returns {1,3,2,4}.
S = new empty set
A = new empty dynamic array

for every element x in the input array A: [ﬁ_ ‘ (L_ ]

if not S.member(x) then

Question 1 (10 points)

S.insert(x) o
A.append(x) < W
return A
What is the Big-O complexity of this algorithm if the set S is implemented as
=5 a Red-Black Tree
7 n unordered Doubly-Linked List

Write the complexity in terms of n and m, where n is the size of the input
array and m is the number of distinct elements in the input array.

Tw case of Ciet & wi(C ée

O(V\W\\/ Bocote We widl check et x
existence iy & which ¥2€ tends o w i

& Tt |
S%, Are.: [O(nim

2 M)) 2o v aud we do i times,

Co resull 4y conplenity @ the 3QW€:

s Ske Coog O\ = :
QT e e pan Got lon g <D

% z
Question 2 (20 points)

Provide short answers (with justification!) to the following questions:

1) Is it possible for selection sort to run in time O(n) on some input?
ﬁ xplain how to sort n integers in the range from 0 to (n® — 1) in O(n)
tme.  Wwith  quickceo

1 @ln Kruskal’s algorithm, at what point the greedy choice is made and
[ what condition is checked?
| 14.) What does “memoization” refer to in Dynamic Programming? V
§ 5. Express T(n) in terms of Big-Theta, if T'(n) = 8T(n/3) + n?.
: o an a weighted undirected graph with 4 nodes have more than 8 distinct
| minimum spanning trees? l
colt choose &

2) No , decause eol. heesled €lewn
% T Litmes, anol vbe douces @), s0

- Ruult hime o [r\,)
3))4% e time 1+ Brkes ‘49*‘56@’%%?5
takes edge with min weight-

onditlon 1o that  new =dge must e
conheoked with vicibed @pomfg 2ot

(1) 1% refrove, to vi Ifé% -
\(‘e,e_,“% U(:QV\ %}\v@;ﬁq‘dﬁ*s . CO‘V\‘F({éeO[
S)E S 2 case f

ond also - &
B 2o )= efa)e i ”®
mz’nmr T Retake NeI, Innopolis Ui lﬂ‘a\

6>/\/o/ M3T 55 wnique each avaph

Question 3 (20 points) 5 @i jfk;

Consider the flow network in Figure 1 and perform the following:

@ Draw residual network for the given flow network.
Find the max flow and compute its value.

73.\Prove that the flow is maximum by applying max flow min cut theorem
and demonstrating the min cut.

\Sepa Stepan

/L/ﬁ Question 4 (15 points)
Given a directed weighted graph G, perform the following:

@Write down representation of G as an adjacency matrix;

A\
l/ {M 2. Find lengths of shortest paths between every pair of vertices in G using
; Floyd-Warshall algorithm. Provide your solution by constructing a

matrix after every iteration of the algorithm (by iteration here we mean, ‘///

a choice of the intermediate vertex). The solution should have exactly

matrices (1 initial + 4 iterations). M

B = C :
e \2 Graph e,r é{;gm
£ ] JNF 2
)
=N L
& 4 D

Thevation

(&

\ " DSA Spring 2022 Final Exam Retake Ne1, Innopolis University

## 2021: Final

Files: [DSA Final 2021.pdf](https://glebpopov.notion.site/4cb85390d2254ee8ad13f468284bb154)


Question P (10 points)
Consider the following array of size 8 representing a Max Heap (in a standard
way, described in the course textbooks, where leftmost cell of the array is
reserved and is not used to store any values of the max heap):
reserved

105

80

29

−1

59

6

1. Show the tree represented by this array.
2. Show the contents of the array after 30 is inserted into the original
heap.
3. Show the contents of the array after removeMax() is executed three
times.

DSA Spring 2021 Final Exam, Innopolis University

Question M (15 points)
Determine which of the following statements are True and which are False:
1. delete(k) method of Map ADT implemented using B-trees has better
worst-case asymptotic time complexity than if implemented using AVLtrees.

2. When using array representation for a binary heap, for a node with
index j, the right child node can be found at index 2j + 1.

3. In-place quicksort is a stable sorting algorithm.

4. Worst-case time complexity of counting sort is o(n log n).

5. Prim’s algorithm cannot be applied to graphs with negative cycles.

6. The recurrence T (n) = 16T ( n2 ) + n4 can be reduced to a closed form
using case 3 of Master theorem.

7. Floyd-Warshall algorithm has worst-case time complexity O(nm) where
n is the number of vertices and m is the number of edges.

8. Counting sort is not a comparison-based sorting algorithm.
9. Expected height of a random BST with n distinct keys is Θ(log2 n).

10. The net flow across a cut (S, T ) in a flow network N is the sum of flow
values of all edges with source vertex in S and target vertex in T .

DSA Spring 2021 Final Exam, Innopolis University

Question F (15 points)
Assuming ties are broken in lexicographic order (i.e. vertex C is considered
before vertex D and edge AD is considered before edge BC if their weight is
the same), perform the following for the given graph:
1. List the edges in the order they are added to the Minimum Spanning
Tree by Kruskal’s algorithm.
2. List the edges in the order they are added to the Minimum Spanning
Tree by Prim’s algorithm (algorithm starts at vertex A).

Figure 1: Graph for Question F.

DSA Spring 2021 Final Exam, Innopolis University

Question B (20 points)
Given an unsorted array of integers of length n, we are interested in finding
and printing any items that are duplicates. For example, given the array
{1, 2, 1, 4, 1, 2}, we want to print the numbers 1, 1, 2 (in any order). Solve
this problem providing three different algorithms with three different running
times:
1. Find and print all duplicates with best-case asymptotic time complexity
Ω(n2 ).
2. Find and print all duplicates with best-case asymptotic time complexity
Ω(n log n).
3. Find and print all duplicates with best-case asymptotic time complexity
Ω(n).
Give your answer in the form of a pseudo-code.
Note: algorithms that achieve the desired bound by using a faster algorithm
and then doing busy-work to consume the remaining time will not receive
credit.

DSA Spring 2021 Final Exam, Innopolis University

Question N (40 points)
Do the following for the given flow network:
1. Show residual network for the given flow network.
2. Find the max flow and its value.
3. Prove that the flow is maximum by applying max flow min cut theorem
and demonstrating the min cut.

Figure 2: Flow network for Question N.
capacity c.

f/c

notation shows flow f and

DSA Spring 2021 Final Exam, Innopolis University

## 2021: Midterm

Files: [DSA Midterm 2021.pdf](https://glebpopov.notion.site/84e79975e04a49d79a8caa45d8f5562e)


Data Structures and Algorithms · Spring 2021 · Midterm Exam

Question P (10 points)
Variant 1
Implement an algorithm (write pseudocode) that takes a list of values and
modifies it by removing all duplicates. You can use only the List ADT
methods1 .
Assuming that input list is implemented as ArrayList, determine worst-case
time complexity of your algorithm using big-O notation. Provide justification
for the time complexity.
Solution. Below algorithm has complexity O(n3 ) since for each of the n
elements we perform a linear scan and for each duplicate we perform remove
operation that is linear for ArrayList.
remove_duplicates(A,n):
i = 0
while i < A.size():
j = i + 1
while j < A.size():
if A.get(i) == A.get(j):
A.remove(j)
else:
j = j + 1

1

add(i,e), set(i,e), remove(i,e), get(i), size(), isEmpty()

Data Structures and Algorithms · Spring 2021 · Midterm Exam

Variant 2
Implement an algorithm (write pseudocode) that takes a list of values and
modifies it by duplicating (adding a copy of) each element that occurs exactly
once in the input list. You can use only the List ADT methods2 .
Assuming that input list is implemented as DoublyLinkedList, determine
worst-case time complexity of your algorithm using big-O notation. Provide
justification for the time complexity.
Solution. Below algorithm has complexity O(n3 ) since for each of the n
elements we perform a linear scan, but we use A.get(j) for each step in the
scan which is linear for DoublyLinkedList.
duplicate_unique(A,n):
i = 0
while i < A.size():
j = i + 1
is_unique = True
while j < A.size():
if A.get(i) == A.get(j):
is_unique = False
break
else:
j = j + 1
if is_unique:
A.addLast(A.get(i))

2

add(i,e), set(i,e), remove(i,e), get(i), size(), isEmpty()

Data Structures and Algorithms · Spring 2021 · Midterm Exam

Variant 3
Implement an algorithm (write pseudocode) that takes a list of values
and modifies it by rotating it by k positions (for example, rotating array
{1,2,3,4,5,6,7} by 3 positions will result in {5,6,7,1,2,3,4}). You can
use only the List ADT methods3 .
Assuming that input list is implemented as LinkedList, determine worst-case
time complexity of your algorithm using big-O notation (in terms of k and
size of the input list). Provide justification for the time complexity.
Solution. Below algorithm has worst-case complexity O(nk) since getting
and removing elements from the end of a LinkedList is linear and adding
elements to the beginning is constant time.
rotate(A,n,k):
for i from 1 to k:
A.add(0, A.get(n))
A.remove(n)

3

add(i,e), set(i,e), remove(i,e), get(i), size(), isEmpty()

Data Structures and Algorithms · Spring 2021 · Midterm Exam

Question M (15 points)
Variant 1
The following array (array is indexed from 0) represents the internal array of
keys for the hashtable:
6

0

0

0

23

11

0

0

3

15

5

4

The hashtable uses Linear Probing to handle hash collisions, and uses the
following hash function
hash(x) = (x + 5)

mod 12

Determine the order in which keys have been added to the hashtable (assuming
there were no removals). If many orders are possible, specify any one.
Solution. The keys may have been inserted in the following order:
3, 5, 23, 11, 15, 4, 6
Justification (not required from students):
1. Only 3, 5 and 23 are at the correct places according to the hash function.
This means that other keys have caused hash collision.
2. 11 has the same hash as 23 and is next to 23 in the array so could have
been inserted right after 23
3. Similarly, 15 could be inserted next, since it has the same hash as 3 and
is located right next to it.
4. 4 should have been where 15 is, but is not, so it should have been
inserted after 15.
5. 6 should have been where 4 landed, but is not, so it should have been
inserted after 4.

Data Structures and Algorithms · Spring 2021 · Midterm Exam

Variant 2
The following array (array is indexed from 0) represents the internal array of
keys for the hashtable:
13

3

0

15

0

11

6

16

6

8

The hashtable uses Linear Probing to handle hash collisions, and uses the
following hash function
hash(x) = (2x + 3)

mod 10

Determine the order in which keys have been added to the hashtable (assuming
there were no removals). If many orders are possible, specify any one.
Solution. The keys may have been inserted in the following order:
8, 11, 15, 6, 16, 6, 13, 3
Justification (not required from students):
1. Only 15, 11 and 8 are at the correct places according to the hash
function. This means that other keys have caused hash collision.
2. 6 has the same hash as 11 and is next to 11 in the array so could have
been inserted right after 11.
3. Similarly, 16 could be inserted next, since it has the same hash as 6 and
is located right next to it.
4. Second 6 could be inserted next (although in a hashmap we should not
have duplicate keys!).
5. 13 should have been where (second) 6 is, but is not, so it should have
been inserted after (second) 6.
6. 3 should have been where (second) 6 landed, but is not, so it should
have been inserted after 13.

Data Structures and Algorithms · Spring 2021 · Midterm Exam

Variant 3
The following array (array is indexed from 0) represents the internal array of
keys for the hashtable:
7

14

26

10

0

5

19

The hashtable uses Quadratic Probing4 to handle hash collisions, and uses
the following hash function
hash(x) = x mod 7
Determine the order in which keys have been added to the hashtable (assuming
there were no removals). If many orders are possible, specify any one.
Solution. The keys may have been inserted in the following order:
5, 7, 10,
Justification (not required from students):
1. Only 7, 10 and 5 are at the correct places according to the hash function.
This means that other keys have caused hash collision.
2. 19 has the same hash as 5 and is next to 5 in the array so could have
been inserted right after 5 (with +1 shift).
3. Similarly, 14 could be inserted next, since it has the same hash as 7 and
is located right next to it (with +1 shift).
4. 26 has the same hash as 5, but that cell is occupied, next cell (with
shift +1) is occupied by 19, the next cell (with shift +4) is vacant, so
that’s where 26 lands.

4

using simple sequence of square shifts: i + 1, i + 4, i + 9, i + 16, . . .

Data Structures and Algorithms · Spring 2021 · Midterm Exam

Question F (15 points)
Variant 1
Assuming that f (n) = nk which of the following statements are true? Assume
that k ≥ 1 and c > 1 are constants. Give justification for each statement.
1. f (n) = O(cn )
2. f (n) = Ω(cn )
3. f (n) = Θ(cn )
4. f (n) = o(n)
5. f (n) = ω(cn )
Hint: you can rely on facts about growth rate of common functions. For
example, you do not need to prove that n log n = o(n2 ).
Solution.
1. True. nk is a polynomial function, and cn is a exponential function.
We know that polynomials always grow more slowly than exponential.
Due to this fact it can be true.

Figure 1: A graph that compares the two functions (with k=2 and c=2),
where we can clearly see the difference in growth
2. False. because polynomials always grow slower than exponentials, and
we could see in the example graph
3. False. By definition O and Ω should be same to make this case true.
In this case it is not.

Data Structures and Algorithms · Spring 2021 · Midterm Exam

4. False. The given term is less than f (n) so it is not true.
5. False. The given term is greater than f (n) so it is not true.

Data Structures and Algorithms · Spring 2021 · Midterm Exam

Variant 2
Assuming that f (n) = n3 log n which of the following statements are true?
Give justification for each statement.
1. f (n) = O(3n log n)
2. f (n) = Ω(3n log n)
3. f (n) = Θ(3n log n)
4. f (n) = o(1)
5. f (n) = ω(n5 )
Hint: you can rely on facts about growth rate of common functions. For
example, you do not need to prove that n log n = o(n2 ).
Solution.
1. False. n3 log n is a function that multiplies a cubic factor by a logarithmic factor, and 3n log n is a function that multiplies a linear factor by
a logarithmic factor.

Figure 

(the rest is in the file)

## 2020: Final

Files: [DSA Final 2020.pdf](https://glebpopov.notion.site/14ae746cceef8004ab24dac3c01a6bd6)


Variant for Ahmed Nouralla (a.shaaban@innopolis.university)
Dear Ahmed Nouralla,
Welcome to the Final Exam of «Data Structures and Algorithms» course!
This document contains 4 questions: question D, question B, question N and
question J. Please read each question carefully and provide the solutions as
directed.
Solutions should be written by hand on paper, using pen or pencil. Be sure
to make your writing clear and readable. After writing down the solutions,
you should take a high quality photo of every page and submit those photos
as a ZIP archive on Moodle.
In case Moodle is not available, you should submit the archive via email to
n.kudasov@innopolis.ru using subject “DSA Final Exam: Ahmed Nouralla”.
Please make sure to leave at least 5 minutes before the end of the exam to
properly submit your solutions! Submissions sent after the end of the
exam will not be accepted.

DSA Spring 2020 Final Exam, Innopolis University

Variant for Ahmed Nouralla (a.shaaban@innopolis.university)

Question D (10 points)
Given a sequence of integer values, build a binary max heap, by inserting
elements in given order:
1, 43, 47, 28, 33, 13, 20, 24, 3, 27
Draw the underlying tree of the heap as well as its array representation after
every insertion.

Question B (10 points)
You have a project written in DSA programming language with source files,
which depend on each other. You are given headers of these files.
Mu.dsa
import Gamma.dll
...
...
Gamma.dsa
import Beta.dll
...
...

Xi.dsa
...
...
...
Lambda.dsa
...
...
...

Eta.dsa
import Delta.dll
...
...
Omega.dsa
import Eta.dll
import Beta.dll
...

Delta.dsa
import Lambda.dll
import Xi.dll
...
Beta.dsa
import Xi.dll
...
...

Command
DSA [sourcename.dsa]
creates [sorcename.dll] file if and only if all dependencies are met. What
application of graph can we use in such problems? Apply that application
to this problem to determine the order that will compile the whole project
with respect to dependencies. Mention if no such order exists. Support your
answer with a drawing of the graph for the given problem.

DSA Spring 2020 Final Exam, Innopolis University

Variant for Ahmed Nouralla (a.shaaban@innopolis.university)

Question N (15 points)
Compute shortest paths from e to all other vertices using Dijkstra algorithm
in two directed weighted graphs given below, if possible. On every step of
the algorithm
• show considered edge (e.g. hu, vi)
• and for every vertex
– show computed distances
– and currently known shortest path from g (e.g. e → . . . → v).
Enter these values into a corresponding table for each graph.
Graph G1 = (V1 , E1 )
• V1 = {a, b, c, d, e, f, g}
• E1 = {(g, d, 3), (a, g, 2), (g, f, 5), (g, e, 5), (g, a, 5)
(d, g, 5), (f, e, 2), (e, f, 2), (b, g, 3), (c, g, 4)
(g, b, 1), (f, g, 5), (e, g, 5), (g, c, 4), (f, d, 3)}
Table 1: Steps of Dijkstra’s algorithm for G1 .
Edge

a

b

c

d

e

f

g

...

∞
...

∞
...

∞
...

∞
...

0
...

∞
...

∞
...

Graph G2 = (V2 , E2 )
• V2 = {a, b, c, d, e, f, g}
• E2 = {(e, f, 5), (c, g, 2), (g, b, 2), (g, f, 2), (b, g, 3)
(f, e, 2), (f, g, −2), (g, c, 2), (g, a, 5), (g, e, 4)
(d, g, 2), (a, g, 3), (f, d, 3), (g, d, 3), (e, g, 1)}
Table 2: Steps of Dijkstra’s algorithm for G2 .
Edge

a

b

c

d

e

f

g

...

∞
...

∞
...

∞
...

∞
...

0
...

∞
...

∞
...

DSA Spring 2020 Final Exam, Innopolis University

Variant for Ahmed Nouralla (a.shaaban@innopolis.university)

Question J (15 points)
Given the network N = (V, E) below, you should find its max-flow using
Fold-Fulkerson algorithm. Your answer should contain:
1. A drawing of the initial network N .
2. The step-by-step of your solution, that is, a series of flows and respective
residual graphs.
3. The final (maximal) flow and its residual graph.
4. A partition whose cut capacity is equal to the max-flow.
Note: Not providing the step-by-step of your solution will incur in ZERO
grade.
V = {s, t, a, b, c, d}
E = {(a, d), (s, c), (d, t), (b, d), (b, t), (a, b)
(c, a), (c, d), (s, a)}
Capacities:
(c, d).c = 3 (d, t).c = 10 (b, t).c = 5 (c, a).c = 1
(s, c).c = 11 (a, d).c = 3 (a, b).c = 6 (b, d).c = 4
(s, a).c = 9

DSA Spring 2020 Final Exam, Innopolis University

## 2020: Midterm

Files: [DSA Midterm 2020.pdf](https://glebpopov.notion.site/c73acc7c67b24790a3676ab73c88fdc8)


Data Structures and Algorithms 2020: Midterm Exam Marks obtained |

Date: 24.02.2020 Total questions: 3 Total points: 20

Student’s name: Time: 1h20

1 MULTIPLE CHOICE (5 pts)
In each of the questions in this section, mark the correct answer(s).

1. The best and the worst-case time complexity for the Insertion sort are respectively: E

(a) O(n * log(n)) and O(n?)
(b) O(n) and O(n?)
{c) O(1) and O(n *log(n))
(d) O(n) and O(n * log(n))
2. Suppose that we perform a sequence of n operations on a certain data structure in which the ith
operation costs i if ¢ is an exact power of 2, and 1 otherwise. For the considered data structure, mark E
the option(s) which is(are) INCORRECT.
(a) The amortized cost per operation is O(1)
(b) The amortized cost per operation is O(n)
(¢) The total cost of n operations is ©(n?)
(d) An aggregate analysis finds a upper bound T(n) on the total cost of a sequence of n operations E

3. What is the correct RPN representation for 2 +2%2- (4 /2)* 27

(a)222*42/2*+-
b)) 2@22%+(42/)2%-
(© 222*+42/2*
(d)222%42/2%-+

For the next two multiple choice questions, we refer to the algorithm below.

begin
i 0;
while i < A.length do
if i =0 or Afi] > A[i — 1] then

| ieit];
else
swap Ali] < A[i - 1J;
i—i—-1;
end
end
end

4. What is the worst-case time complexity of this algorithm if » is the size of input array A? E

(a) ©(nlogn)

(b) 2(n?)
(c) 0(2")
() o(n?)

5. What is the best-case time complexity of this algorithm if n is the size of input array A? E

(a) o(nlogn)
(b) 6("*)
(¢) w(m)
(d) O(n?)

This space is for DRAFT only and will NOT be considered for grading.

Data Structures and Algorithms 2020: Midterm Exam

Student’s name:

2 ALGORITHM ANALYSIS (10 pts)

For the questions in this section, you are expected to present convincing evidence, calculations
and reasons to support your answers. A penalty of -50% points will be applied for missing or
unsatisfactory justification.

IMPORTANT: After each question, enough space is given for your solution. Other pages or
papers will NOT be graded, even if you link or refer to them.

1. Using the definition of asymptotic notation (AN), prove or disprove that 8(n log n) = 6(n2)

2. Using the definition of AN, prove or disprove that T(n) = ag + ayn + azn? + agn® is O(n®)

3. What is the recurrence of an algorithm that, to solve a problem of size n, solves 16 subproblems of
size n/4 and has a cost for combining the solutions of 100? Also, what is its asymptotic solution? You
must use the Master Theorem (CLRS version) in your answer.

4. What is the worst-case time complexity of the algorithm with input » shown below? Justify your
ANSWer.

for (int i = 0; i < n + 100; ++i){
for (int j =0; j <i *n ; ++j){
sum = sum + j;
}
for (int k = 0; k < n + n + n; ++k){
clk] = c[k] + sum;
}

5. Using the Master Theorem (CLRS version), find an asymptotic solution of the following functional
recurrence. Express your answer using ©-notation and state which case applies (if it applies): T(n) =
6T'(n/3) + n? log n

This space is for DRAFT only and will NOT be considered for grading.

Data Structures and Algorithms 2020: Midterm Exam

Student’s name:

3 HASHING - COLLISION RESOLUTION (5 pts)

IMPORTANT: After each question, enough space is given for your solution. Other pages or
papers will NOT be graded, even if you link or refer to them.

Assume that the following array express a HashSet. The top line represents the index and the bottom
represents the value (a string) in the set. In this section, assume that you don’t have to worry about
resizing.

0 [1]2[ 3 ]4[ 5
MA NY| |VA

1. Assuming that we are using chaining and that CA hashes to index 3, which bucket does CA end up
in, and what is the size of the list in that bucket?

2. Assuming that we are using linear probing and that CA hashes to index 3, which bucket does CA end
up in, and how many state objects are in that bucket?

3. Assuming that we are using linear probing, CA hashes to index 3 and CA has already been inserted.
How many buckets would linear probing need to probe if we were to insert AK, which also hashes to
index 3? (The initial bucket check counts as a probe)

4. Assuming that we are using quadratic probing (¢; = 0 and ¢; = 1), CA hashes to index 3 and CA has
already been inserted. How many buckets would quadratic probing need to probe if we were to insert
AK, which also hashes to index 3?

## 2020: Retake 2

Files: [DSA Retake 2 2020.pdf](https://glebpopov.notion.site/f18d1bb012ba460cb47ffc285b4b4e08)


DSA 2020 Retake №2 of Final Exam
Dear student,
Welcome to the Retake №2 of Final Exam of «Data Structures and Algorithms»
course!
Please make sure that you have joined Zoom meeting with camera and
microphone on for the entire duration of the exam. Your face should be
clearly visible on camera. To avoid distractions you can turn off audio on
your computer. In case of poor Internet connection, start self-recording for
the entire duration of the exam. In case of recording on a mobile device make
sure to turn on “Do Not Disturb” mode to avoid interruptions in recording.
This document contains 3 questions. Please read each question carefully and
provide the solutions as directed.
Solutions should be written by hand on paper, using pen or pencil. Be sure
to make your writing clear and readable. After writing solutions down, you
should take a high quality photo of every page and submit those photos as a
ZIP archive on Moodle.
In case Moodle is not available, you should submit the archive via email to
n.kudasov@innopolis.ru using subject “DSA Final Exam: Student Name”.
Please make sure to leave at least 5 minutes before the end of the exam to
properly submit your solutions! Submissions sent after the end of the
exam will not be accepted.

DSA 2020 Retake №2 of Final Exam

Question 1 (15 points)
Let A and B be two arrays of integer elements (possibly with duplicates).
Write down in pseudocode an in-place algorithm that computes set difference
of A and B in O(n) time, where n is the total number of elements in A and
B combined. That is, the result of the algorithm should be a sequence of
elements of A that do not occur in B. The result should not contain duplicate
elements. The algorithm should be in-place, meaning that the result must
be stored in one of the input arrays and only constant amount of additional
memory is allowed.

Question 2 (15 points)
Given a directed weighted graph G, perform the following:
1. Write down representation of G as an adjacency matrix;
2. Find lengths of shortest paths between every pair of vertices in G using
Floyd-Warshall algorithm. Provide your solution by constructing a
matrix after every iteration of the algorithm (by iteration here we mean,
a choice of the intermediate vertex). The solution should have exactly
5 matrices (1 initial + 4 iterations).
A
8

3
9

B

C
2
5

3

D
Figure 1: Graph G.

DSA 2020 Retake №2 of Final Exam

Question 3 (20 points)
Let N be a flow network with a set of vertices V and set of edges E. Let
N − (v) = {u ∈ V |(u, v) ∈ E}. Let us assign to each vertex v ∈ V a real value
cap(v). We need to compute a flow f of maximum value such that it satisfies
an extra constraint: for all v ∈ V the incoming flow for v is at most cap(v),
in other words:
X

f (u, v) ≤ cap(v)

u∈N − (v)

Is it possible to find such a flow my computing regular maximum flow on
some network derived from N ? If yes, provide a corresponding algorithm
and prove its correctness. If no, give a counterexample and prove why its
impossible to find a flow by using regular maximum flow algorithms.

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)

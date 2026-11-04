---
type: regulation
title: "Условия задач/разбор: Задачи(ru) Задачи(en) — round1-solutions-en"
resource: "https://lk-dovuz.innopolis.university/public/files/round1-solutions-en.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/round1-solutions-en.pdf"
    id: "35532c84188a"
    title: "Условия задач/разбор: Задачи(ru) Задачи(en) — round1-solutions-en"
    last_modified: "2026-11-01T23:17:26+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:26+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Условия задач/разбор: Задачи(ru) Задачи(en) — round1-solutions-en

Innopolis Open 2022-2023 First qualification round Russia, Innopolis, November 13, 2022

Problem Tutorial: “Sheet Metal”

To solve the problem, consider all possible ways to place the rectangular sheet over the form:

- • if the form is greater than or equal to the sheet, that is, w1 ≤ w2 and h1 ≤ h2; then the answer is 0

because the form can cover the sheet entirely.

- • if the form is smaller than the sheet, that is, w1 > w2 and h1 > h2, then, in any case, the sheet

would not fall apart into two pieces, and the area is w1 · h1 − w2 · h2.

- • Let’s suppose w1 ≤ w2 and h1 > h2. Then you should divide the sheet into two equal pieces; in this

case, the maximum remaining area is minimized. The answer is w1·(h21−h2).

- • If w1 > w2 and h1 ≤ h2, then, similarly, dividing the sheet into two equal pieces gives h1·(w21−w2).

Of course, there are other cases when one of the rectangles is rotated 90 degrees. It would be convenient to extract the part above as a separate function to avoid code duplication. Then, take a minimum of two calls to that function.

Problem Tutorial: “Lunchtime Fruits”

Let’s convert the problem statement to a more formal one: we have objects of four types A, B, C, and D. We can combine them into sets AABC, AACC, and ABCCD. Let’s denote X = AB, Y = AC, Z = BCD. Then these sets turn into XY , Y Y , and Y Z. Unfortunately, we can’t determine X, Y , and Z uniquely; if we assemble them differently, we can get different results. But, if we know those values, we can determine if it’s possible to assemble some predetermined number of sets.

Notice that each set has a Y . We can subtract the number of Y s at the start, and now we only have to deal with X, Y , and Z. One of the possible ways to proceed is as follows: (a is the number of objects of type A; b is the number of objects of type B, and so on; k is the total number of sets we would like to check). If b + c ≤ a, then we can assemble at most b + c sets, so we check that b + c ≥ k. In another case, we first create Xs and Y s evenly (if the number of objects of some type is too low, then take the closest to half), so you have as many Zs left as possible. The formula is min(b,c,d, b+c2−a) ≥ k − a. Since we figured out how to check if we can assemble k sets, we can run a binary search to find the maximum k.

Problem Tutorial: “Sliding Dominoes”

Consider any cell covered by a domino tile. Consider the moment when it becomes empty for the first time. How does it happen? We would need to move the tile covering it in the direction away from the cell. This means that on the previous turn, some cell at a distance of two was empty.

Thus, for every cell A, there is a unique cell B that must be uncovered before we can move the domino tile and uncover A. We will call cell B a parent of cell A. Considering that there is one initially empty cell, every cell is either unreachable or makes up a rooted tree, which root is the initially empty cell.

What’s left is to solve the problem for a tree: we traverse the tree, starting from the root, and we have to maximize the sum of visited vertices. This can be solved with dynamic programming: let dp[v] be the answer for the subtree v, including v itself. Then dp[v] = max(0,cost[v] + u dp[u]). The solution works in linear time.

Problem Tutorial: “Lost in Translation”

Let’s take on subtasks one at a time. We’ll start with m = 2n, k = 4. You can, for example, replace all 0 with AB, and 1 with CD. Now, for example, if all occurrences of C were removed, you can remove all As and recover the initial bitstring.

Consider the case k = 3 when you can only use three types of characters. Replace 0 with AC, and 1 with BC. If all Cs are removed, you essentially get the original string. Cases when either A or B are removed are similar; let’s consider what happens if the As are removed. If the first character in the string (on the second stage) is B, then it is followed by C, and that means that the original string began with 1. Otherwise, if the encoded string starts with C, it means that originally it had AC, and we deduce that it has to start with 0.

There is a corner case with this solution: we can not distinguish the two cases when we remove A in ACACAC A, or B in BCBCBC, you need to handle strings like 000 and 111 in some particular way.

Let’s try to generalize. Previously, we tried replacing 0 and 1 with some codes to recover the initial string using the knowledge of their structure. We can try encoding longer binary chunks of length c with codes over the alphabet with A, B, C. Then, to encode the binary string split it into chunks and encode each chunk individually. Encoded chunks must satisfy the following rule: for any letter deleted (A, B, or C), all the chunks must be different. It’s not always sufficient because we can still get equal strings after the concatenation of two or more chunks. For example, there exists an encoding of 2 bits into 3 characters, but you can not make it into the encoding of 4 bits into 6 characters.

But, if the encoding is random enough, then it often happens that it’s possible to recover the original string. Let’s find the number of ways to restore the string, using dynamic programming on prefixes: let dp[i][j] be the number of ways to represent the first i characters as a concatenation of j chunks with some characters removed). If it’s equal to 1, then, during the second run, you can restore the string using it (you can either hard-code it into your source or precalc each time). Based on the effectiveness of your implementation, you can build the mapping of 10-bit chunks into codes of length 19 or 18.

Finally, there exists a mapping of 20-bit chunks into codes of length 36, such that each code contains exactly 12 characters of each type A, B, and C. The advantage of using this code is that every string can be decoded uniquely because if you delete any character, each remaining code’s length is exactly 24.

Problem Tutorial: “Summer School”

We are given an implicit bipartite graph: the first part is students, and the second is parallels. We need to find the size of the maximum subset of students such that there is a matching covering it. The first subtasks can be solved using bipartite matching and maximum flow algorithms.

To get the complete solution, we will use the generalized formula from Hall’s theorem: the size of the minimum subset of students that can not be invited is max 0,max

|A| − f(A) . The usual Hall’s theorem

A checks if this is 0. Notice that the set of good parallels for each level is a segment [Li,Ri]. These segments are, in a sense, monotone: Li ≤ Li+1 and Ri ≤ Ri+1. Let ai be the number of students of level i, then |A| − f(A) = ai − k · (Ri − Li + 1), where A denotes the set of students of level i. Our job is to find max

|A| − f(A), so we need to select some levels to maximize the expression. The problem is the segments in the second part can intersect, but we only need to count them once.

A

Let’s define d(i) as the maximum value of |A| − f(A) if we only selected levels ≤ i and level i is selected. Then, either d(i) = dj +ai −k ·(Ri −Li +1) for some j < i, or d(i) = d(i−1)+ai −k ·(Ri −Ri−1). This is based on the fact that if some two levels are selected, and their segments [Li,Ri] and [Lj,Rj] intersect, then all levels between them should also be selected because the size of the right part is the same, but the size of the left part is increased.

In the first case, d(i) = dj + ai − k · (Ri − Li + 1), we suppose that [Li,Ri] and [Lj,Rj] don’t intersect, in the second one that they do intersect. But, in the first case, you can consider all possible j < i because if there is an intersection, then it counts all the vertices in the right part twice, which gives a smaller result.

To calculate d(i), we need to store d(i − 1) and max dj. j<i

For simplicity, we’ll refer to ai − k · (Ri − Li + 1) as openi, and to ai − k · (Ri − Ri−1) as addi. Then the formulas look like d(i) = dj + openi and d(i) = di−1 + addi. We can think about it as a vector (x,y) (in which x = d(i − 1), and y = max dj). The transition from i to i + 1 is a new vector, which is calculated as (max{y + openi,x + addi},max{y,y + openi,x + addi}). You can represent it as a matrix with an unusual multiplication definition cij = max j<i aik +bkj. With these definitions, the transition calculation becomes: k d(i + 1) max d(i) max addi openi addi max{0,openi}

⊕ dj = dj j≤i j<i

Now we can finally solve the problem using a segment tree that stores matrices and their multiplications. For every query, only one leaf of the segment tree changes its value. Thus, the solution works in O((n + m)log n).

# Citations

1. [Условия задач/разбор: Задачи(ru) Задачи(en) — round1-solutions-en](https://lk-dovuz.innopolis.university/public/files/round1-solutions-en.pdf), file 35532c84188a

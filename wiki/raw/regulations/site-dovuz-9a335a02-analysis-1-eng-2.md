---
type: regulation
title: "Analysis 1 ENG"
resource: "https://lk-dovuz.innopolis.university/public/files/Analysis_1_ENG_%282%29.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/Analysis_1_ENG_%282%29.pdf"
    id: "0efcbbf9ee65"
    title: "Analysis 1 ENG"
    last_modified: "2026-11-01T23:17:18+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:18+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Analysis 1 ENG

1 Lebron and the multiverse

Problem statement: Lebron scored r three-point and t two-point shots in the basketball game, but in the «42» universe, k points are deducted from a player’s performance until his performance becomes less than k.

Subtask 2

Let’s find the total number of points that Lebron scored, this is sm = 3 · r + 2 · t. We will subtract k until sm ≥ k.

2 r = int(input())

3 t = int(input())

4 k = int(input())

5 sm = 3 * r + 2 * t

6 while sm >= k:

7 sm -= k

8 print(sm)

Subtask 3

To solve for a full score, you need to understand that after executing the loop, we get the remainder of the division by k.

1 r = int(input())

2 t = int(input())

3 k = int(input())

4 print((3 * r + 2 * t) % k)

The answer may not fit into a 32-bit integer type, so you should use 64-bit integers such as long long in C++ to avoid integer type overflow.

2 Lebron and the problem

Problem statement: Given a rectangle with sides n and m, the coordinates of the lower left corner of the rectangle are (0;0). It is necessary to find the number of right triangles whose vertices have integer coordinates and are inside the rectangle (the vertices can lie on the sides of the rectangle), and also one of the sides is parallel to the Ox axis, and the second to the Oy axis.

Subtask 1 Constraints allow you to iterate over all points and count the number of suitable triangles.

Subtask 2

Let’s fix some point A(x1;y1), then the other two points can only be located on the lines x = x1 and y = y1. To count the number of triangles, we will have to iterate over the two remaining points on these lines. Let’s estimate the running time of this algorithm: we need to iterate over the coordinates of one point — O(n · m), for the other two — only one coordinate O(n · m), as a result O(n2 · m2).

1 n = int(input())

2 m = int(input())

4 ans = 0

5 for x1 in range(n+1):

6 for y1 in range(m+1):

7 for y2 in range(m+1):

8 if y1 == y2:

9 continue

11 for x3 in range(n+1):

12 if x1 == x3:

13 continue

14 ans += 1

15 print(ans)

Subtask 3

To solve the problem for a full score, let’s estimate the exact number of iterations that these loops do:

1 for y2 in range(m+1):

2 if y1 == y2:

3 continue

5 for x3 in range(n+1):

6 if x1 == x3:

7 continue

8 ans += 1

A loop with the variable x3 does n iterations, and a loop with y2 does m iterations, it turns out that in nested loops m · n units are added to the variable ans. Replace these two loops with ans+ = n · m. The asymptotics of the solution has now become O(n · m).

Additional subtask

This problem can be solved in O(1) asymptotics, for such a solution, you can once again make an accurate estimate of the number of iterations and modify the formula.

1 n = int(input())

2 m = int(input())

3 print(n*m*(n+1)*(m+1))

The answer may not fit into a 32-bit integer type, so you should use 64-bit integers such as long long in C++ to avoid integer type overflow.

3 Gift to Lebron

Problem statement: An array of n integers is given. It is necessary to say for each prefix whether there are exactly two different numbers that occur the same number of times on this prefix.

Subtask 1

In the first subtask ai ≤ 100, let’s iterate over the numbers from 1 to 100 on each prefix and count how many each number occurs. Now it remains to check whether there are two numbers that occur the same number of times.

1 n = int(input())

2 a = list(map(int , input().split()))

3 for i in range(n):

4 b = a[:i+1]

6 cnt = []

7 for j in range(1, 101):

8 tmpCnt = b.count(j)

9 if tmpCnt > 0:

10 cnt.append(tmpCnt)

12 ans = False

13 for j in range(n+1):

14 if cnt.count(j) == 2:

15 ans = True

16 break

18 if ans:

19 print("YES")

20 else:

21 print("NO")

Subtask 2

In the second subtask 1 ≤ ai ≤ 2, we will use this condition to solve. Let’s create two variables one and two, in which we will count the number of ones and twos on the prefix, respectively. During the processing of a new element, we will add a unit to one of the variables, after which we need to check whether their number is the same.

1 n = int(input())

2 a = list(map(int , input().split()))

4 one = 0

5 two = 0

7 for i in range(n):

8 if a[i] == 1:

9 one += 1

10 else:

11 two += 1

13 if one == two:

14 print("YES")

15 else:

16 print("NO")

Alternative solution to the subtask 1

Before presenting the solution of subtask 3, let us consider another solution of the first subtask. Restrictions on the array element 1 ≤ ai ≤ 100. Let’s create an array cnt, in which we will maintain how many times k occurs, where k = 1,2,...,100. When we process a new element ai, we will add a unit to the cell of the array ai, that is, cnt[ai]+ = 1. Now it remains to find exactly two elements that will have the same value, for this we will use the solutions described above.

1 n = int(input())

2 a = list(map(int , input().split()))

5 mx = max(a)

6 cnt = [0] * (mx + 1)

9 for i in range(n):

10 cnt[a[i]] += 1

12 ans = False

13 for j in range(1, n+1):

14 if cnt.count(j) == 2:

15 ans = True

16 break

18 if ans:

19 print("YES")

20 else:

21 print("NO")

Subtask 3

Note that you can reuse the technique with an array, but to count the number of each element of the array cnt. Now, to check that there are exactly two elements on the prefix that occur the same number of times, we need to go through the cnt2 array.

1 n = int(input())

2 a = list(map(int , input().split()))

4 mx = max(a)

5 cnt = [0] * (mx + 1)

7 cnt2 = [0] * (n+1)

8 for i in range(n):

9 if cnt2[cnt[a[i]]] != 0:

10 cnt2[cnt[a[i]]] -= 1

12 cnt[a[i]] += 1

13 cnt2[cnt[a[i]]] += 1

15 ans = False

16 for j in range(1, n+1):

17 if cnt2[j] == 2:

18 ans = True

19 break

20 if ans:

21 print("YES")

22 else:

23 print("NO")

This implementation of the idea scored 50 points, but by slightly improving this solution, it was possible to get 65 points.

Subtask 4

To solve the problem for a full score, it should be noted that when processing a new element ai, the number of pairs of elements that can satisfy the answer changes by no more than 2. Let’s create a variable ans, which is responsible for the number of exactly two different numbers that occur the same number of times on this prefix. When processing a new number, there are several options for changing the variable ans (we believe that we have already added one to cnt[a[i]] and there have been changes in cnt2):

**1.** if cnt[a[i]] > 1 and cnt2[cnt[a[i]] − 1] == 1, then ans− = 1

**2.** if cnt2[cnt[a[i]] − 1] == 2, then ans+ = 1

**3.** if cnt2[cnt[a[i]]] == 3, then ans− = 1

**4.** if cnt2[cnt[a[i]]] == 2, then ans+ = 1

After changing ans, it remains only to check whether this variable is greater than 0, if yes, then the answer is YES, if not, then NO.

1 n = int(input())

2 a = list(map(int , input().split()))

4 mx = max(a)

5 ans = 0

6 cnt = [0] * (mx + 1)

7 cnt2 = [0] * (n+1)

9 for i in range(n):

10 if cnt2[cnt[a[i]]] != 0:

11 cnt2[cnt[a[i]]] -= 1

13 if cnt2[cnt[a[i]]] == 1 and cnt[a[i]] > 0:

14 ans -= 1

16 if cnt2[cnt[a[i]]] == 2:

17 ans += 1

19 cnt[a[i]] += 1

20 cnt2[cnt[a[i]]] += 1

22 if cnt2[cnt[a[i]]] == 3:

23 ans -= 1

25 if cnt2[cnt[a[i]]] == 2:

26 ans += 1

28 if ans > 0:

29 print("YES")

30 else:

31 print("NO")

4 Lebron and dominoes

Problem statement: Given an array of pairs of numbers (dominoes). In a pair, the numbers can be swapped, it is necessary to find the maximum sequence of consecutive pairs in which any two sides touched with the same number.

Subtask 1

To solve the first subtask, it was possible to write a brute force algorithm.

Subtask 3

Note the fact that if we fix a certain position of a pair, then only one option for the location of the next pair is possible. Now let’s go through the beginning of the sequence and consider two options for the position of this domino. After that, we will simulate the construction.

1 n = int(input())

2 a = []

3 for i in range(n):

4 a.append(list(map(int , input().split())))

6 ans = 0

7 for i in range(n):

8 tmp = [1, 1]

9 for t in range(2):

10 last = a[i][t]

11 for j in range(i+1, n):

12 if last == a[j][0]:

13 last = a[j][1]

14 elif last == a[j][1]:

15 last = a[j][0]

16 else:

17 break

18 tmp[t] += 1

19 ans = max(ans , max(tmp))

20 print(ans)

Subtask 4

To solve the problem for a full score, you need to use the dynamic programming method. Let dp[i][0] — be the length of consecutive dominoes ending in i domino without its swap, and dp[i][1] — with a turn. The base of the dynamics is dp[i][0] = dp[i][1] = 1, since the minimum length is 1 (one domino is already a sequence). Transition options:

**1.** a[i − 1][1] == a[i][0], then dp[i][0] = max(dp[i][0],dp[i − 1][0] + 1)

**2.** a[i − 1][0] == a[i][0], then dp[i][0] = max(dp[i][0],dp[i − 1][1] + 1)

**3.** a[i − 1][1] == a[i][1], then dp[i][1] = max(dp[i][1],dp[i − 1][0] + 1)

**4.** a[i − 1][0] == a[i][1], then dp[i][1] = max(dp[i][1],dp[i − 1][1] + 1)

The answer is the maximum value among dp[i][0] and dp[i][1].

1 n = int(input())

2 a = []

3 for i in range(n):

4 a.append(list(map(int , input().split())))

6 ans = 1

7 dp = [[1, 1] for i in range(n)]

9 for i in range(1, n):

10 if a[i - 1][1] == a[i][0]:

11 dp[i][0] = max(dp[i][0], dp[i - 1][0] + 1)

13 if a[i - 1][0] == a[i][0]:

14 dp[i][0] = max(dp[i][0], dp[i - 1][1] + 1)

16 if a[i - 1][1] == a[i][1]:

17 dp[i][1] = max(dp[i][1], dp[i - 1][0] + 1)

19 if a[i - 1][0] == a[i][1]:

20 dp[i][1] = max(dp[i][1], dp[i - 1][1] + 1)

21 ans = max(ans , dp[i][0], dp[i][1])

22 print(ans)

5 Circles and basketball

Problem statement: Given n inequalities of the form (x − xi)2 + (y − yi)2 ≤ ri2. It is necessary to count the number of integer points (x,y) that satisfy at least one of the inequalities.

Subtask 1

Constraints allow you to iterate over integer points that can satisfy at least one of the inequalities. In order not to take into account the same points several times, you can use a two-dimensional Boolean array or Set. Asymptotics: O(2002 · n)

1 n = int(input())

2 inequalities = []

3 for i in range(n):

4 inequalities.append(list(map(int , input().split())))

6 used = set()

7 for x_i , y_i , r_i in inequalities:

8 for x in range(x_i - r_i , x_i + r_i+1):

9 for y in range(y_i - r_i , y_i + r_i+1):

10 if (x_i - x) * (x_i - x) + (y_i - y) * (y_i - y) <= r_i*r_i:

11 used.add((x, y))

12 print(len(used))

Subtask 2

After analyzing the constraints, it is clear that the coordinates of the points can be from −2 · 104 to 2·104. Let’s iterate over the line y = j and substitute y into the inequality (that is, we intersect the line y = j with the circle (x − xi)2 + (y − yi)2 = ri2).

(x − xi)2 + (y − yi)2 = ri2 (x − xi)2 = ri2 − (y − yi)2 x − xi = ± ri2 − (y − yi)2 x = xi ± ri2 − (y − yi)2

The entry ⌊x⌋ denotes rounding down the value of x (for instance, ⌊1.4⌋ = 1, ⌊2⌋ = 2). Since only integer points are suitable, the necessary points will have coordinates (⌊xi − ri2 − (y − yi)2⌋,y), (⌊xi − ri2 − (y − yi)2⌋ + 1,y), ..., (⌊xi + ri2 − (y − yi)2⌋,y). Satisfying points with the coordinate y = j total ⌊xi + ri2 − (y − yi)2⌋ − ⌊xi − ri2 − (y − yi)2⌋ + 1 = 2 · ⌊ ri2 − (y − yi)2⌋ + 1.

1 from math import sqrt

3 n = int(input())

4 inequalities = []

5 for i in range(n):

6 inequalities.append(list(map(int , input().split())))

8 cnt = 0

9 for y in range(-20000, 20001):

10 for x_i , y_i , r_i in inequalities:

11 if abs(y - y_i) > r_i:

12 continue

13 d = int(sqrt(r_i * r_i - (y - y_i) * (y - y_i)))

14 cnt += 2*d + 1

15 print(cnt)

Subtask 3

In this subtask n = 2, we will use the method already described in subtask 2. We will intersect the line with circles, but this time we will consider the location of the intersection points with the circle. There are 4 location options in total:

**1.** In this case, you need to check that the point B is to the left of C, so xB ≤ xc, the number of suitable points: (xB − xA + 1) + (xD − xC + 1)

**2.** In this case, the straight line will never intersect two circles at the same time

**3.** Here you need to check that the points are located in this order: A → C → B → D, that is xA ≤ xC ≤ xB ≤ xD, the number of suitable points: xD − xA + 1

**4.** In the fourth case, one circle is inside the other, that is xA ≤ xC ≤ xD ≤ xB, the number of suitable points: xB − xA + 1

1.

2.

**3.** 4.

1 from math import sqrt

3 n = int(input())

4 inequalities = []

5 for i in range(n):

6 inequalities.append(list(map(int , input().split())))

8 cnt = 0

9 for y in range(-20000, 20001):

10 points = []

11 for x_i , y_i , r_i in inequalities:

12 if abs(y - y_i) > r_i:

13 continue

14 d = int(sqrt(r_i * r_i - (y - y_i) * (y - y_i)))

15 points.append((x_i - d, x_i + d))

17 if len(points) == 0:

18 continue

20 points.sort()

21 tmp = 0

22 if len(points) == 1:

23 A, B = points [0]

24 tmp += B - A + 1

25 elif len(points) == 2:

26 A, B = points [0]

27 C, D = points [1]

29 if B < C:

30 tmp += B - A + 1 + D - C + 1

31 elif A <= C <= B <= D:

32 tmp += D - A + 1

33 else:

34 tmp += B - A + 1

35 cnt += tmp

37 print(cnt)

Subtask 4

To solve the fourth subtask, it is necessary to process the intersection of several segments for this we will use the scanning line method (ScanLine). It turns out that we need to count the number of points covered by segments on a straight line.

1 from math import sqrt

3 n = int(input())

5 x = [0]*n

6 y = [0]*n

7 r = [0]*n

8 for i in range(n):

9 x[i], y[i], r[i] = map(int , input().split())

12 plY = [[] for i in range(-20000, 20001)]

14 for i in range(n):

15 for lineY in range(y[i] - r[i], y[i]+r[i]+1):

16 if(abs(lineY - y[i]) > r[i]):

17 continue

18 d = int(sqrt(r[i]*r[i] - (lineY - y[i])**2))

19 x1 = x[i] - d

20 x2 = x[i] + d

22 plY[lineY].append((x1, -1))

23 plY[lineY].append((x2, 1))

25 ans = 0

26 for i in range(-20000, 20001):

27 if len(plY[i]) == 0:

28 continue

30 plY[i].sort()

31 cnt = 0

32 lastX = 0

33 for curX , curType in plY[i]:

34 cnt -= curType

36 if cnt == 0 and curType == 1:

37 ans += curX - lastX + 1

38 if cnt == 1 and curType == -1:

39 lastX = curX

41 print(ans)

# Citations

1. [Analysis 1 ENG](https://lk-dovuz.innopolis.university/public/files/Analysis_1_ENG_%282%29.pdf), file 0efcbbf9ee65

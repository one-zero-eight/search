---
type: regulation
title: "Финальный этап — contest-final 2020-21 — problems/polyline-drawing/statements/.pdf/english/tutorial.pdf"
resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
archive_member: "problems/polyline-drawing/statements/.pdf/english/tutorial.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
    id: "02714f8e909e"
    title: "Финальный этап — contest-final 2020-21 — problems/polyline-drawing/statements/.pdf/english/tutorial.pdf"
    last_modified: "2026-11-04T02:52:48+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-04T02:52:48+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Финальный этап — contest-final 2020-21 — problems/polyline-drawing/statements/.pdf/english/tutorial.pdf

Diamond Hands

For a better understanding, we can visualize this problem on a 2D plane and draw points (di,pi). Then the graph of stock price is a polyline starting at (0,0), all segments of which are directed to the right, having a ±45 degree angle with the OX axis.

First, let’s understand when there is no solution. Every day the stock price changes by one, so the sum di + pi is always even. If the input data contains at least one pair with an odd sum, then the answer is −1. Also, there is a restriction on how much the price can change between adjacent data points: for two pairs (di,pi) and (di+1,pi+1) the following inequality should be true: |pi+1 − pi| ≤ di+1 − di. These two conditions are sufficient.

There are two approaches to finding the answer with the minimum k. The first solution uses dynamic programming: let up[i] be the minimum number of segments in the polyline leading to point i, in which the last segment was going up, similarly for down[i]. We can transition from up[i] to down[i + 1], changing the direction once. When going from up[i] to up[i + 1] we have two cases: if pi+1 − pi = di+1 − di, then we can just extend the last segment and not add any new ones. Otherwise, we need to change the direction twice. Transitions starting at down[i] are similar. While restoring the answer, we need to calculate the point of changing direction, do it carefully. This solution works in O(n) time.

It turns out that in this DP solution the transition from up[i] to up[i + 1] (and its mirrored counterpart with down), when pi+1 −pi = di+1 −di is unnecessary. If the optimal solution contains this transitions, we can change it to up[i] → down[i + 1], the answer decreases by one, but the next transition might cost higher. If the next transition was up[i + 1] → up[i + 2] before (and now it’s down[i + 1] → up[i + 2]), then the modified polyline is not worse. If the next transition was up[i + 1] → down[i + 2] (and now it’s down[i + 1] → down[i + 2]), then the number of segments might increase if the transition down[i + 1] → down[i + 2] cost 2; in this case, we apply the same logic to it.

This means that if pi+1 − pi = di+1 − di, then we always transition to up[i + 1], else it’s always optimal to change the current direction. Based on this observation we can derive a greedy solution: let’s try both initial directions, then, if we can continue the current segment, we do it, otherwise we change the current direction to the opposite one. This solution also works in O(n) time.

Page 1 of 1

# Citations

1. [Финальный этап — contest-final 2020-21 — problems/polyline-drawing/statements/.pdf/english/tutorial.pdf](https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip), file 02714f8e909e

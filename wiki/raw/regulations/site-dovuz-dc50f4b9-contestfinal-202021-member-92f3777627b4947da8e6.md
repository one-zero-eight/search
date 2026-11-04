---
type: regulation
title: "Финальный этап — contest-final 2020-21 — problems/rooted-mst/statements/.pdf/russian/problem.pdf"
resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
archive_member: "problems/rooted-mst/statements/.pdf/russian/problem.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
    id: "c198e4500d9f"
    title: "Финальный этап — contest-final 2020-21 — problems/rooted-mst/statements/.pdf/russian/problem.pdf"
    last_modified: "2026-11-04T02:52:48+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-04T02:52:48+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Финальный этап — contest-final 2020-21 — problems/rooted-mst/statements/.pdf/russian/problem.pdf

Rooted MST

Имя входного файла: стандартный ввод Имя выходного файла: стандартный вывод Ограничение по времени: 3 секунды Ограничение по памяти: 512 мегабайт

Вам дан простой неориентированный граф содержащий n+1 вершин пронумерованных 0,1,...,n и n + m ребер. Вес ребра между вершинами 0 и i равен ai для 1 i n. Вес ребра между вершинами ui и vi равен wi для 1 i m. Вам нужно ответить на q запросов, каждый запрос содержит два целых числа i,w, вам нужно поменять вес ребра между вершинами 0 и i на w и найти вес минимального остовного дерева в графе.

Обратите внимание, что запросы перманенты, т.е. изменения остаются навсегда.

Формат входных данных

В первой строке записаны два целых числа n,m (2 n 300000,0 m 300000). Во второй строке записаны n целых чисел a1,a2,...,an (1 ai 109). В каждой из следующих m строк записаны три целых числа ui,vi,wi

(1 ui,vi n,0 wi 109). Гарантируется, что данный граф простой, а именно не содержит петель и кратных ребер. В следующей строке записано одно целое число q (1 q 300000). В каждой из следующих q строк записаны два целых числа i,w (1 i n,1 w 109).

Формат выходных данных

В каждой строке выведите одно целое число — вес минимального остовного дерева в графе после i запросов.

Система оценки

| Подзадача | Баллы | Ограничения |
| --- | --- | --- |
| 1 | 10 | n,m,q 2000 |
| 2 | 10 | Все веса равны 1 или 2 |
| 3 | 10 | w = 1 во всех запросах |
| 4 | 10 | i = 1 во всех запросах |
| 5 | 10 | i 5 во всех запросах |
| 6 | 10 | m = n − 1,ui = vi − 1 |
| 7 | 20 | n,m,q 150000 |
| 8 | 20 | Нет дополнительных ограничений |

Пример

| стандартный ввод | стандартный вывод |
| --- | --- |
| 5 7 3 2 1 2 1 1 5 1 1 3 2 2 5 2 4 5 2 3 4 1 2 4 2 1 2 1 10 3 2 2 3 4 1 3 2 5 1 5 3 3 1 2 3 4 3 5 1 | 6 6 5 5 5 6 6 6 6 5 |

# Citations

1. [Финальный этап — contest-final 2020-21 — problems/rooted-mst/statements/.pdf/russian/problem.pdf](https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip), file c198e4500d9f

---
type: regulation
title: "contest-final 2020-21 — problems/long-puzzle/statements/.pdf/russian/problem.pdf"
resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
archive_member: "problems/long-puzzle/statements/.pdf/russian/problem.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip"
    id: "99f4e98dc6eb"
    title: "contest-final 2020-21 — problems/long-puzzle/statements/.pdf/russian/problem.pdf"
    last_modified: "2026-11-04T02:52:48+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-04T02:52:48+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# contest-final 2020-21 — problems/long-puzzle/statements/.pdf/russian/problem.pdf

Long puzzle

Имя входного файла: стандартный ввод Имя выходного файла: стандартный вывод Ограничение по времени: 2 секунды Ограничение по памяти: 512 мегабайт

Вы собираете одномерный пазл. Каждая его деталь характеризуется тремя параметрами: длиной, типом левой границы и типом правой границы. Границы бывают трех типов: плоская, выпуклая и вогнутая. Детали нельзя разворачивать, то есть менять местами левую и правую границы. Любая выпуклая граница стыкуется с любой вогнутой и наоборот. Стыковать детали плоскими границами нельзя.

Рис. 1: Примеры деталей

Вы хотите соединить последовательно несколько деталей (возможно, одну), чтобы получился кусок длины l. Левая и правая границы куска должны быть плоскими. Найдите количество под-множеств деталей, из которых можно собрать требуемый кусок, по модулю 1000000007. Обратите внимание, что вам нужно найти именно количество различных подмножеств деталей, а не количество различных способов, которыми можно детали соединить.

Формат входных данных

В первой строке даны два целых числа n и l — количество деталей пазла и требуемая длина собранного куска (1 n 300, 1 l 300).

В следующих n строках дано описание деталей пазла. Каждая строка содержит ai, bi и ci — длину детали, тип левой границы и тип правой границы, соответственно (1 ai l; bi,ci ∈ {«in»,«out»,«none»}). Строка «in» соответствует вогнутой границе, «out» — выпуклой, «none» — плоской.

Формат выходных данных

Выведите одно целое число — остаток от деления количества подмножеств деталей, из которых можно собрать требуемый кусок, на 1000000007.

Система оценки

| Подзадача | Баллы | Ограничения |
| --- | --- | --- |
| 1 | 20 | n 20 |
| 2 | 20 | bi ∈ {«in»,«none»}, ci ∈ {«out»,«none»} |
| 3 | 20 | n,l 50 |
| 4 | 20 | n,l 100 |
| 5 | 20 | Без дополнительных ограничений |

Примеры

| стандартный ввод | стандартный вывод |
| --- | --- |
| 5 10 1 out out 6 none in 10 none none 4 out none 3 in none | 3 |
| 4 5 1 none out 1 in out 2 in out 1 in none | 1 |

Замечание

Детали пазла из первого примера соответствуют иллюстрации выше.

Рис. 2: Подмножества деталей, из которых можно собрать кусок требуемой длины

# Citations

1. [contest-final 2020-21 — problems/long-puzzle/statements/.pdf/russian/problem.pdf](https://lk-dovuz.innopolis.university/public/files/contest-final_2020-21.zip), file 99f4e98dc6eb

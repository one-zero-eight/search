---
type: page
title: "Система сравнения карт, полученных с помощью различных алгоритмов картографирования, с эталонными картами"
description: "Программа предназначена для сравнения карт, полученных с помощью алгоритмов SLAM (одновременной локализации и картографирования) с эталонными картами."
resource: "https://robotics.innopolis.university/patent/sistema-sravneniya-kart-poluchennyh-s-pomoshhyu-razlichnyh-algoritmov-kartografirovaniya-s-etalonnymi-kartami/"
audience: ["student", "postgraduate", "applicant", "teacher", "staff", "management", "public"]
source_kind: website
language: ru
section: "site/robotics"
sources:
  - resource: "https://robotics.innopolis.university/patent/sistema-sravneniya-kart-poluchennyh-s-pomoshhyu-razlichnyh-algoritmov-kartografirovaniya-s-etalonnymi-kartami/"
    id: "3c1dd37cbf4e"
    title: "Система сравнения карт, полученных с помощью различных алгоритмов картографирования, с эталонными картами"
    last_modified: "2026-10-31T09:03:09+00:00"
generated:
  by: "catix-wiki/0.1 sites"
  at: "2026-10-31T09:03:09+00:00"
status: draft
---

# Система сравнения карт, полученных с помощью различных алгоритмов картографирования, с эталонными картами

Вернуться

21.05.2019

Программа предназначена для сравнения карт, полученных с помощью алгоритмов SLAM (одновременной локализации и картографирования) с эталонными картами. Карты представляются в виде сетки заполненности (Occupancy Grid), где каждая клетка сетки представляет из себя участок в физическом мире, и ячейка может принимать одно из двух значений (занято или свободно). Программа строит эталонную карту, полученную с помощью высокоточных измерений, затем строятся карты с помощью алгоритмов SLAM и сохраняются в виде Occupancy Grid. После чего используется алгоритм ICP (итеративный алгоритм ближайших точек) для сопоставления двумерных облаков точек и вычисляется ошибка как сумма расстояний до ближайшего соседа.

_Меню, подвал и другие блоки, которые повторяются на страницах сайта, собраны в одном месте: [/raw/sites/robotics/_shared.md](/raw/sites/robotics/_shared.md)._

# Citations

1. [Система сравнения карт, полученных с помощью различных алгоритмов картографирования, с эталонными картами](https://robotics.innopolis.university/patent/sistema-sravneniya-kart-poluchennyh-s-pomoshhyu-razlichnyh-algoritmov-kartografirovaniya-s-etalonnymi-kartami/), read 2026-10-31

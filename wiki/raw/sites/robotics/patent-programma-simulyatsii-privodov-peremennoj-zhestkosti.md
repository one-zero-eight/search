---
type: page
title: "Программа симуляции приводов переменной жесткости"
description: "При конфигурировании заданных строк в urdf описании робота, программа изменяет тип сустава в роботе на сустав с приводом переменной жёсткости."
resource: "https://robotics.innopolis.university/patent/programma-simulyatsii-privodov-peremennoj-zhestkosti/"
audience: ["student", "postgraduate", "applicant", "teacher", "staff", "management", "public"]
source_kind: website
language: ru
section: "site/robotics"
sources:
  - resource: "https://robotics.innopolis.university/patent/programma-simulyatsii-privodov-peremennoj-zhestkosti/"
    id: "180604a7d22e"
    title: "Программа симуляции приводов переменной жесткости"
    last_modified: "2026-10-31T09:03:15+00:00"
generated:
  by: "catix-wiki/0.1 sites"
  at: "2026-10-31T09:03:15+00:00"
status: draft
---

# Программа симуляции приводов переменной жесткости

Вернуться

21.05.2019

При конфигурировании заданных строк в urdf описании робота, программа изменяет тип сустава в роботе на сустав с приводом переменной жёсткости. После изменения типа сустава, при заполнении полей command_topic и pos_topic, программа создает в ROS два новых потока сообщений, на которые можно подписаться. Первый поток отдает команды на выставление нужного положения. Второй поток отдает текущее положение сустава и внутренних моторов. В программе реализована динамика внутренних моторов, которая адаптируется под разные типы приводов. Программа разработана в Центре технологий компонентов робототехники и мехатроники.

_Меню, подвал и другие блоки, которые повторяются на страницах сайта, собраны в одном месте: [/raw/sites/robotics/_shared.md](/raw/sites/robotics/_shared.md)._

# Citations

1. [Программа симуляции приводов переменной жесткости](https://robotics.innopolis.university/patent/programma-simulyatsii-privodov-peremennoj-zhestkosti/), read 2026-10-31

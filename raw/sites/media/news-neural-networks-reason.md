28 августа 2026
## Учёные Университета Иннополис обнаружили у нейросетей скачок в способности к рассуждению
28 августа 2026
Исследователи обнаружили, что компактные рекурсивные ИИ-модели способны решать сложные задачи на пространственное мышление там, где классические трансформеры сопоставимого размера терпят крах. Для этого необходимо применять рекурсивное мышление. Результаты научной работы могут изменить подход к созданию систем искусственного интеллекта для устройств с ограниченными вычислительными ресурсами.
![](https://media.innopolis.university/upload/iblock/b70/okpgwzpbieaf1q1myhp0gmcqn6qrcnoi/_DUFsCXyXtz6yEDILK9kQ0vMF78YDPcWbtJN2j_Iut6gguFSPPEjNDUACiovJHGazHzhqkTII83Qkji_cH_zH-E2.jpg)
Современные большие языковые модели строятся по принципу «глубже — значит умнее»: чем больше слоёв и параметров, тем лучше результат. И мировые корпорации тратят миллиарды на создание моделей с триллионами параметров. Исследователи Университета Иннополиса проверили альтернативный путь — рекурсивное мышление. Вместо наращивания числа параметров предложенная ими модель многократно обрабатывала информацию одним и тем же компактным блоком: она «думала» над ответом несколько раз, последовательно уточняя его, а рядом с промежуточным решением хранила скрытый вектор — аналог «хода мысли».
Проверили обе ИИ-архитектуры на сборке разрезанных изображений — пазлов. По словам авторов, эта задача идеально подошла для теста: она требовала от модели одновременно локального сопоставления текстур и глобального пространственного планирования — сочетания, которое до сих пор давалась с трудом даже большим визуально-языковым моделям.
Простые пазлы 2×2 обе архитектуры собрали верно примерно в 95% случаях. Но с ростом сложности картина менялась. В сборке пазла 5×5 рекурсивная модель достигла точности 94,15%, тогда как классический трансформер с тем же числом параметров (около 0,7 млн) — лишь 57,61%. За это рекурсивная модель платит вычислениями: ей требуется примерно в 20 раз больше операций. Попытка «догнать» её простым наращиванием глубины трансформера провалилась: точность классической архитектуры пиковала на шести слоях, а 12-слойная версия вовсе переставала обучаться на сложных пазлах 5×5 и 6×6. При этом рекурсивная модель с увеличенной до 12 шагов глубиной «размышления» собирала пазлы 6×6 с точностью 76%.
![](https://media.innopolis.university/upload/medialibrary/c8d/ef8h1ip6awcr7giu1w9uu5ruqwuarqka/content-img.png)
Промежуточные результаты компактной ИИ-модели по сборке пазла на разных шагах (итерациях)
Рустам Лукманов, заместитель директора Института анализа данных и ИИ Университета Иннополис: «Одним из наиболее интересных наблюдений в ходе экспериментов стал эффект “внезапного обучения”. В отличие от классических ИИ-моделей, которые плавно улучшают показатели, компактная рекурсивная модель продемонстрировала фазовый переход: после длительного периода стагнации произошло резкое падение ошибки, сигнализирующее о возникновении логического обобщения. Момент этого перехода зависит от сложности задачи и глубины рекурсии, что позволяет точно настраивать модель под конкретные требования».
Авторы показали, что момент «внезапного обучения» закономерно сдвигался с ростом сложности задачи: время наступления фазового перехода росло экспоненциально, а уровень ошибки в этот момент — логарифмически, причём обе зависимости описывались одним и тем же базовым параметром. Это указывает на единый механизм, управляющий динамикой таких переходов.
Рекурсивный подход оказался применим не только к абстрактным логическим задачам вроде судоку, но и к визуально обоснованному пространственному мышлению — сборке пазлов. Исследователи сделали практический вывод: глубину «мышления» модели можно увеличивать не за счёт роста её размера, а за счёт времени на «размышление». Благодаря компактности — менее миллиона параметров — такие модели могут работать на обычных пользовательских устройствах и в условиях ограниченного вычислительного бюджета.
Статья «Глубина против рекурсии: превосходство над трансформерами в восстановлении пазлов» [опубликована](https://iclr.cc/virtual/2026/10018743) в сборнике одной из ведущих мировых конференций в области ИИ и машинного обучения ICLR 2026. Её авторы — исследователи Университета Иннополис Тимофей Брайко, Артемий Мясоедов и Рустам Лукманов. Исследование выполнено при поддержке Минэкономразвития России.
[Читать далее](https://media.innopolis.university/news/knowledge-day-2026/)
Новости по теме
[30 октября 2026](https://media.innopolis.university/news/students-projects-kdw-2026/)
[На Kazan Digital Week студенты Университета Иннополис и Колледжа Иннополис презентовали разработанные ИИ-решения](https://media.innopolis.university/news/students-projects-kdw-2026/)
[30 октября 2026](https://media.innopolis.university/news/oil-and-gas-digital-alliance/)
[Университет Иннополис вместе с «Газпром нефтью» и 4 партнёрами вошёл в альянс по цифровизации добычи углеводородов](https://media.innopolis.university/news/oil-and-gas-digital-alliance/)
[29 октября 2026](https://media.innopolis.university/news/agreement-alfa-bank-kdw-2026/)
[Университет Иннополис и Альфа-Банк будут совместно готовить ИТ-специалистов для финансового сектора](https://media.innopolis.university/news/agreement-alfa-bank-kdw-2026/)
## Популярные новости
[![](https://media.innopolis.university/upload/iblock/54d/fbqy2ab6dh61rv29in78kjmpiyg6c849/fa_ZdIwgjAn-dC8WaAWYzegFXO79IN7Zj2PcdytlmUlo5-U9EB8MIW2_nwUXtl681KPkWsZE2j0A0nHda9c5LgRq.jpg)](https://media.innopolis.university/news/Industrial-Robotics-Centres-Contest-Results-2026/)
[13 октября 2026](https://media.innopolis.university/news/Industrial-Robotics-Centres-Contest-Results-2026/)
## [В российских вузах и компаниях откроются 13 новых центров развития промышленной робототехники](https://media.innopolis.university/news/Industrial-Robotics-Centres-Contest-Results-2026/)
[Каждый центр получит грант до 500 млн рублей на 3 года на разработку и коммерциализацию технологических решений в промышленной робототехнике, внедрение роботизированных ячеек и комплексов на предприятиях и обучение сотрудников. Конкурс организовали Минпромторг России и Университет Иннополис, а итоги подвела экспертная комиссия во главе с директором ИТ-вуза Дмитрием Вандюковым. Теперь в федеральную сеть входит 21 центр развития промышленной робототехники. Программа реализуется в рамках национального проекта «Средства производства и автоматизации».](https://media.innopolis.university/news/Industrial-Robotics-Centres-Contest-Results-2026/)
[![](https://media.innopolis.university/upload/iblock/e90/8c9jewpdf1v33dwy9h5t3ao51ayc5r53/IMG_7902.JPG)](https://media.innopolis.university/news/worlds-most-influential-scientists-ranking/)
[14 октября 2026](https://media.innopolis.university/news/worlds-most-influential-scientists-ranking/)
## [Ректор Университета Иннополис вошёл в 2% самых влиятельных учёных мира в области ИИ](https://media.innopolis.university/news/worlds-most-influential-scientists-ranking/)
[Александр Гасников вошёл в топ-2% самых влиятельных мировых исследователей искусственного интеллекта. Это следует из ежегодного международного рейтинга, который составляют издательство Elsevier и Стэнфордский университет (признан в РФ нежелательной организацией).](https://media.innopolis.university/news/worlds-most-influential-scientists-ranking/)
[![](https://media.innopolis.university/upload/iblock/094/qube3pt4m6i4rdlz44hbqd2u4eh1vs1f/u4EsaVgKwNEezd4_c4136ox_hnfOyRlzXq4mfOecrkp76Q0Sr6gyTrXX5zWbssXTDKFZcPeXH9_Hg6Kkkiis0Q==.jpeg)](https://media.innopolis.university/news/free-webinars-october-2026/)
[6 октября 2026](https://media.innopolis.university/news/free-webinars-october-2026/)
## [Бесплатные мастер-классы и вебинары Университета Иннополис по программированию, физике и математике в октябре](https://media.innopolis.university/news/free-webinars-october-2026/)
[Центр довузовской подготовки ИТ-вуза проведёт серию образовательных онлайн-мероприятий для учеников 6—11 классов, учителей и родителей. Участники узнают, как создавать видеоигры, социальные сети и головоломки, а также решать математические олимпиадные задания и задачи по динамическому программированию. Спикерами выступят инструкторы по программированию и сотрудники Университета Иннополис. Для участия необходима регистрация. Количество мест ограничено.](https://media.innopolis.university/news/free-webinars-october-2026/)
Все новости
Все медиа
Вконтакте
Youtube
habr
- [Абитуриентам](https://apply.innopolis.university/)
- [Бизнесу](https://media.innopolis.university/proekty/activity/)
- [Медиа](https://media.innopolis.university/)
- [Сайт Университета Иннополис](https://innopolis.university/)
- [Мероприятия](https://media.innopolis.university/events/)
[Telegram](https://t.me/universityinnopolis)
[VK](https://vk.com/innopolisu)
[YouTube](https://www.youtube.com/channel/UCvCTv7cC1yFBFofSm2xWHCQ/videos)
[Max](https://max.ru/id1655258235_biz)
- [Об университете](https://innopolis.university/about/)
- [Абитуриентам](https://apply.innopolis.university/?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- [Курсы повышения квалификации](https://innopolis.university/dpo-courses/?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- [Проектная деятельность](https://innopolis.university/proekty/activity/)
- [Передовая инженерная школа](https://engineerschool.innopolis.university/)
- [Вакансии](https://career.innopolis.university/job?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- [Мерч](http://iustore.innopolis.ru/?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- [Виртуальная экскурсия](https://panoroo.com/virtual-tours/NvQZM6B2?lang=ru&id=12&site=s1&template=university24&landing_mode=edit)
- [Онлайн-курсы и повышение квалификации](https://t.me/inno_university_it_bot)
Контакты
- +7 (843) 203-92-53
- university@innopolis.ru
- 420500, г. Иннополис ул.Университетская, д.1
- [Как добраться](http://www.innopolis.com/city/how-to-get/?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- Ещё контакты
Пресс-служба
- pr@innopolis.ru
- [Новости](https://media.innopolis.university/?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- [Мероприятия](https://media.innopolis.university/events/?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
Полезные ссылки
- [Сведения об образовательной организации](https://innopolis.university/sveden/)
- [Министерство цифрового развития, связи и массовых коммуникаций РФ](https://digital.gov.ru/ru/?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- [Министерство науки и высшего образования Российской Федерации](https://minobrnauki.gov.ru/?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- [Министерство просвещения Российской Федерации](https://edu.gov.ru/)
- [Конкурс на замещение вакантных должностей ППС](https://career.innopolis.university/konkursnyezayavkiprofessorskoprepodavatelskogosostava/)
- [Политика конфиденциальности](https://innopolis.university/files/politicacookies.pdf?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- [«Горячая линия» ситуационного центра (COVID-2019): +7 (495) 198-00-00](https://www.minobrnauki.gov.ru/action/situational_center/?lang=ru&id=396&site=s1&template=university24&landing_mode=edit)
- [Антитеррористическая деятельность](https://innopolis.university/antiterror/)
- Скачать PDF, содержащий материалы страницы
## Мы используем файлы cookies
Они помогают улучшить работу сайта и сделать его удобнее. Посещая страницы сайта, вы соглашаетесь с [условиями использования](https://media.innopolis.university/public/files/Согласие%20на%20обработку%20ПДн%20для%20УИ.pdf) файлов cookie.
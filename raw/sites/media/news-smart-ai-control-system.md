4 февраля 2026
## Университет Иннополис запатентовал умную систему управления беспилотниками на основе нейросетей
4 февраля 2026
- [Индустрия](https://media.innopolis.university/?TAGS=Индустрия)
- [Наука](https://media.innopolis.university/?TAGS=%20Наука)
Российские исследователи изобрели новый способ управления автономным транспортом с применением сквозного обучения нейронных сетей и получили на него евразийский патент. Разработка позволяет автомобилю напрямую, без сложной ручной обработки, интерпретировать данные с камер и лидаров, прогнозировать траекторию и выдавать команды для движения. Это станет основой для более безопасных, надёжных и самостоятельных автономных систем, способных работать в сложных погодных и дорожных условиях, минимизируя риски, связанные с человеческим фактором.
![](https://media.innopolis.university/upload/iblock/8bb/ldukqn6eurmpf2v5chh2jvw9gmtp9jlv/IMG_1068.jpg)
Изобретение решает ключевую проблему создания точных и производительных систем для автономного транспорта. По словам разработчиков, традиционные подходы часто требуют раздельной обработки сигналов от разных датчиков и сложной ручной настройки алгоритмов. Предложенный в Университете Иннополис метод основан на сквозном обучении. Эксперты обучили нейронную сеть TransFuser на входных сигналах — необработанных пикселях изображений с камер и точках облака данных с лидара, которые, выявляя сложные паттерны в данных, сразу генерируют управляющие команды: продолжать движение, объехать препятствие, повернуть или остановиться.
Архитектура модели TransFuser состоит из двух частей, имитирующих процесс принятия решений водителем: сети синтеза и прогнозирования. Сеть синтеза на основе трансформера выступает в роли «мозга», отвечающего за восприятие окружающей обстановки. Она разделена на две параллельные ветви, обрабатывающие информацию разного типа: ветвь изображения анализирует картинку с камеры при помощи серии свёрточных кодировщиков, извлекая визуальные признаки и мелкие детали, а ветвь вида с высоты птичьего полёта обрабатывает облако точек с лидара. Это даёт системе точное геометрическое и пространственное понимание трёхмерной структуры окружающего мира: расположение препятствий, рельефа, дистанции между объектами.
Модуль трансформера выполняет ключевую операцию — совместно обрабатывает и синтезирует информацию от обеих ветвей. Его ядро вычисляет значимость каждого элемента данных относительно других. Например, система может определить, что светофор на изображении соответствует конкретному участку в 3D-пространстве и оценить приоритет этой информации для управления автомобилем.
Сеть прогнозирования пути получает обогащённые и объединённые признаки от трансформера и прогнозирует оптимальную траекторию движения беспилотного автомобиля на несколько шагов вперед. Эти данные затем поступают на стандартные пропорционально-интегрально-дифференцирующие регуляторы, которые непосредственно управляют рулевым механизмом, ускорением и торможением транспортного средства.
Бадер Рашид, старший научный сотрудник Лаборатории инновационных технологий обработки видеоконтента Университета Иннополис: «Для повышения надёжности и способности модели к обобщению в процесс обучения нейросетей мы включили четыре вспомогательные задачи: оценку глубины по 2D-изображению, семантическую сегментацию сцены, построение детальной HD-карты дороги и детекцию 3D-объектов с помощью ограничивающих параллелепипедов. Это позволило ИИ сформировать более целостное и устойчивое представление об окружающей среде».
Эффективность архитектуры изобретения подтверждена в нескольких средах. Первичное обучение и тестирование проводились в реалистичном симуляторе городского движения CARLA. Для оценки способности модели работать с реальными данными специалисты использовали признанный мировой эталон — открытый набор данных KITTI Vision, содержащий синхронизированные записи с камер и лидаров реального автомобиля.
Мостафа Хегази, ассистент Лаборатории интеллектуальных робототехнических систем Университета Иннополис: «Важно, что гибкость подхода позволила адаптировать наш метод и для других типов беспилотных транспортных средств. Наша команда успешно перенесла и протестировала модель на данных, полученных c беспилотных судов, что демонстрирует универсальность предложенной архитектуры для различных сред передвижения».
![photo_2023-11-02_21-45-31.jpg](https://media.innopolis.university/upload/medialibrary/f63/uh709ghoy1kn4c4qyzryl9dizi3r6e4c/photo_2023-11-02_21-45-31.jpg)
Найденные с помощью разработанной модели объекты во время тестирования на беспилотном судне
Метод [запатентовали](https://www.eapo.org/pubservices/info/publications/pub?applicationNumber=202493133&documentCode=B1&publicationDate=2026.01.14&region=EA&ipType=InventionPublication) эксперты Межотраслевого центра трансфера технологий Университета Иннополис. Патент действует на территории государств-участников Евразийской патентной конвенции: Азербайджана, Кыргызстана, Армении, Беларуси, Казахстана, Таджикистана, России и Туркменистана.
[Читать далее](https://media.innopolis.university/news/rimm-2026/)
Новости по теме
[30 октября 2026](https://media.innopolis.university/news/oil-and-gas-digital-alliance/)
[Университет Иннополис вместе с «Газпром нефтью» и 4 партнёрами вошёл в альянс по цифровизации добычи углеводородов](https://media.innopolis.university/news/oil-and-gas-digital-alliance/)
[29 октября 2026](https://media.innopolis.university/news/agreement-alfa-bank-kdw-2026/)
[Университет Иннополис и Альфа-Банк будут совместно готовить ИТ-специалистов для финансового сектора](https://media.innopolis.university/news/agreement-alfa-bank-kdw-2026/)
[22 октября 2026](https://media.innopolis.university/news/sapfir-ai-sprint/)
[Как писать научные статьи уровня A*: в Иннополисе провели экспертное мероприятие для молодых учёных](https://media.innopolis.university/news/sapfir-ai-sprint/)
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
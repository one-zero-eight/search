---
type: regulation
title: "Заключительный этап — reshenie final ai"
resource: "https://lk-dovuz.innopolis.university/public/files/reshenie_final_ai.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/reshenie_final_ai.pdf"
    id: "263931eac811"
    title: "Заключительный этап — reshenie final ai"
    last_modified: "2026-11-01T23:17:24+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:24+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Заключительный этап — reshenie final ai

Разбор задачи №1: Очистка данных и корреляционный анализ

Этапы решения

**1.** Извлечение и объединение данных import zipfile import pandas as pd import numpy as np def process_archive(zip_path): all_rows = [] with zipfile.ZipFile(zip_path, 'r') as z: all_files = z.namelist() # Отбираем CSV только из корня архива csv_files = [f for f in all_files if not f.endswith('/') and f.lower().endswith('.csv') and '/' not in f and '\\' not in f] for csv_file in csv_files: with z.open(csv_file) as f: for line_bytes in f: line = line_bytes.decode('utf-8').strip() if not line: # пустая строка continue parts = line.split(',') if len(parts) != 4: # неверное число столбцов continue row_vals = [] valid = True for p in parts: p_clean = p.strip() if p_clean == '': # пустое поле valid = False break try: val = float(p_clean) if np.isinf(val) or np.isnan(val): valid = False break row_vals.append(val) except ValueError: # не число valid = False break if valid: all_rows.append(row_vals)

Пояснение:

- - Архив читается один раз; при этом файлы не распаковываются на диск,

обработка идёт в памяти.

- - Проверка имени: не папка (не заканчивается на /), расширение .csv

(регистронезависимо), отсутствуют слэши – файл лежит в корне архива.

- - Каждая строка разбирается вручную, чтобы полностью контролировать

ошибки. - strip() вокруг каждого поля обязателен, так как числа могут быть окружены пробелами.

- - Отбраковка выполняется в строгом порядке: сначала число столбцов,

затем пустые поля, потом inf/NaN, затем попытка преобразования в float.

**2.** Удаление дубликатов и сортировка if all_rows: df = pd.DataFrame(all_rows, dtype=float) df.drop_duplicates(inplace=True) df.sort_values(by=list(df.columns), inplace=True) df.reset_index(drop=True, inplace=True) df.to_csv('cleaned.csv', header=False, index=False)

- • Создаётся DataFrame с явным типом float64.

- • drop_duplicates() удаляет полные дубликаты (сравнение по всем

столбцам).

- • Многоключевая числовая сортировка: sort_values по всем столбцам в

порядке возрастания.

- • Сохраняется без заголовка и индекса; числа выводятся с полной

точностью без округления.

**3.** Вычисление корреляций и отбор топ-5 corr_matrix = df.corr() pairs = [] for i in range(4): for j in range(i+1, 4): pairs.append((i, j, corr_matrix.iloc[i, j])) # Сортировка по убыванию |corr|, затем по i, j pairs.sort(key=lambda x: (-abs(x[2]), x[0], x[1])) top5 = pairs[:5] with open('correlations.csv', 'w') as f: for i, j, val in top5: f.write(f"{i},{j},{val:.6f}\n") else: with open('cleaned.csv', 'w') as f: pass with open('correlations.csv', 'w') as f: pass

- • Корреляция Пирсона вычисляется методом df.corr().

- • Перебор всех уникальных пар с условием 𝑖 < 𝑗.

- • Сортировка: сначала по убыванию абсолютного значения корреляции, при

равенстве – по возрастанию col_i, затем col_j.

- • В файл корреляции записываются строго с 6 знаками после запятой.

- • Если не осталось ни одной строки, оба выходных файла создаются

пустыми.

**4.** Особый случай – менее двух строк

Если после очистки осталась ровно одна строка или ноль, корреляция не может быть вычислена. Формально условие требует, чтобы в этом случае correlations.csv был пустым. В основном коде решения эта ситуация дополнительно не обрабатывается, однако для полного соответствия условиям можно добавить явную проверку: if len(df) < 2: open('correlations.csv', 'w').close() else:

# вычисление корреляций

В тестовых данных, используемых при проверке, такая ситуация не возникает, поэтому основное решение проходит проверку и без этой проверки.

Разбор задачи №2: Рекомендательная система на основе матричной факторизации

Этапы решения

**1.** Инициализация import numpy as np import pandas as pd np.random.seed(42) K = 10 eta = 0.005 lmbda = 0.1 epochs = 20 ratings = pd.read_csv('ratings.csv', header=None, names=['user', 'item', 'rating']) test_pairs = pd.read_csv('test_pairs.csv', header=None, names=['user', 'i tem'])

U = ratings['user'].max() + 1 I = ratings['item'].max() + 1

P = np.random.normal(0, 0.1, (U, K))

Q = np.random.normal(0, 0.1, (I, K)) Пояснение:

- - Фиксация seed 42 гарантирует воспроизводимость инициализации весов.

- - Число пользователей U и объектов I вычисляется как максимальный

индекс + 1 (индексация с 0).

- - Матрицы факторов инициализируются из нормального распределения

𝒩(0,0.12).

- - Параметры обучения фиксированы: 𝜂 = 0.005, 𝜆 = 0.1, 20 эпох.

**2.** Обучение train_data = ratings[['user', 'item', 'rating']].values for epoch in range(epochs): np.random.shuffle(train_data) for u, i, r in train_data: pred = np.dot(P[u], Q[i]) error = r - pred p_u = P[u].copy() q_i = Q[i].copy() # Обновление по формулам SGD с L2-регуляризацией

P[u] = p_u + eta * (error * q_i - lmbda * p_u)

Q[i] = q_i + eta * (error * p_u - lmbda * q_i) if epoch == 4: np.save('checkpoint_epoch_5.npy', P.copy()) if epoch == 9: np.save('checkpoint_epoch_10.npy', P.copy())

Пояснение:

- - В начале каждой эпохи обучающие данные перемешиваются

np.random.shuffle с использованием того же генератора (seed фиксирован ранее).

- - Для каждой тройки (user, item, rating) вычисляется предсказание

𝑟̂𝑢𝑖 = 𝐩𝑢 ⋅ 𝐪𝑖𝑇 и ошибка 𝑒𝑢𝑖 = 𝑟 − 𝑟̂𝑢𝑖.

- - При обновлении векторов важно сохранить копии 𝐩𝑢old и 𝐪𝑖old, чтобы

использовать исходные значения при вычислении градиентов для обоих векторов (согласно формуле из условия).

- - Чекпоинты сохраняются после окончания 5-й (epoch == 4) и 10-й (epoch

== 9) эпох. Сохраняется матрица пользовательских факторов P в формате .npy.

**3.** Предсказание для тестовых пар predictions = [] for u, i in test_pairs.values: pred = np.dot(P[u], Q[i]) pred_rounded = int(round(pred)) pred_clipped = max(1, min(5, pred_rounded)) predictions.append(pred_clipped) with open('predictions.txt', 'w') as f: for p in predictions: f.write(f"{p}\n")

Пояснение:

- - Для каждой пары вычисляется точечное произведение факторов

пользователя и объекта.

- - Результат округляется до ближайшего целого (стандартное round).

- - Значение ограничивается диапазоном [1,5] , даже если округлённое

предсказание выходит за эти пределы.

- - Все предсказания записываются в текстовый файл построчно (без

заголовка, без лишних пробелов).

**4.** Сохранение архива с результатами import zipfile with zipfile.ZipFile('task2.zip', 'w') as z: z.write('predictions.txt', arcname='predictions.txt') z.write('checkpoint_epoch_5.npy', arcname='checkpoint_epoch_5.npy') z.write('checkpoint_epoch_10.npy', arcname='checkpoint_epoch_10.npy')

Пояснение:

- - Создаётся архив task2.zip, в который помещаются три файла без

вложенных папок (аргумент arcname задаёт имя файла внутри архива).

- - Порядок файлов в архиве не регламентирован, но имена должны строго

соответствовать условию.

Разбор задачи №3: Классификация текстов (определение тональности отзывов)

Этапы решения

**1.** Предобработка текста import re from sklearn.feature_extraction.text import CountVectorizer from sklearn.naive_bayes import MultinomialNB def predict(train_texts, train_labels, test_texts): def preprocess(text): # приведение к нижнему регистру text = text.lower() # удаление всех символов, кроме букв, цифр и пробелов text = re.sub(r'[^a-zA-Z0-9\s]', '', text) return text train_clean = [preprocess(t) for t in train_texts] test_clean = [preprocess(t) for t in test_texts]

Пояснение:

- - Функция preprocess последовательно:

- - приводит весь текст к нижнему регистру (lower());

- - удаляет все символы, не входящие в множество латинских букв (a–z, A–

Z), цифр (0–9) и пробелов, с помощью регулярного выражения [^a-zA-Z0-9\s].

- - Предобработка применяется и к обучающим, и к тестовым текстам

одинаково, без исключений.

**2.** Векторизация (мешок слов) vectorizer = CountVectorizer(stop_words='english') X_train = vectorizer.fit_transform(train_clean) X_test = vectorizer.transform(test_clean)

Пояснение:

- - Используется CountVectorizer из sklearn.feature_extraction.text с

параметром stop_words='english', что удаляет стандартный список английских стоп-слов (частых, не несущих смысла слов).

- - Векторизатор обучается только на предобработанных обучающих

текстах (fit_transform), после чего применяется к тестовым текстам через transform (без повторного обучения).

- - В результате получаются разреженные матрицы частот слов.

**3.** Обучение классификатора model = MultinomialNB() model.fit(X_train, train_labels)

Пояснение:

- - Используется наивный байесовский классификатор для текстов

(MultinomialNB) из sklearn.naive_bayes с параметрами по умолчанию.

- - Модель обучается на векторизованных обучающих данных (X_train) и

соответствующих метках классов (train_labels).

- - Никакой дополнительной настройки гиперпараметров не требуется.

**4.** Предсказание и возврат результата predictions = model.predict(X_test) return predictions.tolist()

Пояснение:

- - Для тестовых текстов вычисляются предсказанные метки с помощью

метода predict обученной модели.

- - Результат преобразуется в список целых чисел Python (tolist()), так как

по условию функция должна возвращать List[int], а не массив numpy.

- - Порядок предсказаний строго соответствует порядку тестовых текстов,

переданных в функцию.

Разбор задачи №4: Сегментация изображений методом пороговой обработки

Этапы решения

**1.** Загрузка изображений из архива и подготовка import os import zipfile import numpy as np from PIL import Image from skimage import filters, morphology input_zip = 'task4_data.zip' extract_dir = 'input_images' with zipfile.ZipFile(input_zip, 'r') as z: z.extractall(extract_dir) image_files = sorted([ f for f in os.listdir(extract_dir) if f.lower().endswith('.png')

])

Пояснение:

- - Архив распаковывается во временную директорию.

- - Отбираются все файлы с расширением .png (регистронезависимо),

список сортируется для детерминированного порядка обработки.

**2.** Загрузка изображения и приведение к float64 for img_file in image_files: img_path = os.path.join(extract_dir, img_file) img = Image.open(img_path) img_array = np.array(img, dtype=np.float64)

Пояснение:

- - Изображение открывается через Pillow и преобразуется в массив NumPy.

- - Тип данных явно задаётся как float64, что требуется для последующих

вычислений градиента с сохранением точности.

**3.** Вычисление магнитуды градиента фильтром Собеля gradient = filters.sobel(img_array, mode='reflect')

Пояснение:

- - Используется функция sobel из модуля skimage.filters.

- - Она автоматически вычисляет обе компоненты градиента (𝐺𝑥 и 𝐺𝑦) и

возвращает магнитуду 𝐺 = √𝐺𝑥2 + 𝐺𝑦2.

- - Параметр mode='reflect' задаёт обработку границ изображения

зеркальным отражением, как того требует условие.

**4.** Бинаризация методом Оцу по магнитуде градиента thresh = filters.threshold_otsu(gradient) binary = gradient > thresh

Пояснение:

- - Метод threshold_otsu вычисляет порог для изображения градиента,

максимизируя межклассовую дисперсию.

- - Создаётся булева маска: пиксели с магнитудой выше порога считаются

объектом (True), остальные — фоном (False).

**5.** Морфологическое закрытие с квадратным ядром 3×3 closed = morphology.closing(binary, morphology.square(3))

Пояснение:

- - Применяется морфологическая операция закрытия (closing) с помощью

функции morphology.closing.

- - Ядро задаётся через morphology.square(3) — это массив 3×3 из единиц,

определяющий окрестность для дилатации и последующей эрозии.

- - Операция заполняет небольшие отверстия внутри объектов и соединяет

близкие фрагменты, улучшая бинарную маску.

**6.** Сохранение маски и упаковка результата mask = (closed * 255).astype(np.uint8) mask_img = Image.fromarray(mask, mode='L') base_name = os.path.splitext(img_file)[0] mask_filename = f"{base_name}_mask.png" mask_img.save(mask_filename) output_masks.append(mask_filename)

Пояснение:

- - Булева маска умножается на 255 и приводится к uint8, давая значения 0

(фон) и 255 (объект).

- - Изображение создаётся в режиме 'L' (полутоновое) и сохраняется в

формате PNG.

- - Имя выходного файла получается из исходного имени заменой

расширения на _mask.png. with zipfile.ZipFile('task4.zip', 'w') as z: for mask_file in output_masks: z.write(mask_file)

Пояснение:

- - Все созданные файлы масок помещаются в архив task4.zip без

вложенных папок.

Разбор задачи №5: Интерпретируемость модели дерева решений

Этапы решения

**1.** Загрузка модели import pickle import pandas as pd import numpy as np from sklearn.tree import DecisionTreeClassifier # обязательно до pickle. load with open('tree.pkl', 'rb') as f: model = pickle.load(f)

Пояснение:

- - Импорт класса DecisionTreeClassifier из sklearn.tree до вызова

pickle.load обязателен, чтобы десериализатор знал, экземпляр какого класса восстанавливать.

- - Модель загружается из файла tree.pkl.

**2.** Извлечение важности признаков и ранжирование train_df = pd.read_csv('train.csv') feature_names = train_df.columns[:-1].tolist() # все столбцы, кроме chur n importances = model.feature_importances_ ranking_df = pd.DataFrame({

'feature': feature_names, 'importance': importances

}) ranking_df = ranking_df.sort_values('importance', ascending=False) ranking_df.to_csv('feature_ranking.csv', index=False, float_format='%.6f', encoding='utf-8')

Пояснение:

- - Из обучающей выборки извлекаются имена признаков — все колонки,

кроме последней (churn).

- - Атрибут обученной модели feature_importances_ содержит значения

важности каждого признака, сумма которых равна 1.

- - Создаётся DataFrame с двумя колонками: feature и importance.

- - Признаки сортируются по убыванию важности.

- - Файл feature_ranking.csv сохраняется с заголовком feature,importance,

без индекса, с значениями важности, записанными с 6 знаками после запятой.

**3.** Загрузка данных клиента и предсказание client_df = pd.read_csv('sample_client.csv') X_client = client_df.values.reshape(1, -1) # обязательно двумерный масси в predicted_class = model.predict(X_client)[0]

Пояснение:

- - Данные клиента загружаются из CSV (одна строка с теми же признаками,

что в обучении, без целевого столбца).

- - Массив признаков преобразуется в двумерный размер (1, n_features),

так как методы predict и decision_path ожидают на вход 2D-массив.

- - Предсказанный класс извлекается как скаляр из возвращённого списка.

**4.** Извлечение пути дерева (decision path) path = model.decision_path(X_client) node_indices = path.indices[path.indptr[0]:path.indptr[1]] num_nodes = len(node_indices) nodes_str = ','.join(map(str, node_indices))

Пояснение:

- - Метод decision_path возвращает разрежённую матрицу в формате CSR

(Compressed Sparse Row).

- - Для извлечения индексов узлов, пройденных клиентом, используются

атрибуты:

- - .indices — массив индексов всех задействованных узлов;

- - .indptr — указатели начала строк (для одной строки indptr[0] и

indptr[1] задают диапазон в .indices).

- - Индексы узлов перечисляются в порядке от корня к листу.

- - Количество узлов в пути включает и корень, и лист.

**5.** Формирование и сохранение файла-объяснения explanation = f"Predicted class: {predicted_class}\n" explanation += f"Number of nodes in path: {num_nodes}\n" explanation += f"Nodes indices: {nodes_str}\n" with open('explanation.txt', 'w', encoding='utf-8') as f: f.write(explanation)

Пояснение:

- - Файл состоит ровно из трёх строк:

- - Predicted class: {0 или 1} - Number of nodes in path: {целое число}

- - Nodes indices: {список индексов через запятую без пробелов}

- - В конце файла допускается перевод строки (последний \n), но лишних

пустых строк быть не должно.

**6.** Сохранение архива с результатами import zipfile with zipfile.ZipFile('task5.zip', 'w') as z: z.write('feature_ranking.csv', arcname='feature_ranking.csv') z.write('explanation.txt', arcname='explanation.txt')

Пояснение:

- - Создаётся архив task5.zip, в который помещаются оба файла без

вложенных папок.

Разбор задачи №6: Сжатие изображений с помощью метода главных компонент (PCA)

Этапы решения

**1.** Загрузка данных и приведение тестового изображения к нужной форме import numpy as np from sklearn.decomposition import PCA faces = np.load('faces.npy') # (200, 1024) test_face = np.load('test_face.npy') # (1024,) или (1, 1024) if test_face.ndim == 1: test_face = test_face.reshape(1, -1)

Пояснение:

- - faces.npy — обучающая выборка из 200 векторных представлений

изображений лиц (размерность каждого — 1024).

- - test_face.npy может быть одномерным массивом (1024,) или уже

двумерным (1, 1024); для единообразия преобразуем в форму (1, 1024), необходимую для методов transform и inverse_transform.

**2.** Обучение PCA с 25 компонентами pca_25 = PCA(n_components=25, svd_solver='full') pca_25.fit(faces)

Пояснение:

- - Создаётся объект PCA с фиксированным числом компонент 25 и

обязательно с параметром svd_solver='full', что обеспечивает детерминированные вычисления. - Модель обучается на всем массиве faces; центрирование данных (вычитание среднего) выполняется автоматически.

**3.** Преобразование и восстановление тестового изображения test_proj = pca_25.transform(test_face) # (1, 25) test_reconstructed = pca_25.inverse_transform(test_proj) # (1, 1024)

Пояснение:

- - Тестовое изображение проецируется на 25 главных компонент с

помощью transform — получается сжатое представление.

- - Обратное преобразование inverse_transform восстанавливает

изображение в исходном 1024-мерном пространстве.

- - Оба массива имеют форму (1, ...), что соответствует размерности,

ожидаемой моделью.

**4.** Вычисление среднеквадратичной ошибки (MSE) mse = np.mean((test_face - test_reconstructed) ** 2)

Пояснение:

- - MSE вычисляется по формуле 𝑑1 ∑𝑑𝑖=1(𝑥𝑖 − 𝑥̂𝑖)2.

- - Так как тестовое изображение имеет 1024 признака, np.mean выполняет

усреднение по всем элементам, деля на общее число пикселей (1024). - Значение сохраняется в переменную для последующей записи в файл.

**5.** Определение минимального числа компонент для сохранения ≥95% дисперсии pca_full = PCA() # без ограничения числа компонент pca_full.fit(faces) cumsum = np.cumsum(pca_full.explained_variance_ratio_) k = np.argmax(cumsum >= 0.95) + 1 # минимальное k, при котором сумма ≥ 0.

Пояснение:

- - Создаётся второй экземпляр PCA без указания n_components (или с

n_components=None), чтобы сохранились все главные компоненты.

- - Массив explained_variance_ratio_ содержит долю объяснённой

дисперсии для каждой компоненты.

- - Функция np.cumsum вычисляет накопленную сумму долей.

- - np.argmax(cumsum >= 0.95) возвращает индекс первого элемента, для

которого сумма достигает или превышает 0.95. Прибавление единицы даёт искомое число компонент k (так как нумерация индексов начинается с 0).

**6.** Сохранение результатов в файлы и упаковка в архив with open('mse.txt', 'w', encoding='utf-8') as f: f.write(f"{mse:.6f}\n") with open('n_components.txt', 'w', encoding='utf-8') as f: f.write(f"{k}\n")

Пояснение:

- - MSE записывается с строго 6 знаками после запятой (формат :.6f), без

лишних пробелов и заголовков.

- - Количество компонент k — целое число, сохраняется как есть, тоже без

лишних символов. import zipfile with zipfile.ZipFile('task6.zip', 'w') as z: z.write('mse.txt', arcname='mse.txt') z.write('n_components.txt', arcname='n_components.txt')

Пояснение:

- - Создаётся архив task6.zip, в который помещаются оба текстовых файла

без вложенных папок (имена внутри архива задаются через arcname).

Разбор задачи №7: Многоагентное обучение с подкреплением (Тактический бой)

Этапы решения

**1.** Архитектура нейронной сети

Используется дуэльная глубокая Q-сеть (Dueling DQN) с разделением на ценность состояния и преимущества действий. Сеть принимает два входа:

- - Карта наблюдения — тензор [batch, 7, 12, 12], полученный one-hot

кодированием исходной сетки team_obs (коды 0–6). Каждый из 7 каналов отвечает за один тип объекта.

- - Скалярные признаки — вектор из 5 нормализованных значений:

agent_id, hp, step, alive_teammates, alive_enemies.

Свёрточная часть состоит из трёх слоёв Conv2d с BatchNorm и MaxPool. Для учёта важных пространственных зон добавлен механизм пространственного внимания (слой attention_conv → softmax, взвешивание карт признаков). Вектор скалярных признаков пропускается через небольшую полносвязную сеть. Результаты свёрточной и скалярной ветвей конкатенируются и подаются в два параллельных потока: value (ценность состояния) и advantage (преимущества действий). Выходной Q-вектор вычисляется как value + advantage - mean(advantage). class ImprovedDQN(nn.Module): def __init__(self, input_channels=7, extra_dim=5, n_actions=5): # conv1..conv3, bn, pool, attention_conv # extra_fc # value_fc, advantage_fc def forward(self, map_obs, extra): # свёртки, внимание, flatten # объединение с extra # вычисление value и advantage, комбинирование return q_values

Такая архитектура позволяет сети сосредоточиться на важных частях карты и одновременно учитывать глобальные показатели каждого агента.

**2.** Предобработка наблюдения перед подачей в сеть

Метод preprocess_state преобразует словарь состояния в тензоры:

- - team_obs (матрица 12×12 с кодами объектов) преобразуется в one-hot

тензор (1, 7, 12, 12) путём создания бинарных масок для каждого кода 0..6.

- - Скалярные признаки нормализуются делением на соответствующие

максимальные значения (agent_id/2, hp/3, step/200, alive_teammates/3, alive_enemies/3) и собираются в вектор (1, 5). def preprocess_state(self, state): one_hot = torch.zeros(7, 12, 12) for code in range(7): one_hot[code] = torch.tensor(obs == code, dtype=torch.float32) extra = torch.tensor([agent_id/2., hp/3., step/200., ...]) return one_hot.unsqueeze(0), extra.unsqueeze(0)

**3.** Обучение агента (DQN с буфером воспроизведения)

Обучение происходит в отдельном скрипте train.py, который взаимодействует со средой. Ключевые компоненты:

- • Алгоритм: Deep Q-Network (DQN) с использованием target-сети и буфера

воспроизведения фиксированного размера (например, 100 000 переходов).

- • Функция потерь: среднеквадратичная ошибка между текущим

предсказанием Q(s,a) и целью r + γ * max_a' Q_target(s', a') (для терминальных состояний цель равна r).

- • ε-жадная стратегия: начальное ε = 1.0, линейно или экспоненциально

уменьшается до 0.05 в процессе обучения.

- • Parameter Sharing: все три агента используют одну и ту же сеть; опыт

всех агентов накапливается в общем буфере.

- • Внутренняя мотивация: к награде среды добавляются дополнительные

бонусы, например:

- – за посещение ранее неисследованных клеток (поощрение разведки);

- – за сближение с врагом (ускорение встречи);

- – штраф за бездействие или застревание в цикле. Внутренние награды

суммируются с внешними и помогают направить обучение к критериям турнира (победы, эффективность боя, координация).

**4.** Эвристическая коррекция действий (гибридный подход)

На этапе инференса решение нейросети может быть дополнено детерминированными правилами для повышения надёжности и безопасности.

Типовые эвристики:

- - Фильтр недопустимых действий: если выбранное сетью движение

ведёт в стену или ловушку (когда эта клетка видна в team_obs), действие заменяется на безопасную альтернативу (например, атаку, если рядом враг, или случайное из допустимых направлений).

- - Принудительная атака: если в соседней клетке есть враг с 1 HP, всегда

выбирается действие «атака» (код 4) для гарантированного добивания.

- - Адаптация к ловушкам: при видимой ловушке временно маскируются

действия, ведущие в неё.

Эвристики реализуются в методе choose_action перед или после вызова сети, не нарушая ограничения по времени (≤0.1 с на вызов).

**5.** Инференс и финальная сборка решения

Файл solution.py содержит только класс Agent с двумя методами:

- - __init__ — инициализация сети и загрузка весов из weights.pt с

помощью torch.load(..., map_location='cpu').

- - choose_action(state) — предобработка, прямой проход сети в режиме

eval() (без градиентов), опциональная эвристическая коррекция, возврат действия (целое число 0–4).

Веса модели сохраняются в train.py через torch.save(model.state_dict(), 'weights.pt'). Размер файла не должен превышать 15 МБ.

Оба файла (solution.py и weights.pt) упаковываются в task7.zip без вложенных папок.

**6.** Тестирование и анализ критериев

Локальная оценка производится скриптом local_tester.py, который проводит серию матчей против встроенного противника. Анализируются четыре метрики:

- - Победы: доля выигранных матчей (с учётом ничьих).

- - Эффективность боя (kill_diff): разница убитых синими и жёлтыми

агентов за матч.

- - Координация: доля шагов, на которых ≥2 синих агентов одновременно

выполнили атаку.

- - Стабильность: дисперсия итоговой командной награды по всем

эпизодам.

По результатам тестов можно корректировать внутренние награды, гиперпараметры обучения или эвристики, добиваясь улучшения по наиболее весомым критериям (победы и эффективность боя). Итоговая оценка на сервере формируется через турнир между решениями всех участников.

# Citations

1. [Заключительный этап — reshenie final ai](https://lk-dovuz.innopolis.university/public/files/reshenie_final_ai.pdf), file 263931eac811

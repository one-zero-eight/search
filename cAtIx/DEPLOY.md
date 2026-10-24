# Деплой cAtIx для бета-теста

Один сервер (VPS/VM) с Docker. Модели (llama.cpp) остаются на GPU-сервере: приложение ходит к ним по сети или через SSH-туннель.

## 1. Что нужно
- Linux-сервер с Docker и Docker Compose v2, 2 ГБ ОЗУ и 10 ГБ диска хватит на бету.
- Доступ с сервера к llama.cpp серверам: чат `:8080`, эмбеддинги `:8081`, реранкер `:8082` (напрямую или через профиль `tunnel`).
- Отдельный бот у @BotFather для беты (privacy mode выключен: `/setprivacy` → Disable), команды ставит сам бот.
- Отдельный Telegram-аккаунт для userbot (не личный): он читает чаты, куда вступил.

## 2. Первый запуск
```bash
git clone <репозиторий> && cd cAtIx
cp .env.example .env          # заполнить; пароли: openssl rand -base64 24
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```
Поднимутся `db`, `redis`, `migrate` (схема БД, повторяемо), `wiki` (вики в базу из checkout ветки `wiki`, см. 2a), `tgbot`, `maxbot`, `worker`. Логи: `docker compose -f docker-compose.prod.yml logs -f tgbot`.

Проверка: бот отвечает на `/start`, в логе `tgbot` строка `Running as @...`. Меню команд ставится при каждом старте.

Учебную группу пользователь назначает себе в боте командой `/mygroup`. Брать её из InNoHassle по Telegram id пока выключено (группы там пока неверные): включается `INNOHASSLE_GROUPS=true` вместе с `INNOHASSLE_SERVICE_TOKEN` — токеном со scope `users`, его выдаёт админ InNoHassle (`/accounts/v0/tokens/generate-service-token?sub=catix&scopes=users`), действует до 14 августа. Тогда `/mygroup` отвечает «Ваша группа определена по InNoHassle: …» и вручную её не поменять.

## 2a. Вики документов (поиск по положениям, правилам приёма, курсам)
Вики живёт не в коде, а в своей ветке `wiki` (orphan: только `wiki/` и `raw/`). В неё коммитит только сама вики (раздел 2b), и только то, что прошло проверки. На сервере рядом с кодом лежит checkout этой ветки, сервис `wiki` читает его и кладёт в базу только изменившиеся страницы:
```bash
git clone -b wiki --single-branch <репозиторий> ../catix-wiki      # один раз; другой путь — WIKI_DIR в .env
docker compose -f docker-compose.prod.yml run --rm wiki              # первый раз: ~20 с, 2155 файлов
```
Векторы не обязательно считать на сервере заново: индекс можно привезти с машины, где он уже посчитан. Это только вики-таблицы, сообщения чатов не затрагиваются; импорт занимает около 2 минут против ≈45 на подсчёт. Файл около 370 МБ, в git его не кладём:
```bash
uv run catix-wiki index export wiki-index.tar.gz                        # локально; в файле записан коммит ветки wiki
scp wiki-index.tar.gz server:/srv/cAtIx/
docker compose -f docker-compose.prod.yml run --rm -v ./wiki-index.tar.gz:/tmp/wiki-index.tar.gz:ro wiki catix-wiki index import /tmp/wiki-index.tar.gz
```
После импорта сервис `wiki` досчитывает только то, что изменилось после коммита из файла.

Новые коммиты вики привозит `scripts/wiki-pull.sh`: `git pull` ветки и, если что-то пришло, сервис `wiki`. Скрипт ставится в cron, например `*/15 * * * * /srv/cAtIx/scripts/wiki-pull.sh >> /var/log/catix-wiki-pull.log 2>&1`. Пересобирать образ для обновления вики не нужно.

Векторы кусков считает `worker` в фоне, когда нет новых сообщений из чатов. Пока векторов нет, куски находятся по словам. Первый раз это займёт около 45 минут (88 тыс. кусков), дальше — секунды на коммит. Очередь вики в алертах не участвует.

Проверка:
```bash
docker compose -f docker-compose.prod.yml exec worker catix-wiki index status   # страницы, куски, векторы, очередь
```
Для поиска нужен и реранкер (`RERANKER_ROUTE`): без него поиск работает, но заметно хуже (80% против 90% в первой пятёрке). Если сменить `EMBEDDINGS_MODEL`, все векторы вики пересчитаются сами.

## 2b. Вики обслуживает себя сама (машина с локальной LLM)
`catix-wiki autopilot --loop` работает там, где есть LLM (llama.cpp), и пишет в checkout ветки `wiki` (`WIKI_ROOT` в `.env`):
```bash
git worktree add ../catix-wiki wiki          # или git clone -b wiki; затем WIKI_ROOT=<путь> в .env
uv run catix-wiki autopilot --loop           # лучше как systemd-сервис пользователя
```
- **Источники** (`src/catix/wiki/sources/`, расписание в `__init__.py`) опрашиваются по своему расписанию:
  - `eduwiki` — каждые 6 часов, по номерам ревизий;
  - `sveden` — раз в день: новые документы и архивы РПД на сайте, решение модели о новых;
  - `files` — раз в неделю: HEAD каждого прочитанного документа (ETag, дата, размер), изменившиеся скачиваются заново.

  `catix-wiki autopilot --source sveden` спрашивает источник сразу.
- **Пересборка.** Если что-то пришло: страницы, связи, темы и гайды (модель), проверки, индекс.
- **Проверки:**
  - lint без ошибок;
  - нет гайдов на изменившихся доказательствах;
  - поиск находит ответы `src/catix/wiki/quality.py` (hit@5 ≥ `WIKI_MIN_HIT5`, по умолчанию 85%);
  - агент проходит `tests/test_docs_answers.py`.
- **Коммит.** Все проверки прошли — коммит от «cAtIx wiki» в `wiki` и push. Что-то не прошло — те же изменения уходят в ветку `wiki-review/<время>`, а `wiki` не меняется. Человек смотрит и решает: `catix-wiki autopilot accept` (в `wiki` и push) или `catix-wiki autopilot discard`.
- **Агент вики** (`src/catix/wiki/agent.py`, LangChain deepagents): после пересборки читает изменившиеся страницы-источники и ведёт карточки знаний `wiki/knowledge/` — одна тема на карточку, собранная из всех страниц, где о ней говорится. Страницы-источники он не меняет. Карточку пишет только через проверку кодом: у каждого предложения ссылка на страницу и пункт, страница и пункт существуют, числа есть в цитируемом тексте; не прошла — карточка не записывается, агент исправляет. За прогон не больше `WIKI_AGENT_MAX_PAGES` страниц (30), остальные ждут в `raw/knowledge-queue.json`. Страницы идут задачами по 3, `WIKI_AGENT_PARALLEL` задач сразу (по умолчанию 4 с `WIKI_LLM_ROUTE`, 1 на локальной модели: её слоты нужны боту); в каждой задаче агент видит список уже готовых карточек и дополняет их, а не заводит двойники; за прогон он печатает потраченные токены. Карточки, переставшие сходиться со страницами, — проверка «cards» перед коммитом. Вручную: `catix-wiki agent /regulations/x.md`, `catix-wiki agent all regulations` (поставить в очередь), `catix-wiki agent check`. Выключить: `WIKI_AGENT=false`. Модель вики можно взять отдельно: `WIKI_LLM_ROUTE`, `WIKI_LLM_MODEL`, `WIKI_LLM_API_KEY` (туда уходят только публичные документы университета).
- **Защита путей.** Коммит, затронувший что-то кроме `wiki/` и `raw/`, не делается вовсе. На GitHub стоит включить защиту ветки `main`, а токену машины с вики дать права только на `wiki` и `wiki-review/*`.

## 2c. Модели на той же машине
Если llama-серверы запущены на той же машине, что и Docker, контейнеры не могут ходить на `localhost`: это сам контейнер.
- **Обычный Docker:** `LLM_ROUTE=http://host.docker.internal:8080/v1` (и так же 8081, 8082). Имя уже прописано в `docker-compose.prod.yml` (`extra_hosts`). llama-серверы должны слушать не только 127.0.0.1 (`--host 0.0.0.0` или адрес `docker0`).
- **Rootless Docker** (`docker info` показывает `rootless`): `host.docker.internal` (172.17.0.1) ведёт в сеть rootlesskit, а не на хост, и даёт `Connection refused`. Нужен IP машины в локальной сети (`ip -4 addr`, интерфейс вроде `eth0`), например `LLM_ROUTE=http://10.1.1.27:8080/v1`; llama-серверы с `--host 0.0.0.0`.

Проверка из контейнера (после правки `.env` — `docker compose -f docker-compose.prod.yml up -d --force-recreate tgbot worker`):
```bash
docker compose -f docker-compose.prod.yml exec worker python -c "import httpx; print([httpx.get(f'http://10.1.1.27:{p}/health').text for p in (8080, 8081, 8082)])"
```

## 3. Модели через SSH-туннель (если GPU-сервер напрямую недоступен)
Положить в `secrets/ssh/` ключ `id_ed25519` (chmod 600) и `known_hosts` GPU-сервера, в `.env`:
```
GPU_SSH=user@gpu-host
LLM_ROUTE=http://tunnel:8080/v1
EMBEDDINGS_ROUTE=http://tunnel:8081/v1
RERANKER_ROUTE=http://tunnel:8082/v1
```
```bash
docker compose -f docker-compose.prod.yml --profile tunnel up -d
```

## 4. Userbot (чтение чатов аккаунтом)
Вход интерактивный (код из Telegram), делается один раз, сессия хранится в томе `catix_data`:
```bash
docker compose -f docker-compose.prod.yml run --rm userbot catix-tguserbot login
docker compose -f docker-compose.prod.yml --profile userbot up -d
```
Дальше всё в боте: администратор пишет `/listen`, выбирает чаты и учебные группы; `/admin` добавляет других администраторов. Новый администратор должен один раз написать боту `/start`.

**Если userbot пишет `Attempt 1 at connecting failed: TimeoutError`**, сеть сервера не пускает к дата-центрам Telegram (MTProto). Бота это не касается: он ходит по HTTPS на `api.telegram.org`. Проверка с сервера:
```bash
timeout 5 bash -c "</dev/tcp/149.154.167.51/443" && echo ok || echo blocked
```
Тогда userbot ходит через прокси с машины, откуда Telegram открыт, `TG_PROXY` в `.env`:
```
TG_PROXY=http://user:password@host:3128          # HTTP-прокси (CONNECT); «HTTP/HTTPS-прокси» провайдеров — это он
TG_PROXY=socks5://user:password@host:1080        # или socks4://
TG_PROXY=mtproxy://SECRET@host:443               # MTProxy: hex-секрет, обычный или dd...; fake-TLS (ee...) Telethon не умеет
```
Прокси, к которому подключаются по TLS (`https://` в адресе самого прокси), Telethon не умеет: такой адрес бот отвергает при старте. Обычный HTTP-прокси с CONNECT подходит — трафик Telegram внутри него и так зашифрован. Прокси должен разрешать CONNECT на порт 443 (дата-центры Telegram слушают 443). Проверить прокси с сервера:
```bash
curl -sS -o /dev/null -w "%{http_code}\n" -x http://user:password@host:3128 https://api.telegram.org   # 302 или 200 — прокси работает
```
Прокси нужен и для `login`:
```bash
docker compose -f docker-compose.prod.yml --profile userbot run --rm userbot catix-tguserbot login
docker compose -f docker-compose.prod.yml --profile userbot up -d
```
Затем в `docker compose -f docker-compose.prod.yml logs userbot` не должно быть `Attempt 1 at connecting failed`.

## 5. Календарный фид
Воркер (FastAPI) отдаёт личный календарь пользователя `GET /users/me.ics` на порту `127.0.0.1:8090`. В запросе заголовок `Authorization: Bearer <токен InNoHassle пользователя>`: подпись проверяется по открытым ключам InNoHassle (`/accounts/v0/.well-known/jwks.json`), `telegram_id` из токена говорит, чей это календарь. В календаре события, которые пользователь добавил кнопкой «➕ В мой календарь» под ответами. Календарей групп нет. Перед портом нужен HTTPS (Caddy: `reverse_proxy 127.0.0.1:8090` для вашего домена).

Кнопки «➕ В мой календарь» и `/calendar` (ближайшие события и адрес календаря) появляются, когда в `.env` задан `FEED_PUBLIC_URL=https://<домен>` (тот же адрес, что перед портом 8090).

## 6. Эксплуатация
- Обновление: `git pull && docker compose -f docker-compose.prod.yml up -d --build` (схема применяется сама; вики обновляется отдельно, раздел 2a).
- Резервная копия БД: `scripts/backup.sh /srv/backups` (хранит 14 последних), поставить в cron на ночь. Восстановление: `gunzip -c файл.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U ctx -d ctx`.
- Состояние: `docker compose -f docker-compose.prod.yml exec worker catix-db status`.
- Алерты: воркер каждую минуту проверяет `/health` моделей, эмбеддингов и реранкера и длину очереди эмбеддингов; о проблеме (после двух неудачных проверок подряд), напоминании каждые 6 часов и восстановлении пишет всем администраторам бота в Telegram. Отключить: `ALERTS=false`.
- Трассировка запросов агента: Phoenix, раздел 6a.
- Все секреты только в `.env` на сервере (в git он не попадает). Перед бетой перевыпустить токены, которые использовались в разработке.

## 6a. Phoenix (трейсы агента)
Phoenix показывает каждый вопрос целиком: вызовы модели, помощников и инструментов, шаги поиска (`embed`, `hybrid` с `bm25` и `vector`, `rerank`) со временем, а также оценки 👍/👎 пользователей. Он необязателен: без него бот работает так же.

1. В `.env` на сервере:
   ```
   PHOENIX_ENDPOINT=http://phoenix:6006
   PHOENIX_PROJECT=catix
   ```
   Адрес `phoenix` — имя сервиса в docker-сети, `localhost` из контейнера не подойдёт.
2. Запустить Phoenix и перезапустить приложения, чтобы они подхватили адрес:
   ```bash
   docker compose -f docker-compose.prod.yml --profile phoenix up -d phoenix
   docker compose -f docker-compose.prod.yml up -d tgbot worker   # и maxbot / userbot, если запущены
   ```
   В логе `tgbot` при старте строка `phoenix tracing on (http://phoenix:6006/, project catix)`.
3. Интерфейс без входа по паролю, поэтому порт 6006 открыт только на localhost сервера. Открыть со своей машины через SSH-туннель:
   ```bash
   ssh -N -L 6006:localhost:6006 server
   ```
   и в браузере `http://localhost:6006`, проект `catix`.

Данные лежат в томе `phoenixdata` (SQLite). Трейсы старше 30 дней Phoenix удаляет сам; срок задаёт `PHOENIX_RETENTION_DAYS` в `.env`. Удалить все трейсы: `docker compose -f docker-compose.prod.yml --profile phoenix down` и `docker volume rm catix-prod_phoenixdata`. Выключить трейсы: убрать `PHOENIX_ENDPOINT` из `.env` и перезапустить приложения.

## 7. Перед приглашением тестеров
Сообщить им, что бот и userbot сохраняют сообщения чатов, куда добавлены (приветствия и мусор отбрасываются), и что бота можно убрать из чата.

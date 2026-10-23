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
- **Источники** (`src/catix/wiki/sources.py`) опрашиваются по своему расписанию:
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
- **Защита путей.** Коммит, затронувший что-то кроме `wiki/` и `raw/`, не делается вовсе. На GitHub стоит включить защиту ветки `main`, а токену машины с вики дать права только на `wiki` и `wiki-review/*`.

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

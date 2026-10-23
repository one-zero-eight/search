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
Поднимутся `db`, `redis`, `migrate` (схема БД, повторяемо), `wiki` (вики в базу, см. 2a), `tgbot`, `maxbot`, `worker`. Логи: `docker compose -f docker-compose.prod.yml logs -f tgbot`.

Проверка: бот отвечает на `/start`, в логе `tgbot` строка `Running as @...`. Меню команд ставится при каждом старте.

## 2a. Вики документов (поиск по положениям, правилам приёма, курсам)
Папка `wiki/` входит в образ. Сервис `wiki` при каждом `up` кладёт её в базу: только страницы, изменившиеся с прошлого образа. В первый раз на это уходит около 20 с (1435 страниц, 43 тыс. кусков), при повторном запуске без изменений — 0 с. После этого сервис завершается, и боты его не ждут.

Векторы кусков считает `worker` в фоне, когда нет новых сообщений из чатов: в первый раз около 20–25 минут, через эмбеддинги `EMBEDDINGS_ROUTE`. Пока векторов нет, куски уже находятся по словам. Очередь вики в алертах не участвует.

Проверка:
```bash
docker compose -f docker-compose.prod.yml logs wiki                      # «1435 pages new …» или «… pages unchanged»
docker compose -f docker-compose.prod.yml exec worker catix-wiki index status   # куски, векторы, очередь
```
Для поиска нужен и реранкер (`RERANKER_ROUTE`): без него поиск работает, но заметно хуже (по замеру — 80% против 90% в первой пятёрке). Если сменить `EMBEDDINGS_MODEL`, все векторы вики пересчитаются сами.

Вики обновляется на машине разработчика (`catix-wiki build`, нужна локальная LLM) и коммитится в git. На сервер её привозит обычное обновление (раздел 6).

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
Воркер отдаёт `/feed/<FEED_TOKEN>.ics` на порту `127.0.0.1:8090`. Перед ним нужен HTTPS (Caddy: `reverse_proxy 127.0.0.1:8090` для вашего домена), затем один раз привязать адрес:
`docker compose -f docker-compose.prod.yml exec worker catix-feed link https://<домен>`.

Чтобы пользователи получали ссылки через бота (`/calendar`), задайте в `.env` `FEED_PUBLIC_URL=https://<домен>` (тот же адрес, что перед портом 8090) и `FEED_TOKEN`. Бот выдаёт каждому подписанную ссылку на ленту его учебной группы (`/feed/g/<подпись>/<ГРУППА>.ics`, подпись считается из `FEED_TOKEN` отдельно для каждой группы) и личную ссылку на его события (`/feed/me/<токен>.ics`, токен у каждого свой и заменяется кнопкой «Новая личная ссылка»). Сам `FEED_TOKEN` пользователям не показывается.

## 6. Эксплуатация
- Обновление: `git pull && docker compose -f docker-compose.prod.yml up -d --build` (схема применяется сама, изменившиеся страницы вики попадают в базу).
- Резервная копия БД: `scripts/backup.sh /srv/backups` (хранит 14 последних), поставить в cron на ночь. Восстановление: `gunzip -c файл.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U ctx -d ctx`.
- Состояние: `docker compose -f docker-compose.prod.yml exec worker catix-db status`.
- Алерты: воркер каждую минуту проверяет `/health` моделей, эмбеддингов и реранкера и длину очереди эмбеддингов; о проблеме (после двух неудачных проверок подряд), напоминании каждые 6 часов и восстановлении пишет всем администраторам бота в Telegram. Отключить: `ALERTS=false`.
- Трассировка запросов агента: Langfuse (`LANGFUSE_*` в `.env`), ставится отдельно.
- Все секреты только в `.env` на сервере (в git он не попадает). Перед бетой перевыпустить токены, которые использовались в разработке.

## 7. Перед приглашением тестеров
Сообщить им, что бот и userbot сохраняют сообщения чатов, куда добавлены (приветствия и мусор отбрасываются), и что бота можно убрать из чата.

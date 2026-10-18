-- Chat messages for search. Postgres 17 with pg_search (BM25) and pgvector (docker-compose.yml).
-- Applied by `catix-db init`; safe to run again. __TZ__ is replaced by the TIMEZONE setting.
-- Vectors live in their own table: writing a vector later must not rewrite the message row,
-- because every row rewrite also rewrites its entry in the BM25 index.

CREATE TABLE IF NOT EXISTS chats (
    chat_id    bigint PRIMARY KEY,
    title      text NOT NULL,
    username   text,                              -- set for public chats/channels
    synced_at  timestamptz,
    bot_member boolean NOT NULL DEFAULT false,    -- the Bot API bot is in this chat (getChatMember works)
    link       text,                              -- link to the chat itself, for sources of messages that have no link
    group_code text NOT NULL DEFAULT 'all'        -- study group the chat belongs to (groups.py); 'all' = everybody
);
ALTER TABLE chats ADD COLUMN IF NOT EXISTS group_code text NOT NULL DEFAULT 'all';  -- tables created before this column existed

-- The study group a user searches in; no row = 'all'. user_key is 'tg:<id>' or 'max:<id>'.
CREATE TABLE IF NOT EXISTS user_groups (
    user_key   text PRIMARY KEY,
    group_code text NOT NULL
);
ALTER TABLE chats ADD COLUMN IF NOT EXISTS link text;  -- tables created before this column existed

-- What the userbot listens to, set by an admin in the bot (/listen, tgbot/listen.py) and read by the userbot
-- (tguserbot/userbot.py). The userbot publishes the chats and forum topics it can see; the admin picks from them.
CREATE TABLE IF NOT EXISTS userbot_dialogs (
    chat_id      bigint PRIMARY KEY,
    title        text NOT NULL,
    kind         text NOT NULL,                   -- 'group' or 'channel'
    username     text,
    forum        boolean NOT NULL DEFAULT false,
    refreshed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS userbot_topics (
    chat_id  bigint NOT NULL,
    topic_id bigint NOT NULL,
    title    text NOT NULL,
    closed   boolean NOT NULL DEFAULT false,
    PRIMARY KEY (chat_id, topic_id)
);
-- A row = the chat is listened to. topic_ids NULL = the whole chat, otherwise only these forum topics.
CREATE TABLE IF NOT EXISTS userbot_listen (
    chat_id   bigint PRIMARY KEY,
    topic_ids bigint[]
);
-- 'seeded' (TG_CHATS / TG_TOPICS from .env were copied once), 'refresh_requested' (unix time, set by the bot).
CREATE TABLE IF NOT EXISTS userbot_meta (
    key   text PRIMARY KEY,
    value text NOT NULL
);

-- Which chats an answer may use is decided by the asker's study group (groups.py), not by who is in a chat.
DROP TABLE IF EXISTS members;

-- Telegram ids of the bot's admins added in the bot itself (/admin); the ones in ADMIN_TELEGRAM_IDS (or the owner of
-- INNOHASSLE_TOKEN) come from settings and are not stored here.
CREATE TABLE IF NOT EXISTS bot_admins (
    telegram_id bigint PRIMARY KEY,
    added_by    bigint,
    added_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chat_id     bigint NOT NULL REFERENCES chats (chat_id),
    msg_id      bigint NOT NULL,
    topic_id    bigint,
    date        timestamptz NOT NULL,
    edit_date   timestamptz,
    sender_id   bigint,
    sender_name text,
    reply_to    bigint,
    text        text NOT NULL,
    link        text,
    sender_link text,                             -- profile link of the author (from the @username), if any
    UNIQUE (chat_id, msg_id)
);
ALTER TABLE messages ADD COLUMN IF NOT EXISTS sender_link text;  -- tables created before this column existed
CREATE INDEX IF NOT EXISTS messages_date_idx ON messages (date);

-- chat_id is copied here so that vector search can filter by the chats a user may see without a join.
CREATE TABLE IF NOT EXISTS message_embeddings (
    message_id bigint PRIMARY KEY REFERENCES messages (id) ON DELETE CASCADE,
    chat_id    bigint,
    embedding  vector(1024) NOT NULL
);
ALTER TABLE message_embeddings ADD COLUMN IF NOT EXISTS chat_id bigint;  -- tables created before this column existed
UPDATE message_embeddings e SET chat_id = m.chat_id FROM messages m WHERE m.id = e.message_id AND e.chat_id IS NULL;
ALTER TABLE message_embeddings ALTER COLUMN chat_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS message_embeddings_chat_idx ON message_embeddings (chat_id);

-- Messages waiting for a vector. A trigger fills it, workers take rows with FOR UPDATE SKIP LOCKED, so any
-- number of workers (and processes) can embed in parallel and a crash loses nothing.
CREATE TABLE IF NOT EXISTS embedding_queue (
    message_id bigint PRIMARY KEY REFERENCES messages (id) ON DELETE CASCADE,
    queued_at  timestamptz NOT NULL DEFAULT now()
);
CREATE OR REPLACE FUNCTION enqueue_embedding() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO embedding_queue (message_id) VALUES (NEW.id) ON CONFLICT DO NOTHING;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS messages_enqueue_insert ON messages;
CREATE TRIGGER messages_enqueue_insert AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION enqueue_embedding();
DROP TRIGGER IF EXISTS messages_enqueue_edit ON messages;
CREATE TRIGGER messages_enqueue_edit AFTER UPDATE OF text ON messages
    FOR EACH ROW WHEN (OLD.text IS DISTINCT FROM NEW.text) EXECUTE FUNCTION enqueue_embedding();
-- Messages that never got a vector (loaded before the trigger existed).
INSERT INTO embedding_queue (message_id)
    SELECT m.id FROM messages m WHERE NOT EXISTS (SELECT 1 FROM message_embeddings e WHERE e.message_id = m.id)
    ON CONFLICT DO NOTHING;

-- BM25. The text is indexed twice: with the Russian stemmer (default field) and the English one
-- (field text_en), since chats mix both languages. chat_id and date are in the index so that
-- access and date filters run inside the index scan.
CREATE INDEX IF NOT EXISTS messages_search ON messages USING paradedb (
    id,
    (text::pdb.simple('stemmer=russian')),
    (text::pdb.simple('stemmer=english', 'alias=text_en')),
    chat_id,
    date
) WITH (mutable_segment_rows = 100);
-- mutable_segment_rows: new rows are buffered in memory and that buffer is read on every query. The default 1000
-- made queries take 50-200 ms while it filled up; 100 keeps them at 10-40 ms at no cost in write speed (measured).

-- Dense search, cosine distance (bge-m3 vectors are normalised).
CREATE INDEX IF NOT EXISTS message_embeddings_hnsw ON message_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------------------------------------
-- SQL for the model. It connects as the role ctx_reader, which has no rights on the tables above, only SELECT
-- on the views in schema "visible". The views show the chats listed for that connection's backend pid in
-- query_context (written by the app before the query; the reader cannot read or change it), so the filter
-- cannot be switched off from inside a query the way a session setting could.
-- ---------------------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS query_context (
    backend_pid int PRIMARY KEY,
    chat_ids    bigint[],                        -- NULL = every chat (local CLI only)
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE SCHEMA IF NOT EXISTS visible;

CREATE OR REPLACE FUNCTION visible.allowed_chats() RETURNS bigint[]
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_catalog AS $$
    SELECT CASE WHEN q.backend_pid IS NULL THEN ARRAY[]::bigint[]          -- no context: nothing is visible
                WHEN q.chat_ids IS NULL THEN (SELECT coalesce(array_agg(chat_id), ARRAY[]::bigint[]) FROM chats)
                ELSE q.chat_ids END
    FROM (SELECT 1) AS one LEFT JOIN query_context q ON q.backend_pid = pg_backend_pid()
$$;
REVOKE ALL ON FUNCTION visible.allowed_chats() FROM PUBLIC;
-- A view's tables are checked as the view owner, but the functions it calls are checked as the caller.
-- The function only ever returns the list stored for the caller's own backend pid.
GRANT EXECUTE ON FUNCTION visible.allowed_chats() TO ctx_reader;

-- security_barrier: the chat filter runs before any condition the query adds, so a clever function in the
-- query's WHERE cannot see rows of other chats.
CREATE OR REPLACE VIEW visible.chats WITH (security_barrier = true) AS
    SELECT c.chat_id, c.title, c.username
    FROM public.chats c
    WHERE c.chat_id = ANY (visible.allowed_chats());

CREATE OR REPLACE VIEW visible.messages WITH (security_barrier = true) AS
    SELECT 'm' || m.id AS ref,
           m.chat_id,
           c.title AS chat,
           m.topic_id,
           (m.date AT TIME ZONE '__TZ__')::date AS day,
           m.date AS sent_at,
           m.sender_name,
           m.reply_to,
           m.text,
           m.link
    FROM public.messages m
    JOIN public.chats c ON c.chat_id = m.chat_id
    WHERE m.chat_id = ANY (visible.allowed_chats());

-- Personal calendar of a user (personal_calendar.py): events they added with "➕ В мой календарь" under an answer, served
-- as a private iCalendar feed at /feed/me/<token>.ics. user_key is 'tg:<id>'.
CREATE TABLE IF NOT EXISTS user_calendars (
    user_key   text PRIMARY KEY,
    token      text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS personal_events (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_key   text NOT NULL,
    title      text NOT NULL,
    starts_at  timestamptz NOT NULL,
    ends_at    timestamptz,
    all_day    boolean NOT NULL DEFAULT false,
    room       text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_key, title, starts_at)
);
ALTER TABLE personal_events ADD COLUMN IF NOT EXISTS source_url text;  -- the message the event comes from (X-WR-LINK)

-- Events the agent offered under an answer, waiting for a button press (short ids fit in callback data).
CREATE TABLE IF NOT EXISTS calendar_proposals (
    id         text PRIMARY KEY,
    event      jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Reschedules, room changes and cancellations found in chat messages (changes.py). Only approved ones reach the
-- calendar feed. The worker reads new messages from a Redis stream, so history is never scanned.
CREATE TABLE IF NOT EXISTS schedule_changes (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id  bigint NOT NULL UNIQUE REFERENCES messages (id) ON DELETE CASCADE,
    kind        text NOT NULL CHECK (kind IN ('reschedule', 'room_change', 'cancel', 'announcement')),
    subject     text,
    starts_at   timestamptz NOT NULL,
    ends_at     timestamptz,
    all_day     boolean NOT NULL DEFAULT false,   -- no time was stated: an all-day event
    room        text,
    summary     text NOT NULL,
    status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    notified_at timestamptz,
    decided_at  timestamptz
);

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM ctx_reader;
REVOKE ALL ON SCHEMA public FROM ctx_reader;
GRANT USAGE ON SCHEMA visible TO ctx_reader;
GRANT SELECT ON visible.chats, visible.messages TO ctx_reader;
ALTER TABLE schedule_changes ADD COLUMN IF NOT EXISTS all_day boolean NOT NULL DEFAULT false;  -- tables created before this column existed
-- 'announcement' was added after the table was first created.
ALTER TABLE schedule_changes DROP CONSTRAINT IF EXISTS schedule_changes_kind_check;
ALTER TABLE schedule_changes ADD CONSTRAINT schedule_changes_kind_check
    CHECK (kind IN ('reschedule', 'room_change', 'cancel', 'announcement'));

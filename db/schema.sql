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
ALTER TABLE chats ADD COLUMN IF NOT EXISTS requires_verified_group boolean NOT NULL DEFAULT false;
ALTER TABLE chats ADD COLUMN IF NOT EXISTS max_legacy_archived boolean NOT NULL DEFAULT false;
-- An admin marks a chat as official (catix/official.py): only its messages may be called official in an answer.
ALTER TABLE chats ADD COLUMN IF NOT EXISTS official boolean NOT NULL DEFAULT false;

-- The study group a user searches in; no row = 'all'. user_key is 'tg:<id>' or 'max:<id>'.
CREATE TABLE IF NOT EXISTS user_groups (
    user_key   text PRIMARY KEY,
    group_code text NOT NULL
);
ALTER TABLE chats ADD COLUMN IF NOT EXISTS link text;  -- tables created before this column existed

-- The never-deployed Bot API state may only be replaced when every MAX state table is empty.
-- A DO block is one transaction: any failed guard leaves all state and indexed history untouched.
DO $$
DECLARE
    table_name text;
    occupied boolean;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns c
               WHERE c.table_schema = 'public' AND c.table_name = 'max_sources' AND c.column_name = 'membership_event_ms')
       OR to_regclass('public.max_message_ids') IS NOT NULL THEN
        FOREACH table_name IN ARRAY ARRAY['max_sources', 'max_inbox', 'max_message_ids',
                                          'max_message_state', 'max_publish_queue', 'max_account'] LOOP
            IF to_regclass('public.' || table_name) IS NOT NULL THEN
                EXECUTE format('LOCK TABLE public.%I IN ACCESS EXCLUSIVE MODE', table_name);
                EXECUTE format('SELECT EXISTS (SELECT 1 FROM public.%I)', table_name) INTO occupied;
                IF occupied THEN
                    RAISE EXCEPTION 'MAX userbot schema requires empty old MAX state tables; public.% contains data', table_name;
                END IF;
            END IF;
        END LOOP;
        DROP TABLE IF EXISTS public.max_inbox;
        DROP TABLE IF EXISTS public.max_message_ids;
        DROP TABLE IF EXISTS public.max_message_state;
        DROP TABLE IF EXISTS public.max_publish_queue;
        DROP TABLE IF EXISTS public.max_sources;
        DROP TABLE IF EXISTS public.max_account;
    END IF;
END
$$;

-- MAX is an explicitly enabled source, independent of Telegram reader selection.
CREATE TABLE IF NOT EXISTS max_sources (
    chat_id bigint PRIMARY KEY REFERENCES chats(chat_id) ON DELETE CASCADE,
    raw_chat_id bigint UNIQUE NOT NULL,
    kind text NOT NULL CHECK (kind IN ('chat', 'channel')),
    enabled boolean NOT NULL DEFAULT false,
    access text NOT NULL DEFAULT 'unknown' CHECK (access IN ('unknown', 'ready', 'removed', 'no_permission')),
    generation bigint NOT NULL DEFAULT 0,
    config_version bigint NOT NULL DEFAULT 0,
    legacy_chat_id bigint UNIQUE REFERENCES chats(chat_id),
    metadata_pending boolean NOT NULL DEFAULT true,
    checked_at timestamptz,
    last_error text,
    history_status text NOT NULL DEFAULT 'idle'
        CHECK (history_status IN ('idle', 'pending', 'running', 'complete', 'failed', 'partial', 'cancelled')),
    history_before_ms bigint,
    history_started_at timestamptz,
    history_last_id bigint,
    history_available_at timestamptz NOT NULL DEFAULT now(),
    metadata_available_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS catchup_before_ms bigint;
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS catchup_until_ms bigint;
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS catchup_after_ms bigint;
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS catchup_status text NOT NULL DEFAULT 'idle'
    CHECK (catchup_status IN ('idle','pending','running','complete','partial','failed','cancelled'));
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS catchup_available_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS sync_watermark_ms bigint;
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS deletion_scan_after_id bigint;
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS deletion_scan_until_id bigint;
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS deletion_scan_pending boolean NOT NULL DEFAULT false;
ALTER TABLE max_sources ADD COLUMN IF NOT EXISTS deletion_scan_available_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS max_inbox (
    id bigserial PRIMARY KEY,
    event_key text UNIQUE NOT NULL,
    chat_id bigint NOT NULL REFERENCES max_sources(chat_id) ON DELETE CASCADE,
    generation bigint NOT NULL,
    payload jsonb,
    received_at timestamptz NOT NULL DEFAULT now(),
    available_at timestamptz NOT NULL DEFAULT now(),
    attempts integer NOT NULL DEFAULT 0,
    processed_at timestamptz,
    error_code text
);
CREATE INDEX IF NOT EXISTS max_inbox_available ON max_inbox (available_at, id) WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS max_inbox_chat_pending ON max_inbox (chat_id, id) WHERE processed_at IS NULL;
CREATE TABLE IF NOT EXISTS max_message_state (
    chat_id bigint NOT NULL REFERENCES max_sources(chat_id) ON DELETE CASCADE,
    msg_id bigint NOT NULL,
    last_received_at timestamptz NOT NULL,
    last_live_id bigint,
    deleted boolean NOT NULL DEFAULT false,
    PRIMARY KEY (chat_id, msg_id)
);
CREATE TABLE IF NOT EXISTS max_publish_queue (
    id bigserial PRIMARY KEY,
    chat_id bigint NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    msg_id bigint NOT NULL,
    available_at timestamptz NOT NULL DEFAULT now(),
    attempts integer NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS max_publish_available ON max_publish_queue (available_at, id);

CREATE TABLE IF NOT EXISTS max_account (
    singleton boolean PRIMARY KEY CHECK (singleton),
    account_id bigint,
    connected_at timestamptz,
    heartbeat_at timestamptz,
    catalog_requested boolean NOT NULL DEFAULT true,
    catalog_status text NOT NULL DEFAULT 'idle'
        CHECK (catalog_status IN ('idle', 'running', 'complete', 'partial', 'failed')),
    catalog_error text,
    catalog_checked_at timestamptz
);

-- Telegram users the bot may write to first (bot_users.py): Telegram lets a bot message only a person who opened a
-- private chat with it (/start or any message there). Found schedule changes go to them. blocked_at: the user blocked
-- the bot; cleared when they start it again.
CREATE TABLE IF NOT EXISTS bot_users (
    telegram_id bigint PRIMARY KEY,
    started_at  timestamptz NOT NULL DEFAULT now(),
    blocked_at  timestamptz
);
-- The users who chose a group with /mygroup did it in a private chat with the bot. (A blocked one keeps blocked_at.)
INSERT INTO bot_users (telegram_id)
SELECT substr(user_key, 4)::bigint FROM user_groups WHERE user_key ~ '^tg:[0-9]+$'
ON CONFLICT (telegram_id) DO NOTHING;

-- What the userbot listens to, set by an admin in the bot (/listen, tgbot/listen.py) and read by the userbot
-- Private invitations remain outside chats until a moderator approves and Telegram confirms membership.
CREATE TABLE IF NOT EXISTS source_requests (
    id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{32}$'),
    owner text NOT NULL,
    email text NOT NULL,
    invite_link text NOT NULL,
    group_code text NOT NULL,
    comment text NOT NULL DEFAULT '',
    consented_at timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'joining', 'waiting_join', 'connected', 'failed', 'rejected')),
    message text,
    title text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (owner, invite_link)
);
-- Explicitly consented, moderated 'all' proposals are allowed; existing chat policies are unchanged.
ALTER TABLE source_requests DROP CONSTRAINT IF EXISTS source_requests_group_code_check;
ALTER TABLE source_requests ADD COLUMN IF NOT EXISTS decided_by bigint;
ALTER TABLE source_requests ADD COLUMN IF NOT EXISTS decided_at timestamptz;
ALTER TABLE source_requests ADD COLUMN IF NOT EXISTS available_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE source_requests ADD COLUMN IF NOT EXISTS token text;
ALTER TABLE source_requests ADD COLUMN IF NOT EXISTS lease_until timestamptz;
ALTER TABLE source_requests ADD COLUMN IF NOT EXISTS join_started_at timestamptz;
ALTER TABLE source_requests ADD COLUMN IF NOT EXISTS chat_id bigint;
ALTER TABLE source_requests ADD COLUMN IF NOT EXISTS backfill_pending boolean NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS source_requests_queue ON source_requests (available_at, created_at)
    WHERE status IN ('approved', 'joining', 'waiting_join');
-- Independent of request rows: deleting a claimed request cannot start overlapping Telegram writes.
CREATE TABLE IF NOT EXISTS source_request_lease (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    token text,
    lease_until timestamptz,
    available_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO source_request_lease (singleton) VALUES (true) ON CONFLICT DO NOTHING;

-- One Telegram account shares join intent across owners; request deletion must not erase it.
CREATE TABLE IF NOT EXISTS source_request_join_intents (
    invite_link text PRIMARY KEY,
    started_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO source_request_join_intents (invite_link, started_at)
SELECT invite_link, min(join_started_at) FROM source_requests
WHERE join_started_at IS NOT NULL GROUP BY invite_link
ON CONFLICT DO NOTHING;

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
-- Who stores a listened chat when both the userbot's account and the Bot API bot are in it ('auto' = the userbot, it has the
-- history; 'bot' / 'userbot' force one): both would store everything twice, a basic group even under different ids.
ALTER TABLE userbot_listen ADD COLUMN IF NOT EXISTS reader text NOT NULL DEFAULT 'auto';
-- NULL preserves legacy storage scope AND unrestricted live search. New confirmations explicitly
-- choose a default (including future topics) and per-topic store/search/off overrides.
-- topic_ids remains a coarse storage scope: NULL = all (check policy exclusions), [] = none.
ALTER TABLE userbot_listen ADD COLUMN IF NOT EXISTS topic_policy jsonb;
-- 'search': nobody stores the chat; the userbot searches it live with Telegram's own search when a question needs it
-- (a huge chat that is not worth indexing).
ALTER TABLE userbot_listen DROP CONSTRAINT IF EXISTS userbot_listen_reader_check;
ALTER TABLE userbot_listen ADD CONSTRAINT userbot_listen_reader_check CHECK (reader IN ('auto', 'userbot', 'bot', 'search'));
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

-- Durable exclusion/version fence, independent of chats/messages (an edit can arrive first).
-- Ordinary row deletion/maintenance must not erase this protection.
CREATE TABLE IF NOT EXISTS message_ingest_state (
    chat_id bigint NOT NULL,
    msg_id bigint NOT NULL,
    edit_date timestamptz,
    excluded boolean NOT NULL DEFAULT false,
    PRIMARY KEY (chat_id, msg_id)
);
ALTER TABLE message_ingest_state ADD COLUMN IF NOT EXISTS observed_at timestamptz;
-- Only attribution, never excluded caption/OCR/media. Used when a newer edit reenters.
ALTER TABLE message_ingest_state ADD COLUMN IF NOT EXISTS original_metadata jsonb;

-- Captions stay separate from derived OCR; messages.text is the searchable combination.
ALTER TABLE messages ADD COLUMN IF NOT EXISTS image_caption text; -- NULL only for legacy rows (fall back to text)
ALTER TABLE messages ADD COLUMN IF NOT EXISTS image_source text;
ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_image_source_check;
-- 'maxbot' remains only for untouched legacy archive rows; no runtime handles its OCR.
ALTER TABLE messages ADD CONSTRAINT messages_image_source_check
    CHECK (image_source IN ('tguserbot', 'tgbot', 'maxbot', 'maxuserbot'));
ALTER TABLE messages ADD COLUMN IF NOT EXISTS image_refs text[] NOT NULL DEFAULT '{}';
ALTER TABLE messages ADD COLUMN IF NOT EXISTS image_text text; -- NULL = not recognized, '' = recognized without text
CREATE TABLE IF NOT EXISTS image_queue (
    message_id bigint PRIMARY KEY REFERENCES messages (id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'claimed', 'failed')),
    attempts integer NOT NULL DEFAULT 0,
    available_at timestamptz NOT NULL DEFAULT now(),
    token text,
    lease_until timestamptz
);
-- Independent of messages: an edit/deletion must not release a still-running OCR request.
CREATE TABLE IF NOT EXISTS image_queue_lease (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    token text,
    lease_until timestamptz
);
INSERT INTO image_queue_lease (singleton) VALUES (true) ON CONFLICT DO NOTHING;
CREATE OR REPLACE FUNCTION enqueue_image() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF cardinality(NEW.image_refs) > 0 AND NEW.image_source IS NOT NULL THEN
        INSERT INTO image_queue (message_id) VALUES (NEW.id)
            ON CONFLICT (message_id) DO UPDATE SET status = 'pending', attempts = 0,
                available_at = now(), token = NULL, lease_until = NULL;
    ELSE
        DELETE FROM image_queue WHERE message_id = NEW.id;
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS messages_image_insert ON messages;
CREATE TRIGGER messages_image_insert AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION enqueue_image();
DROP TRIGGER IF EXISTS messages_image_edit ON messages;
CREATE TRIGGER messages_image_edit AFTER UPDATE OF image_caption, image_source, image_refs ON messages
    FOR EACH ROW WHEN (OLD.image_caption IS DISTINCT FROM NEW.image_caption
                      OR OLD.image_source IS DISTINCT FROM NEW.image_source
                      OR OLD.image_refs IS DISTINCT FROM NEW.image_refs)
    EXECUTE FUNCTION enqueue_image();

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

-- Retired experimental model profiles; the active vectors stay in message_embeddings.
DROP TABLE IF EXISTS public.message_model_embeddings;

-- Messages waiting for a vector. A trigger fills it, workers take rows with FOR UPDATE SKIP LOCKED, so any
-- number of workers (and processes) can embed in parallel and a crash loses nothing.
CREATE TABLE IF NOT EXISTS embedding_queue (
    message_id bigint PRIMARY KEY REFERENCES messages (id) ON DELETE CASCADE,
    queued_at  timestamptz NOT NULL DEFAULT now()
);
CREATE OR REPLACE FUNCTION enqueue_embedding() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO embedding_queue (message_id) VALUES (NEW.id)
        ON CONFLICT (message_id) DO UPDATE SET queued_at = excluded.queued_at;
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
    SELECT coalesce(array_agg(c.chat_id), ARRAY[]::bigint[])
    FROM query_context q JOIN chats c
      ON q.chat_ids IS NULL OR c.chat_id = ANY(q.chat_ids)
    WHERE q.backend_pid = pg_backend_pid() AND NOT c.max_legacy_archived
$$;
REVOKE ALL ON FUNCTION visible.allowed_chats() FROM PUBLIC;
-- A view's tables are checked as the view owner, but the functions it calls are checked as the caller.
-- The function only ever returns the list stored for the caller's own backend pid.
GRANT EXECUTE ON FUNCTION visible.allowed_chats() TO ctx_reader;

-- security_barrier: the chat filter runs before any condition the query adds, so a clever function in the
-- query's WHERE cannot see rows of other chats.
CREATE OR REPLACE VIEW visible.chats WITH (security_barrier = true) AS
    SELECT c.chat_id, c.title, c.username, c.group_code AS chat_group
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
           m.link,
           c.group_code AS chat_group
    FROM public.messages m
    JOIN public.chats c ON c.chat_id = m.chat_id
    WHERE m.chat_id = ANY (visible.allowed_chats());

-- Personal calendar of a user (personal_calendar.py): events they added with "➕ В мой календарь" under an answer, served
-- at /users/my-calendar.ics to the holder of the user's InNoHassle token. user_key is 'tg:<id>'.
DROP TABLE IF EXISTS user_calendars;  -- The calendars had a secret link each; now the InNoHassle token opens them.
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
ALTER TABLE personal_events ADD COLUMN IF NOT EXISTS source_note text;  -- the chat, time, author and text of it (DESCRIPTION)

-- Events the agent offered under an answer, waiting for a button press (short ids fit in callback data).
CREATE TABLE IF NOT EXISTS calendar_proposals (
    id         text PRIMARY KEY,
    event      jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- The conversations of the site's assistant (catix-api POST /ask/, api/chats.py): whose each one is, and its answers as the
-- client got them, to show again when the user comes back to it. What the agent itself remembers of a conversation is in
-- LangGraph's tables (checkpoints, checkpoint_blobs, checkpoint_writes, made by AsyncPostgresSaver.setup() when the API
-- starts), thread 'api:<chat_id>'.
CREATE TABLE IF NOT EXISTS api_chats (
    chat_id       text PRIMARY KEY,
    innohassle_id text NOT NULL,                     -- the owner
    title         text NOT NULL,                     -- the first question, then what the model or the user named it
    title_by      text NOT NULL DEFAULT 'question' CHECK (title_by IN ('question', 'model', 'user')),
    checkpoint    text,                              -- the agent's thread after the last answer: the next question goes on
                                                     -- from it, so one cancelled or failed halfway leaves nothing behind
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now() -- of the last answer
);
CREATE INDEX IF NOT EXISTS api_chats_owner_idx ON api_chats (innohassle_id, updated_at DESC);

-- Private chat attachments: never part of wiki/BM25/vector indexes or ctx_reader views.
-- Pending uploads expire after 24h (enforced on reads and cleaned under an owner advisory lock).
-- Binding fixes the chat for life; deleting a chat deletes its originals and extracted pages.
CREATE TABLE IF NOT EXISTS api_attachments (
    id         text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{32}$'),
    owner      text NOT NULL,
    chat_id    text REFERENCES api_chats (chat_id) ON DELETE CASCADE,
    filename   text NOT NULL CHECK (char_length(filename) BETWEEN 1 AND 200),
    media_type text NOT NULL CHECK (media_type IN ('text/plain', 'application/pdf', 'image/png', 'image/jpeg', 'image/webp')),
    size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 1 AND 10485760),
    pages      integer NOT NULL CHECK (pages BETWEEN 1 AND 20),
    data       bytea NOT NULL CHECK (octet_length(data) = size_bytes),
    page_text  jsonb NOT NULL CHECK (jsonb_typeof(page_text) = 'array' AND jsonb_array_length(page_text) = pages),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS api_attachments_owner_idx ON api_attachments (owner, created_at);
CREATE INDEX IF NOT EXISTS api_attachments_chat_idx ON api_attachments (chat_id) WHERE chat_id IS NOT NULL;
-- (tables created before this column existed; a name the user gave is never replaced by the model's)
ALTER TABLE api_chats ADD COLUMN IF NOT EXISTS title_by text NOT NULL DEFAULT 'question'
    CHECK (title_by IN ('question', 'model', 'user'));
CREATE TABLE IF NOT EXISTS api_answers (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chat_id      text NOT NULL REFERENCES api_chats (chat_id) ON DELETE CASCADE,
    ask_query_id text UNIQUE,                        -- what a 👍/👎 names; none when tracing is off
    span_id      text,                               -- the root span of the answer's trace in Phoenix: what the vote annotates
    response     jsonb NOT NULL,                     -- AskResponses without `messages` (the agent's own history)
    feedback     text,                               -- the user's last vote, 'like' or 'dislike'
    comment      text,                               -- and what they said of it
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS api_answers_chat_idx ON api_answers (chat_id, id);
-- A question whose answer waits for the user's decision on actions in InNoHassle (HumanInTheLoopMiddleware, api/ask.py): the
-- checkpoint the agent paused at, which the decision resumes, and what the client got (AskResponses with its `approval`,
-- and the interrupts with how many actions each). A new question drops it; an answer clears it.
ALTER TABLE api_chats ADD COLUMN IF NOT EXISTS waiting_checkpoint text;
ALTER TABLE api_chats ADD COLUMN IF NOT EXISTS waiting jsonb;

-- Reschedules, room changes and cancellations found in chat messages (changes.py). Each is sent to the users of the
-- chat's group, and a user who accepts it gets it in their personal calendar (personal_events); status and decided_at
-- are from when an admin decided for everybody and are no longer used. The worker reads new messages from a Redis
-- stream, so history is never scanned.
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

-- Raw opaque calendar subscription keys are intentionally retained only for link retrieval/revocation.
-- The application role needs access; ctx_reader must never read this table (revokes follow below).
CREATE TABLE IF NOT EXISTS calendar_export_keys (
    user_key   text PRIMARY KEY,
    access_key text NOT NULL UNIQUE,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
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

-- Messages the guardrail stopped as an attack or abuse, per user, and the pauses that repeated ones lead to (catix/abuse.py).
-- user_key is 'tg:<id>' or 'max:<id>'. Nobody is notified; the admins read /abuse.
CREATE TABLE IF NOT EXISTS abuse_log (
    id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_key text NOT NULL,
    category text NOT NULL,
    at       timestamptz NOT NULL DEFAULT now(),
    preview  text NOT NULL
);
CREATE INDEX IF NOT EXISTS abuse_log_user_idx ON abuse_log (user_key, at);
CREATE TABLE IF NOT EXISTS abuse_state (
    user_key      text PRIMARY KEY,
    pauses        int NOT NULL DEFAULT 0,
    last_pause_at timestamptz,
    paused_until  timestamptz
);
ALTER TABLE abuse_state DROP COLUMN IF EXISTS alert_pending;  -- admins used to be messaged; they are not any more

-- ---------------------------------------------------------------------------------------------------------
-- The wiki (catix-wiki index, src/catix/wiki/search_index.py): the pages of the OKF bundle in wiki/ and the pieces
-- the agent searches. A page is cut again only when its file (or the cutting scheme) changed; a piece whose text
-- stayed the same keeps its row and its vector, so an update of the wiki embeds only what is new.
-- ---------------------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wiki_pages (
    path           text PRIMARY KEY,                -- '/regulations/attestation-regulation.md'
    sha            text NOT NULL,                   -- of the file and the cutting scheme
    title          text NOT NULL,
    type           text NOT NULL,
    trust          text NOT NULL CHECK (trust IN ('official', 'guide', 'wiki')),  -- a document of the university, a guide written from evidence, eduwiki
    audience       text[] NOT NULL DEFAULT '{}',
    resource       text,                            -- the original: a PDF on the university's site or an eduwiki page
    status         text,
    review         text,                            -- what on the page nobody checked, if anything
    source_warning text,
    stale_after    date,
    issued         date,                            -- when the source was issued or last edited (newer documents replace older ones)
    indexed_at     timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE wiki_pages ADD COLUMN IF NOT EXISTS issued date;  -- tables created before this column existed
CREATE TABLE IF NOT EXISTS wiki_chunks (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path        text NOT NULL REFERENCES wiki_pages (path) ON DELETE CASCADE,
    trust       text NOT NULL,                      -- copied from the page: the search filters by it inside the index
    seq         int NOT NULL,                       -- order on the page
    heading     text NOT NULL,                      -- 'Chapter > Section'
    clause      text NOT NULL,                      -- '5.3' or '5.3–5.5' or ''
    sha         text NOT NULL,                      -- of heading and text
    text        text NOT NULL,
    search_text text NOT NULL,                      -- title, headings and text: what is searched and embedded
    cites       jsonb NOT NULL DEFAULT '[]'         -- a guide's [n] resolved to the pages it cites
);
CREATE INDEX IF NOT EXISTS wiki_chunks_path_idx ON wiki_chunks (path);
-- A piece whose text another page holds too (the course programme of every intake, a site's header): the search finds only
-- the piece it is a copy of, and shows where else it stands (search_index.mark_copies).
ALTER TABLE wiki_chunks ADD COLUMN IF NOT EXISTS copy_of bigint REFERENCES wiki_chunks (id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS wiki_chunks_copy_of_idx ON wiki_chunks (copy_of) WHERE copy_of IS NOT NULL;
CREATE TABLE IF NOT EXISTS wiki_chunk_embeddings (
    chunk_id  bigint PRIMARY KEY REFERENCES wiki_chunks (id) ON DELETE CASCADE,
    embedding vector(1024) NOT NULL
);
-- (harrier-oss-v1 was tried as a second vector space and found worse than bge-m3 on the wiki: its table is gone.)
DROP TABLE IF EXISTS wiki_chunk_embeddings_harrier;
-- Retired experimental model profiles; the active vectors stay in wiki_chunk_embeddings.
DROP TABLE IF EXISTS public.wiki_model_embeddings;
CREATE TABLE IF NOT EXISTS wiki_embedding_queue (
    chunk_id  bigint PRIMARY KEY REFERENCES wiki_chunks (id) ON DELETE CASCADE,
    queued_at timestamptz NOT NULL DEFAULT now()
);
-- Which embeddings model made the vectors: another model makes them all invalid.
CREATE TABLE IF NOT EXISTS wiki_meta (
    key   text PRIMARY KEY,
    value text NOT NULL
);
CREATE OR REPLACE FUNCTION enqueue_wiki_embedding() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO wiki_embedding_queue (chunk_id) VALUES (NEW.id)
        ON CONFLICT (chunk_id) DO UPDATE SET queued_at = excluded.queued_at;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS wiki_chunks_enqueue_insert ON wiki_chunks;
CREATE TRIGGER wiki_chunks_enqueue_insert AFTER INSERT ON wiki_chunks
    FOR EACH ROW EXECUTE FUNCTION enqueue_wiki_embedding();
DROP TRIGGER IF EXISTS wiki_chunks_enqueue_edit ON wiki_chunks;
CREATE TRIGGER wiki_chunks_enqueue_edit AFTER UPDATE OF search_text ON wiki_chunks
    FOR EACH ROW WHEN (OLD.search_text IS DISTINCT FROM NEW.search_text) EXECUTE FUNCTION enqueue_wiki_embedding();
-- BM25 with the Russian and the English stemmer, as for messages: the documents are Russian, the guides English.
CREATE INDEX IF NOT EXISTS wiki_chunks_search ON wiki_chunks USING paradedb (
    id,
    (search_text::pdb.simple('stemmer=russian')),
    (search_text::pdb.simple('stemmer=english', 'alias=search_text_en')),
    trust
) WITH (mutable_segment_rows = 100);
CREATE INDEX IF NOT EXISTS wiki_chunk_embeddings_hnsw ON wiki_chunk_embeddings
    USING hnsw (embedding vector_cosine_ops);

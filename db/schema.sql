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

DROP TABLE IF EXISTS bot_users;  -- Telegram notifications were removed

-- The Telegram and MAX chats Moodle courses link to (moodle_chats.py), found when a user's course is synced: a list for
-- the admins to look through; nothing joins them by itself.
CREATE TABLE IF NOT EXISTS proposed_chats (
    link     text PRIMARY KEY,               -- canonical https://t.me/… or https://max.ru/… (chat_links.normalize_link)
    owner    text NOT NULL,                  -- InNoHassle id of the user whose course linked it first
    course   text NOT NULL DEFAULT '',       -- that course's full name
    found_at timestamptz NOT NULL DEFAULT now()
);
DROP TABLE IF EXISTS source_request_join_intents, source_request_lease, source_requests;  -- the moderated chat requests were removed

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

DROP TABLE IF EXISTS bot_admins;
-- cAtIx admins by InNoHassle id. added_by NULL: the row of an ADMIN_INNOHASSLE_IDS admin, kept only for their contacts.
-- email and telegram_id are copied from the admin's own token on each admin request (alerts go to telegram_id).
CREATE TABLE IF NOT EXISTS admins (
    innohassle_id text PRIMARY KEY,
    added_by      text,
    added_at      timestamptz NOT NULL DEFAULT now(),
    email         text,
    telegram_id   bigint
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

-- An offer under an answer of the site goes with its chat (the chat shows the answer, so its button must work); the ones of
-- the Telegram bot have no chat.
ALTER TABLE calendar_proposals ADD COLUMN IF NOT EXISTS chat_id text REFERENCES api_chats (chat_id) ON DELETE CASCADE;

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

DROP TABLE IF EXISTS schedule_changes;  -- schedule changes are no longer detected in chat messages
DELETE FROM calendar_proposals WHERE id LIKE 'change:%';  -- their saved durations

-- Raw opaque calendar subscription keys are intentionally retained only for link retrieval/revocation.
-- The application role needs access; ctx_reader must never read this table (revokes follow below).
CREATE TABLE IF NOT EXISTS calendar_export_keys (
    user_key   text PRIMARY KEY,
    access_key text NOT NULL UNIQUE,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- A user's Moodle data, sent by the InNoHassle browser extension (api/moodle.py, catix/moodle_sync.py). Private to the user:
-- never part of the document indexes or of ctx_reader's views. Every sync replaces it; DELETE /users/my-moodle drops it.
CREATE TABLE IF NOT EXISTS moodle_accounts (
    innohassle_id  text PRIMARY KEY,
    moodle_user_id bigint NOT NULL,
    synced_at      timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS moodle_courses (
    innohassle_id     text NOT NULL REFERENCES moodle_accounts ON DELETE CASCADE,
    course_id         bigint NOT NULL,
    fullname          text NOT NULL,
    shortname         text NOT NULL,
    starts_at         timestamptz,
    ends_at           timestamptz,
    content_synced_at timestamptz,                       -- none: the text of the course was never sent
    PRIMARY KEY (innohassle_id, course_id)
);
CREATE TABLE IF NOT EXISTS moodle_events (
    innohassle_id    text NOT NULL REFERENCES moodle_accounts ON DELETE CASCADE,
    event_id         bigint NOT NULL,
    course_id        bigint,
    name             text NOT NULL,
    description      text,                               -- markdown
    event_type       text NOT NULL,                      -- Moodle's eventtype: due, course, user, site, group, ...
    module           text,                               -- Moodle's modulename: assign, quiz, ...
    starts_at        timestamptz NOT NULL,
    duration_seconds integer NOT NULL DEFAULT 0,
    url              text,
    pending          boolean NOT NULL DEFAULT false,     -- on the Moodle timeline: still to do (a deadline not met yet)
    PRIMARY KEY (innohassle_id, event_id)
);
ALTER TABLE moodle_events ADD COLUMN IF NOT EXISTS group_id bigint;      -- a group event: for this group of the course only
CREATE TABLE IF NOT EXISTS moodle_grades (
    innohassle_id   text NOT NULL,
    course_id       bigint NOT NULL,
    item_id         bigint NOT NULL,
    position        integer NOT NULL,                    -- the order of the Moodle grade report
    name            text NOT NULL,
    item_type       text NOT NULL,                       -- course, category, mod, manual
    module          text,
    grade           double precision,
    grade_min       double precision,
    grade_max       double precision,
    grade_text      text,                                -- gradeformatted, as Moodle shows it
    percentage_text text,
    feedback        text,                                -- markdown
    graded_at       timestamptz,
    PRIMARY KEY (innohassle_id, course_id, item_id),
    FOREIGN KEY (innohassle_id, course_id) REFERENCES moodle_courses ON DELETE CASCADE
);
-- The text of course sections and modules, once per distinct text (sha256 of it): many students of a course send the same.
CREATE TABLE IF NOT EXISTS moodle_texts (
    sha256 text PRIMARY KEY,
    text   text NOT NULL
);
CREATE TABLE IF NOT EXISTS moodle_sections (
    innohassle_id  text NOT NULL,
    course_id      bigint NOT NULL,
    section_id     bigint NOT NULL,
    position       integer NOT NULL,
    name           text NOT NULL,
    summary_sha256 text REFERENCES moodle_texts,
    PRIMARY KEY (innohassle_id, course_id, section_id),
    FOREIGN KEY (innohassle_id, course_id) REFERENCES moodle_courses ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS moodle_modules (
    innohassle_id text NOT NULL,
    course_id     bigint NOT NULL,
    module_id     bigint NOT NULL,                       -- Moodle's course module id (cmid)
    section_id    bigint NOT NULL,
    position      integer NOT NULL,
    name          text NOT NULL,
    module        text NOT NULL,                         -- Moodle's modname: page, label, assign, resource, ...
    url           text,
    text_sha256   text REFERENCES moodle_texts,
    PRIMARY KEY (innohassle_id, course_id, module_id),
    FOREIGN KEY (innohassle_id, course_id, section_id) REFERENCES moodle_sections ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS moodle_assignments (
    innohassle_id     text NOT NULL,
    course_id         bigint NOT NULL,
    assignment_id     bigint NOT NULL,
    module_id         bigint NOT NULL,                   -- cmid
    name              text NOT NULL,
    description       text,                              -- markdown
    opens_at          timestamptz,
    due_at            timestamptz,
    cutoff_at         timestamptz,
    grading_due_at    timestamptz,
    max_grade         double precision,
    submission_status text,                              -- new, draft, submitted, reopened; none: not asked (outside the window) or Moodle did not say
    grading_status    text,                              -- graded, notgraded, ...
    grade             text,                              -- markdown of Moodle's gradefordisplay
    PRIMARY KEY (innohassle_id, course_id, assignment_id),
    FOREIGN KEY (innohassle_id, course_id) REFERENCES moodle_courses ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS moodle_quizzes (
    innohassle_id      text NOT NULL,
    course_id          bigint NOT NULL,
    quiz_id            bigint NOT NULL,
    module_id          bigint NOT NULL,
    name               text NOT NULL,
    description        text,
    opens_at           timestamptz,
    closes_at          timestamptz,
    time_limit_seconds integer,
    attempts_allowed   integer NOT NULL DEFAULT 0,       -- 0: unlimited
    attempts_used      integer,                          -- none: not asked
    best_grade         double precision,
    max_grade          double precision,
    PRIMARY KEY (innohassle_id, course_id, quiz_id),
    FOREIGN KEY (innohassle_id, course_id) REFERENCES moodle_courses ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS moodle_completion (
    innohassle_id text NOT NULL,
    course_id     bigint NOT NULL,
    module_id     bigint NOT NULL,
    state         smallint NOT NULL CHECK (state BETWEEN 0 AND 3),  -- Moodle: 0 incomplete, 1 complete, 2 complete pass, 3 complete fail
    completed_at  timestamptz,
    PRIMARY KEY (innohassle_id, course_id, module_id),
    FOREIGN KEY (innohassle_id, course_id) REFERENCES moodle_courses ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS moodle_groups (
    innohassle_id text NOT NULL,
    course_id     bigint NOT NULL,
    group_id      bigint NOT NULL,
    name          text NOT NULL,
    PRIMARY KEY (innohassle_id, course_id, group_id),
    FOREIGN KEY (innohassle_id, course_id) REFERENCES moodle_courses ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS moodle_announcements (
    innohassle_id text NOT NULL,
    course_id     bigint NOT NULL,
    discussion_id bigint NOT NULL,
    position      integer NOT NULL,
    title         text NOT NULL,
    text_sha256   text REFERENCES moodle_texts,
    posted_at     timestamptz NOT NULL,
    PRIMARY KEY (innohassle_id, course_id, discussion_id),
    FOREIGN KEY (innohassle_id, course_id) REFERENCES moodle_courses ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS moodle_files (                 -- names and links only, never the file
    innohassle_id text NOT NULL,
    course_id     bigint NOT NULL,
    module_id     bigint NOT NULL,
    position      integer NOT NULL,
    filename      text NOT NULL,
    url           text NOT NULL,                         -- https://moodle.innopolis.university/pluginfile.php/..., opens for a signed-in browser
    size_bytes    bigint,
    mime_type     text,
    modified_at   timestamptz,
    PRIMARY KEY (innohassle_id, course_id, module_id, position),
    FOREIGN KEY (innohassle_id, course_id, module_id) REFERENCES moodle_modules ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS moodle_sections_text_idx ON moodle_sections (summary_sha256);
CREATE INDEX IF NOT EXISTS moodle_modules_text_idx ON moodle_modules (text_sha256);
CREATE INDEX IF NOT EXISTS moodle_announcements_text_idx ON moodle_announcements (text_sha256);
ALTER TABLE moodle_accounts ADD COLUMN IF NOT EXISTS study_groups text[] NOT NULL DEFAULT '{}';  -- InNoHassle-verified study groups at the last overview sync: they read the shareable materials of this user's courses
CREATE INDEX IF NOT EXISTS moodle_accounts_groups_idx ON moodle_accounts USING gin (study_groups);
ALTER TABLE moodle_sections ADD COLUMN IF NOT EXISTS shareable boolean NOT NULL DEFAULT false;  -- visible to every student of the course (the extension decides)
ALTER TABLE moodle_modules ADD COLUMN IF NOT EXISTS shareable boolean NOT NULL DEFAULT false;   -- visible to every student, and in a shareable section

ALTER TABLE moodle_files ADD COLUMN IF NOT EXISTS sha256 text;        -- of the file's bytes; none: not offered (type or size)
CREATE INDEX IF NOT EXISTS moodle_files_sha256_idx ON moodle_files (sha256) WHERE sha256 IS NOT NULL;
-- The course files the extension uploaded, once per distinct file (sha256 of the bytes), with their extraction state: a queue
-- read by the moodle-files thread of `catix-worker` (worker/moodle_reader.py). Deleted once no moodle_files row
-- of any user has its sha256 (moodle_sync._gc_files).
CREATE TABLE IF NOT EXISTS moodle_blobs (
    sha256       text PRIMARY KEY,
    suffix       text NOT NULL,                             -- '.pdf', '.pptx', ...: how it is read
    size_bytes   bigint NOT NULL,
    data         bytea NOT NULL,
    status       text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'claimed', 'done', 'skipped', 'failed')),
    attempts     integer NOT NULL DEFAULT 0,
    available_at timestamptz NOT NULL DEFAULT now(),
    token        text,
    lease_until  timestamptz,
    method       text,                                      -- 'text layer (opendataloader)', 'ocr (LightOnOCR)', 'plain text'
    pages        integer,
    note         text,                                      -- why skipped or failed
    uploaded_at  timestamptz NOT NULL DEFAULT now(),
    extracted_at timestamptz
);
CREATE INDEX IF NOT EXISTS moodle_blobs_queue_idx ON moodle_blobs (available_at) WHERE status IN ('pending', 'claimed');
-- Pieces of a file (sha256) or of a course text (text_sha256).
CREATE TABLE IF NOT EXISTS moodle_blob_chunks (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sha256      text NOT NULL REFERENCES moodle_blobs ON DELETE CASCADE,
    seq         integer NOT NULL,
    heading     text NOT NULL,
    text        text NOT NULL,
    search_text text NOT NULL                               -- filename, headings and text: what is searched and embedded
);
CREATE INDEX IF NOT EXISTS moodle_blob_chunks_sha256_idx ON moodle_blob_chunks (sha256);
ALTER TABLE moodle_blob_chunks ADD COLUMN IF NOT EXISTS page integer;   -- the PDF page (slide) of a file's piece; none: not paged (.txt/.md, course text)
ALTER TABLE moodle_blob_chunks ADD COLUMN IF NOT EXISTS text_sha256 text REFERENCES moodle_texts ON DELETE CASCADE;  -- a piece of a course text instead of a file
ALTER TABLE moodle_blob_chunks ALTER COLUMN sha256 DROP NOT NULL;
ALTER TABLE moodle_blob_chunks DROP CONSTRAINT IF EXISTS moodle_blob_chunks_one_source;
ALTER TABLE moodle_blob_chunks ADD CONSTRAINT moodle_blob_chunks_one_source CHECK (num_nonnulls(sha256, text_sha256) = 1);
CREATE INDEX IF NOT EXISTS moodle_blob_chunks_text_idx ON moodle_blob_chunks (text_sha256) WHERE text_sha256 IS NOT NULL;
ALTER TABLE moodle_texts ADD COLUMN IF NOT EXISTS chunked boolean NOT NULL DEFAULT false;  -- its pieces are in moodle_blob_chunks (moodle_files.chunk_texts)
CREATE INDEX IF NOT EXISTS moodle_texts_unchunked_idx ON moodle_texts (sha256) WHERE NOT chunked;
-- Files read before pieces had pages are read again once (a re-read sets page on every piece of a PDF or image).
UPDATE moodle_blobs b SET status = 'pending', attempts = 0, available_at = now(), note = NULL
WHERE b.status = 'done' AND b.suffix NOT IN ('.txt', '.md')
  AND EXISTS (SELECT 1 FROM moodle_blob_chunks c WHERE c.sha256 = b.sha256 AND c.page IS NULL);
CREATE TABLE IF NOT EXISTS moodle_blob_chunk_embeddings (
    chunk_id  bigint PRIMARY KEY REFERENCES moodle_blob_chunks (id) ON DELETE CASCADE,
    embedding vector(1024) NOT NULL
);
CREATE TABLE IF NOT EXISTS moodle_blob_embedding_queue (
    chunk_id  bigint PRIMARY KEY REFERENCES moodle_blob_chunks (id) ON DELETE CASCADE,
    queued_at timestamptz NOT NULL DEFAULT now()
);
CREATE OR REPLACE FUNCTION enqueue_moodle_blob_embedding() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO moodle_blob_embedding_queue (chunk_id) VALUES (NEW.id) ON CONFLICT (chunk_id) DO NOTHING;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS moodle_blob_chunks_enqueue ON moodle_blob_chunks;
CREATE TRIGGER moodle_blob_chunks_enqueue AFTER INSERT ON moodle_blob_chunks
    FOR EACH ROW EXECUTE FUNCTION enqueue_moodle_blob_embedding();
DROP INDEX IF EXISTS moodle_blob_chunks_search;
CREATE INDEX IF NOT EXISTS moodle_blob_chunks_search_2 ON moodle_blob_chunks USING paradedb (
    id,
    (search_text::pdb.simple('stemmer=russian')),
    (search_text::pdb.simple('stemmer=english', 'alias=search_text_en')),
    sha256,
    text_sha256
) WITH (mutable_segment_rows = 100);
CREATE INDEX IF NOT EXISTS moodle_blob_chunk_embeddings_hnsw ON moodle_blob_chunk_embeddings USING hnsw (embedding vector_cosine_ops);

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM ctx_reader;
REVOKE ALL ON SCHEMA public FROM ctx_reader;
GRANT USAGE ON SCHEMA visible TO ctx_reader;
GRANT SELECT ON visible.chats, visible.messages TO ctx_reader;

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
-- The documents of the sources (catix-docs, src/catix/docs/): a document is a markdown body with its meta, cut into the
-- pieces the agent searches. A document is cut again only when it (or the cutting scheme) changed; a piece whose text
-- stayed the same keeps its row and its vector, so an update embeds only what is new.
-- ---------------------------------------------------------------------------------------------------------
-- The tables were called wiki_*, and their documents were keyed by the files of a wiki ('/raw/regulations/x.md').
-- Renamed once: the pieces follow their document's new path (ON UPDATE CASCADE), their vectors stay.
DO $$
BEGIN
    IF to_regclass('public.wiki_pages') IS NOT NULL AND to_regclass('public.documents') IS NULL THEN
        ALTER TABLE wiki_pages RENAME TO documents;
        ALTER TABLE wiki_chunks RENAME TO document_chunks;
        ALTER TABLE wiki_chunk_embeddings RENAME TO document_chunk_embeddings;
        ALTER TABLE wiki_embedding_queue RENAME TO document_embedding_queue;
        ALTER TABLE wiki_meta RENAME TO docs_meta;
        ALTER INDEX wiki_chunks_path_idx RENAME TO document_chunks_path_idx;
        ALTER INDEX wiki_chunks_copy_of_idx RENAME TO document_chunks_copy_of_idx;
        ALTER INDEX wiki_chunk_embeddings_hnsw RENAME TO document_chunk_embeddings_hnsw;
        DROP INDEX wiki_chunks_search;
        DROP TRIGGER wiki_chunks_enqueue_insert ON document_chunks;
        DROP TRIGGER wiki_chunks_enqueue_edit ON document_chunks;
        DROP FUNCTION enqueue_wiki_embedding();
        ALTER TABLE documents ADD COLUMN body text NOT NULL DEFAULT '', ADD COLUMN meta jsonb NOT NULL DEFAULT '{}'::jsonb;
        ALTER TABLE documents DROP CONSTRAINT IF EXISTS wiki_pages_trust_check;
        ALTER TABLE documents ADD CONSTRAINT documents_trust_check CHECK (trust IN ('official', 'wiki'));
        ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS wiki_chunks_path_fkey;
        ALTER TABLE document_chunks ADD CONSTRAINT document_chunks_path_fkey
            FOREIGN KEY (path) REFERENCES documents (path) ON DELETE CASCADE ON UPDATE CASCADE;
        UPDATE documents SET path = CASE
            WHEN resource LIKE 'https://eduwiki.innopolis.university/%' THEN 'eduwiki/' || regexp_replace(path, '^/raw/(.*)\.md$', '\1')
            ELSE regexp_replace(path, '^/raw/(.*)\.md$', '\1') END
        WHERE path ~ '^/raw/.*\.md$';
    END IF;
END $$;
CREATE TABLE IF NOT EXISTS documents (
    path           text PRIMARY KEY,                -- 'regulations/attestation-regulation', 'sites/hotel/roomfund', 'eduwiki/courses/…'
    sha            text NOT NULL,                   -- of the document and the cutting scheme
    title          text NOT NULL,
    type           text NOT NULL,
    trust          text NOT NULL CHECK (trust IN ('official', 'wiki')),  -- a document of the university, a page of eduwiki or of a site
    audience       text[] NOT NULL DEFAULT '{}',
    resource       text,                            -- the original: a PDF on the university's site or an eduwiki page
    status         text,                            -- 'current' or 'unlisted' (no page of the site links it any more); "outdated" is stale_after in the past, worked out at search time
    review         text,                            -- what in the document nobody checked, if anything
    source_warning text,
    stale_after    date,
    issued         date,                            -- when the source was issued or last edited (newer documents replace older ones)
    indexed_at     timestamptz NOT NULL DEFAULT now(),
    body           text NOT NULL DEFAULT '',        -- the markdown
    meta           jsonb NOT NULL DEFAULT '{}'      -- what the source knows of it (sources, archive member, ...)
);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS site text;  -- the site the document comes from: 'hotel', 'university', ... ('eduwiki', 'guide')
CREATE INDEX IF NOT EXISTS documents_site_idx ON documents (site);
CREATE INDEX IF NOT EXISTS documents_issued_idx ON documents (issued);
CREATE TABLE IF NOT EXISTS document_chunks (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path        text NOT NULL REFERENCES documents (path) ON DELETE CASCADE ON UPDATE CASCADE,
    trust       text NOT NULL,                      -- copied from the document: the search filters by it inside the index
    seq         int NOT NULL,                       -- order in the document
    heading     text NOT NULL,                      -- 'Chapter > Section'
    clause      text NOT NULL,                      -- '5.3' or '5.3–5.5' or ''
    sha         text NOT NULL,                      -- of heading and text
    text        text NOT NULL,
    search_text text NOT NULL,                      -- title, headings and text: what is searched and embedded
    cites       jsonb NOT NULL DEFAULT '[]',        -- the [n] of the text resolved to the pages the document cites
    -- A piece whose text another document holds too (the course programme of every intake, a site's header): the search finds
    -- only the piece it is a copy of, and shows where else it stands (docs/store.py mark_copies).
    copy_of     bigint REFERENCES document_chunks (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS document_chunks_path_idx ON document_chunks (path);
CREATE INDEX IF NOT EXISTS document_chunks_copy_of_idx ON document_chunks (copy_of) WHERE copy_of IS NOT NULL;
CREATE TABLE IF NOT EXISTS document_chunk_embeddings (
    chunk_id  bigint PRIMARY KEY REFERENCES document_chunks (id) ON DELETE CASCADE,
    embedding vector(1024) NOT NULL
);
-- (harrier-oss-v1 was tried as a second vector space and found worse than bge-m3: its table is gone.)
DROP TABLE IF EXISTS wiki_chunk_embeddings_harrier;
-- Retired experimental model profiles; the active vectors stay in document_chunk_embeddings.
DROP TABLE IF EXISTS public.wiki_model_embeddings;
CREATE TABLE IF NOT EXISTS document_embedding_queue (
    chunk_id  bigint PRIMARY KEY REFERENCES document_chunks (id) ON DELETE CASCADE,
    queued_at timestamptz NOT NULL DEFAULT now()
);
-- Which embeddings model made the vectors: another model makes them all invalid. Also the state of `catix-docs run`.
CREATE TABLE IF NOT EXISTS docs_meta (
    key   text PRIMARY KEY,
    value text NOT NULL
);
CREATE OR REPLACE FUNCTION enqueue_document_embedding() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO document_embedding_queue (chunk_id) VALUES (NEW.id)
        ON CONFLICT (chunk_id) DO UPDATE SET queued_at = excluded.queued_at;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS document_chunks_enqueue_insert ON document_chunks;
CREATE TRIGGER document_chunks_enqueue_insert AFTER INSERT ON document_chunks
    FOR EACH ROW EXECUTE FUNCTION enqueue_document_embedding();
DROP TRIGGER IF EXISTS document_chunks_enqueue_edit ON document_chunks;
CREATE TRIGGER document_chunks_enqueue_edit AFTER UPDATE OF search_text ON document_chunks
    FOR EACH ROW WHEN (OLD.search_text IS DISTINCT FROM NEW.search_text) EXECUTE FUNCTION enqueue_document_embedding();
-- BM25 with the Russian and the English stemmer, as for messages.
CREATE INDEX IF NOT EXISTS document_chunks_search ON document_chunks USING paradedb (
    id,
    (search_text::pdb.simple('stemmer=russian')),
    (search_text::pdb.simple('stemmer=english', 'alias=search_text_en')),
    trust
) WITH (mutable_segment_rows = 100);
CREATE INDEX IF NOT EXISTS document_chunk_embeddings_hnsw ON document_chunk_embeddings
    USING hnsw (embedding vector_cosine_ops);
-- The catalog of sites (catix-docs sites catalog): one column per field of sources/sites.py Site, the same defaults.
CREATE TABLE IF NOT EXISTS site_catalog (
    name text PRIMARY KEY CHECK (name ~ '^[a-z0-9][a-z0-9-]*$'),
    base text NOT NULL CHECK (base ~ '^https?://[^/]+/'),
    language text NOT NULL CHECK (language IN ('ru', 'en')),
    about text NOT NULL,
    skip text NOT NULL DEFAULT '',
    sitemap text DEFAULT 'sitemap.xml',      -- NULL: no sitemap (Site.sitemap False); a path: Site.sitemap (True = 'sitemap.xml')
    max_pages integer NOT NULL DEFAULT 60 CHECK (max_pages > 0),
    english text,
    dated boolean NOT NULL DEFAULT false,
    render boolean NOT NULL DEFAULT false,
    robots boolean NOT NULL DEFAULT false,
    pause real CHECK (pause >= 0),
    headings text,
    bare boolean NOT NULL DEFAULT false,
    listing text,
    "end" text,
    drop text,
    profile text,
    audience text[],
    discover text,
    missing text,
    signin text,
    private text,
    feeds text[] NOT NULL DEFAULT '{}',
    aliases text[] NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS blocked_hosts (host text PRIMARY KEY);

-- The crawl (src/catix/docs/frontier.py): one row per address, and the links between them.
CREATE TABLE IF NOT EXISTS crawl_urls (
    address text PRIMARY KEY,                -- sites.address(url)
    url text NOT NULL,
    site text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('page', 'listing', 'document')),
    pinned boolean NOT NULL DEFAULT false,
    every interval NOT NULL,
    next_at timestamptz,                     -- NULL: never read again
    priority smallint NOT NULL DEFAULT 1,    -- 0 request, 1 new, 2 recheck
    state text NOT NULL DEFAULT 'new' CHECK (state IN ('new', 'ok', 'missing', 'gone', 'tried')),
    why text,
    slug text,                               -- pages: documents path sites/<site>/<slug>
    doc_key text UNIQUE,                     -- documents: key of document_files / archives
    ext text,
    title text,
    sha256 text,
    validators jsonb NOT NULL DEFAULT '{}',
    short_words integer,
    text text,                               -- pages: markdown
    audience text[],
    fetched_at timestamptz,
    read_at timestamptz,
    unlinked_since date,
    CHECK ((kind = 'document') = (doc_key IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS crawl_urls_due ON crawl_urls (priority, next_at) WHERE next_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS crawl_urls_site ON crawl_urls (site, kind, state);
CREATE UNIQUE INDEX IF NOT EXISTS crawl_urls_slug ON crawl_urls (site, slug) WHERE slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS crawl_urls_words ON crawl_urls (site, sha256) WHERE kind = 'page';
CREATE TABLE IF NOT EXISTS crawl_links (
    src text NOT NULL REFERENCES crawl_urls (address) ON DELETE CASCADE ON UPDATE CASCADE,
    dst text NOT NULL,                       -- sites.address(link): every http(s) link, trusted or not
    anchor text NOT NULL DEFAULT '',
    context text NOT NULL DEFAULT '',
    PRIMARY KEY (src, dst)
);
CREATE INDEX IF NOT EXISTS crawl_links_dst ON crawl_links (dst);

-- A document file read (docs/notes.py): its note (what regulations._fetch_once knows of it) and its text. revision: '' for
-- a file at its URL; the content sha of an archive member or of an archive URL that served a PDF (revisions coexist until read).
CREATE TABLE IF NOT EXISTS document_files (
    key text NOT NULL,
    revision text NOT NULL DEFAULT '',
    url text, title text, section text, context text,
    sha256 text, method text, chars integer, tables smallint, pdf_created text,
    remote jsonb NOT NULL DEFAULT '{}',
    ocr text CHECK (ocr IN ('queued', 'too long')), pages integer, queued_at timestamptz, ocr_failed integer,
    skipped text, failed text, tried_at timestamptz, checked_at timestamptz, fetched_at timestamptz,
    refetch boolean NOT NULL DEFAULT false, force boolean NOT NULL DEFAULT false,
    text text,
    PRIMARY KEY (key, revision)
);
CREATE INDEX IF NOT EXISTS document_files_ocr ON document_files (ocr) WHERE ocr IS NOT NULL;

-- The manifest of an archive container (sources/archive_documents.py), published whole after a safe extraction.
CREATE TABLE IF NOT EXISTS archives (
    key text PRIMARY KEY, url text NOT NULL, sha256 text, remote jsonb NOT NULL DEFAULT '{}',
    status text, error text, refetch boolean NOT NULL DEFAULT false, tried_at timestamptz,
    document jsonb, members jsonb NOT NULL DEFAULT '[]'
);

-- Course programmes (sources/rpd.py): one per PDF of a РПД archive; and what the site said of each archive.
CREATE TABLE IF NOT EXISTS course_programmes (
    key text PRIMARY KEY, archive text NOT NULL, archive_title text, member text, programme text, level text,
    year integer, semester integer, kind text, code text, name text, fetched_at timestamptz,
    sha256 text, method text, chars integer, skipped text, text text
);
CREATE TABLE IF NOT EXISTS rpd_archives (url text PRIMARY KEY, remote jsonb NOT NULL DEFAULT '{}', failed text, tried_at timestamptz);

-- The snapshot of the eduwiki (sources/eduwiki.py).
CREATE TABLE IF NOT EXISTS eduwiki_pages (
    pageid integer PRIMARY KEY, ns integer NOT NULL, title text NOT NULL, revid bigint NOT NULL,
    redirect boolean NOT NULL DEFAULT false, deleted boolean NOT NULL DEFAULT false,
    timestamp timestamptz, wikitext text, fetched_at timestamptz
);

-- Minimal users table for FB-03 (login). Mohammed's FB-11 schema will extend/replace this.
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    org_name      TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('donor', 'charity', 'admin')),
    -- FB-12 (admin approval) flips this to 'approved' or 'rejected'
    status        TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (length(trim(email)) > 0),
    password_hash TEXT NOT NULL CHECK (length(trim(password_hash)) > 0),
    role TEXT NOT NULL CHECK (role IN ('student', 'staff'))
);

-- Each row represents one physical item or complete kit; asset_id is its label.
CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY,
    asset_id TEXT NOT NULL UNIQUE CHECK (length(trim(asset_id)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    category TEXT NOT NULL CHECK (length(trim(category)) > 0),
    description TEXT NOT NULL,
    condition TEXT NOT NULL DEFAULT 'good' CHECK (length(trim(condition)) > 0),
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'reserved', 'checked_out', 'maintenance'))
);

-- ISO calendar dates are sortable strings. Validate both format and real dates.
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE RESTRICT,
    pickup_date TEXT NOT NULL CHECK (
        length(pickup_date) = 10 AND date(pickup_date, '+0 days') IS pickup_date),
    return_date TEXT NOT NULL CHECK (
        length(return_date) = 10 AND date(return_date, '+0 days') IS return_date
        AND return_date > pickup_date),
    status TEXT NOT NULL DEFAULT 'reserved'
        CHECK (status IN ('reserved', 'checked_out', 'cancelled', 'completed')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (id, user_id, equipment_id)
);

-- A loan always names its borrower/item. Its optional reservation supports Req 12
-- walk-ins; the composite reference prevents linking a different borrower/item.
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE RESTRICT,
    reservation_id INTEGER UNIQUE,
    checkout_date TEXT NOT NULL CHECK (
        length(checkout_date) = 10 AND date(checkout_date, '+0 days') IS checkout_date),
    due_date TEXT NOT NULL CHECK (
        length(due_date) = 10 AND date(due_date, '+0 days') IS due_date
        AND due_date > checkout_date),
    actual_return_date TEXT CHECK (actual_return_date IS NULL OR (
        length(actual_return_date) = 10
        AND date(actual_return_date, '+0 days') IS actual_return_date
        AND actual_return_date >= checkout_date)),
    status TEXT NOT NULL DEFAULT 'checked_out'
        CHECK (status IN ('checked_out', 'returned')),
    CHECK ((status = 'returned' AND actual_return_date IS NOT NULL)
        OR (status = 'checked_out' AND actual_return_date IS NULL)),
    FOREIGN KEY (reservation_id, user_id, equipment_id)
        REFERENCES reservations(id, user_id, equipment_id) ON DELETE RESTRICT
);

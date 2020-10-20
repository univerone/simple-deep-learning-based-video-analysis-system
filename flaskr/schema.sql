-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS TASK;

CREATE TABLE TASK (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  finished TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  filename TEXT NOT NULL,
  status TEXT NOT NULL,
  result TEXT DEFAULT ''
);

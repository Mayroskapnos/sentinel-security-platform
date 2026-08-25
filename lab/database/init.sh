#!/bin/sh
set -eu

psql --set ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set app_user="$LAB_DB_USER" \
  --set app_password="$LAB_DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password') \gexec

CREATE TABLE departments (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE employees (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username text NOT NULL UNIQUE,
    display_name text NOT NULL,
    department text NOT NULL
);

CREATE TABLE inventory (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_tag text NOT NULL UNIQUE,
    item_name text NOT NULL,
    state text NOT NULL
);

INSERT INTO departments (name) VALUES ('Engineering'), ('Operations'), ('Finance');
INSERT INTO employees (username, display_name, department) VALUES
    ('demo-user', 'Demo User', 'Engineering'),
    ('ops-user', 'Operations User', 'Operations');
INSERT INTO inventory (asset_tag, item_name, state) VALUES
    ('LAB-1001', 'Demo Laptop', 'assigned'),
    ('LAB-2001', 'Demo Monitor', 'in_stock');

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user'
) \gexec
GRANT USAGE ON SCHEMA public TO :"app_user";
GRANT SELECT ON departments, employees, inventory TO :"app_user";
SQL

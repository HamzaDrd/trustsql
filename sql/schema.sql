-- Final database schema. The pipeline runs this file before loading,
-- so the tables are always rebuilt from scratch (idempotent).

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS employees;

CREATE TABLE customers (
    customer_id  INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT UNIQUE,
    country      TEXT,
    city         TEXT,
    signup_date  DATE
);

CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT,
    price       REAL NOT NULL CHECK (price >= 0),
    cost        REAL CHECK (cost >= 0)
);

CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date   DATE NOT NULL,
    status       TEXT CHECK (status IN ('completed', 'cancelled', 'refunded'))
);

CREATE TABLE order_items (
    order_item_id  INTEGER PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES orders(order_id),
    product_id     INTEGER NOT NULL REFERENCES products(product_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price     REAL NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE employees (
    employee_id  INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    department   TEXT,
    salary       INTEGER CHECK (salary > 0),
    hire_date    DATE
);

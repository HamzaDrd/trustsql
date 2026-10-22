-- Post-load checks, written in SQL.
-- Each query must return 0. Anything else means the loaded data is wrong.
-- Each query is preceded by a comment line naming the check.

-- check: orders without any order items
SELECT COUNT(*) FROM orders o
WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = o.order_id);

-- check: order items with a non-positive line total
SELECT COUNT(*) FROM order_items WHERE quantity * unit_price <= 0;

-- check: orders placed before the customer signed up
SELECT COUNT(*) FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_date < c.signup_date;

-- check: products sold below cost price in the catalog
SELECT COUNT(*) FROM products WHERE cost > price;

-- check: duplicate customer emails
SELECT COUNT(*) FROM (
    SELECT email FROM customers WHERE email IS NOT NULL
    GROUP BY email HAVING COUNT(*) > 1
);

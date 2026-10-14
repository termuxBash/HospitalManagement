-- =======================================================
-- DCL (Data Control Language) Operations in MySQL
-- Demonstrates: CREATE USER, SELECT, GRANT, FLUSH PRIVILEGES,
--               switching users, testing permissions, REVOKE,
--               and verifying permission denied error.
-- =======================================================

-- 1. Create a new MySQL user 'kunj' identified by password (replace 'YOUR NAME' with your password)
CREATE USER IF NOT EXISTS 'kunj'@'localhost' IDENTIFIED BY 'YOUR NAME';

-- 2. View all MySQL users to verify 'kunj' exists
SELECT user, host FROM mysql.user;

-- 3. Grant ALL privileges on the product table to 'kunj'
GRANT ALL PRIVILEGES ON hospital.product TO 'kunj'@'localhost';

-- 4. Flush privileges to apply changes immediately
FLUSH PRIVILEGES;

-- 5. Specifically grant INSERT privilege on product to 'kunj'
GRANT INSERT ON hospital.product TO 'kunj'@'localhost';
FLUSH PRIVILEGES;

-- =======================================================
-- Testing as user 'kunj':
-- Open a terminal and run:
--   mysql -u kunj -p
-- Enter password: YOUR NAME
-- USE hospital;
-- INSERT INTO product VALUES (12, 'oreo', 40, 10, 'biscuit');
-- SELECT * FROM product WHERE product_id = 12;
-- =======================================================

-- 6. Revoke INSERT privilege from 'kunj'
-- (Also ensure ALL PRIVILEGES isn't bypassing the revoke)
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'kunj'@'localhost';
GRANT SELECT ON hospital.product TO 'kunj'@'localhost';
FLUSH PRIVILEGES;

-- Alternative direct revoke if only INSERT was granted:
-- REVOKE INSERT ON hospital.product FROM 'kunj'@'localhost';
-- FLUSH PRIVILEGES;

-- =======================================================
-- Testing verification after REVOKE:
-- In user kunj's terminal, try inserting again:
--   INSERT INTO product VALUES (13, 'maggi', 15, 20, 'noodles');
--
-- Expected Output / Error Message:
--   ERROR 1142 (42000): INSERT command denied to user 'kunj'@'localhost' for table 'product'
-- =======================================================

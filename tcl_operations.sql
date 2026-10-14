-- =======================================================
-- TCL (Transaction Control Language) Operations in MySQL
-- Demonstrates: START TRANSACTION, COMMIT, ROLLBACK,
--               SAVEPOINT, and ROLLBACK TO SAVEPOINT.
-- Note: MySQL InnoDB engine is required for transactions.
-- =======================================================

USE hospital;

-- Reset any previously inserted test products (8, 9, 10, 11) for repeatable execution
DELETE FROM product WHERE product_id >= 8;

-- Verify initial product table contents (rows 1 to 7)
SELECT * FROM product;

-- -------------------------------------------------------
-- Part 1: START TRANSACTION and COMMIT
-- -------------------------------------------------------
START TRANSACTION;

-- Insert new product 'biscuit' with product_id 10
INSERT INTO product(product_id, name) VALUES (10, 'biscuit');

-- Permanently save changes to the database
COMMIT;

-- biscuit (product_id 10) is now permanently saved
SELECT * FROM product;

-- -------------------------------------------------------
-- Part 2: Testing ROLLBACK on committed data
-- -------------------------------------------------------
-- Because COMMIT was executed earlier, ROLLBACK here has no effect on biscuit
ROLLBACK;

-- Verify all 8 rows remain intact
SELECT * FROM product;

-- -------------------------------------------------------
-- Part 3: SAVEPOINT and ROLLBACK TO SAVEPOINT
-- -------------------------------------------------------
START TRANSACTION;

-- Insert 'amul milk' (product_id 8) and 'Dairy' (product_id 11)
INSERT INTO product(product_id, name) VALUES (8, 'amul milk');
INSERT INTO product(product_id, name) VALUES (11, 'Dairy');

-- Create a savepoint marker 'sp1'
SAVEPOINT sp1;

SELECT * FROM product;

-- Insert 'amul chocolate' (product_id 9) AFTER savepoint sp1
INSERT INTO product(product_id, name) VALUES (9, 'amul chocolate');

-- Table now temporarily shows 11 rows in this transaction
SELECT * FROM product;

-- Rollback uncommitted changes back to savepoint 'sp1'
-- This reverts 'amul chocolate' (9) while keeping 'amul milk' (8) and 'Dairy' (11)
ROLLBACK TO SAVEPOINT sp1;

-- Commit the remaining transaction
COMMIT;

-- Verify final results:
-- 'amul chocolate' (9) is NOT saved because SAVEPOINT sp1 was rollbacked!
SELECT * FROM product;

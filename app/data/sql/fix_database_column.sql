-- Fix database column name mismatch
-- Run this in MySQL Workbench

USE bidding_auction_db;

-- Check if column exists with old name
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'bidding_auction_db' 
  AND TABLE_NAME = 'auction_outcomes' 
  AND COLUMN_NAME = 'hours_remaining';

-- If the above query returns a row, then run this ALTER statement:
ALTER TABLE auction_outcomes 
CHANGE COLUMN hours_remaining hours_remaining_at_decision DECIMAL(5,2);

-- Verify the change
DESCRIBE auction_outcomes;




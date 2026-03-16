-- Supabase table creation script for Domain Auction Bidding Agent
-- Run this in your Supabase SQL Editor to create the required tables

-- Auction outcomes table
CREATE TABLE IF NOT EXISTS auction_outcomes (
    id SERIAL PRIMARY KEY,
    auction_id VARCHAR(255) UNIQUE NOT NULL,
    domain VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ,
    estimated_value DECIMAL(10,2),
    current_bid_at_decision DECIMAL(10,2),
    final_price DECIMAL(10,2),
    num_bidders INT,
    hours_remaining_at_decision DECIMAL(5,2),
    bot_detected BOOLEAN DEFAULT FALSE,
    strategy_used VARCHAR(50),
    recommended_bid DECIMAL(10,2),
    decision_source VARCHAR(50),
    confidence DECIMAL(3,2),
    result VARCHAR(20),
    profit_margin DECIMAL(5,4),
    opponent_hash VARCHAR(255),
    raw_data JSONB  -- JSONB for native JSON storage with indexing
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_platform ON auction_outcomes(platform);
CREATE INDEX IF NOT EXISTS idx_estimated_value ON auction_outcomes(estimated_value);
CREATE INDEX IF NOT EXISTS idx_timestamp ON auction_outcomes(timestamp);
CREATE INDEX IF NOT EXISTS idx_result ON auction_outcomes(result);


CREATE TABLE IF NOT EXISTS auction_rounds(
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    round_number INT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    estimated_value DECIMAL(10,2),
    current_bid_at_decision DECIMAL(10,2),
    strategy_used VARCHAR(50),
    recommended_bid DECIMAL(10,2),
    decision_source VARCHAR(50),
    confidence DECIMAL(3,2),
    result_round VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(thread_id, round_number)
);
CREATE INDEX IF NOT EXISTS idx_auction_rounds_thread ON auction_rounds(thread_id);

-- Opponent profiles table
CREATE TABLE IF NOT EXISTS opponent_profiles (
    opponent_id VARCHAR(255) PRIMARY KEY,
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    encounter_count INT DEFAULT 0,
    is_likely_bot BOOLEAN DEFAULT FALSE,
    avg_reaction_time DECIMAL(8,2),
    aggression_scores JSONB,  -- JSONB for array storage
    platforms JSONB,           -- JSONB for array storage
    wins INT DEFAULT 0,
    losses INT DEFAULT 0
);

-- Strategy performance table
CREATE TABLE IF NOT EXISTS strategy_performance (
    id SERIAL PRIMARY KEY,
    strategy VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    value_tier VARCHAR(20) NOT NULL,
    total_uses INT DEFAULT 0,
    wins INT DEFAULT 0,
    total_profit DECIMAL(12,2) DEFAULT 0,
    UNIQUE(strategy, platform, value_tier)
);

-- Create indexes for strategy performance
CREATE INDEX IF NOT EXISTS idx_strategy_perf_lookup ON strategy_performance(strategy, platform, value_tier);

-- Enable Row Level Security (optional, for security)
ALTER TABLE auction_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE opponent_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategy_performance ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations for authenticated users (adjust as needed)
CREATE POLICY "Enable all operations for service role" ON auction_outcomes
    FOR ALL USING (true);

CREATE POLICY "Enable all operations for service role" ON opponent_profiles
    FOR ALL USING (true);

CREATE POLICY "Enable all operations for service role" ON strategy_performance
    FOR ALL USING (true);

-- Optional: Add comments for documentation
COMMENT ON TABLE auction_outcomes IS 'Stores completed auction outcomes for learning and analysis';
COMMENT ON TABLE opponent_profiles IS 'Tracks recurring opponent bidders and their behavior patterns';
COMMENT ON TABLE strategy_performance IS 'Aggregated performance metrics for each strategy by context';



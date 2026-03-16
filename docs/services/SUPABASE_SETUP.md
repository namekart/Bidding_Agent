# Supabase Setup Guide

This guide explains how to set up Supabase for the Domain Auction Bidding Agent's history tracking features.

## Prerequisites

1. A Supabase account (sign up at https://supabase.com)
2. Python package: `supabase` installed

## Step 1: Install Supabase Python Client

```bash
pip install supabase
```

## Step 2: Create Supabase Project

1. Go to https://app.supabase.com
2. Click "New Project"
3. Fill in:
   - Name: `domain-auction-agent` (or your preferred name)
   - Database Password: (choose a strong password)
   - Region: (select closest to you)
4. Click "Create new project" and wait for setup to complete

## Step 3: Get Your Credentials

1. Go to Project Settings → API
2. Copy the following:
   - **Project URL**: `https://your-project-id.supabase.co`
   - **Service Role Key** (secret): `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   
   ⚠️ **Use the Service Role Key**, not the anon/public key, for server-side operations.

## Step 4: Create Database Tables

1. In your Supabase dashboard, go to **SQL Editor**
2. Click "New Query"
3. Copy the entire contents of `supabase_tables.sql` and paste it
4. Click "Run" to execute the SQL
5. Verify tables were created: Go to **Table Editor** and you should see:
   - `auction_outcomes`
   - `opponent_profiles`
   - `strategy_performance`

## Step 5: Configure Environment Variables

Create or update your `.env` file in the project root:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-service-role-key

# LLM Configuration (if using)
OPENROUTER_API_KEY=your_openrouter_key
# or
ANTHROPIC_API_KEY=your_anthropic_key
```

**Security Note:** Never commit `.env` to version control. Add it to `.gitignore`.

## Step 6: Test the Connection

Run a simple test:

```python
from history.storage import AuctionHistoryStorage

# Test connection
try:
    storage = AuctionHistoryStorage()
    print("✓ Supabase connection successful")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

## Step 7: Using the Agent

Now you can use the agent with history tracking:

```python
from hybrid_strategy_selector import HybridStrategySelector
from models import AuctionContext

# Initialize with Supabase (reads from environment variables)
selector = HybridStrategySelector()

# Use the agent
context = AuctionContext(
    domain="example.com",
    platform="godaddy",
    estimated_value=1000.0,
    # ... other fields
)

decision = selector.select_strategy(context)

# After auction ends, record the outcome
selector.record_outcome(
    auction_context=context,
    decision=decision,
    result="won",  # or "lost"
    final_price=850.0
)
```

## Troubleshooting

### "Supabase URL and key required"
- Make sure `SUPABASE_URL` and `SUPABASE_KEY` are set in your `.env` file
- Make sure you're using the **Service Role Key**, not the anon key

### "Could not verify Supabase tables"
- Run the SQL script in Supabase SQL Editor
- Check Table Editor to confirm tables exist
- Verify your service role key has correct permissions

### "Error recording outcome to Supabase"
- Check that the `auction_id` is unique
- Verify data types match the table schema
- Check Supabase logs in the dashboard for detailed errors

## Optional: Direct SQL Access

If you need to query the database directly:

```python
from supabase import create_client
import os

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
client = create_client(url, key)

# Query all auctions
result = client.table('auction_outcomes').select('*').execute()
print(result.data)
```

## Migration from MySQL

If you were previously using MySQL:

1. Export your MySQL data using `mysqldump` or a SQL export tool
2. Convert MySQL syntax to PostgreSQL:
   - `AUTO_INCREMENT` → `SERIAL`
   - `ON DUPLICATE KEY UPDATE` → `ON CONFLICT ... DO UPDATE`
   - `DATETIME` → `TIMESTAMPTZ`
3. Import into Supabase via SQL Editor or using a migration tool
4. Update your code to remove `mysql_config` and use environment variables

## Next Steps

- Set up automated backups in Supabase dashboard
- Monitor database usage and performance
- Consider setting up Row Level Security policies for production use
- Use Supabase Realtime features for live auction monitoring (optional)

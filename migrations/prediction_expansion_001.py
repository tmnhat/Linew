"""
Database migration script for prediction system expansion.
Run this script to create new tables and update existing ones.
"""
import asyncio
import logging
from sqlalchemy import text

from app.core.database import async_engine as engine, async_session_maker

logger = logging.getLogger(__name__)


async def run_migration():
    """Run database migration."""
    
    async with engine.begin() as conn:
        # 1. Create tracked_symbols table
        logger.info("Creating tracked_symbols table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tracked_symbols (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                symbol VARCHAR(30) NOT NULL,
                name VARCHAR(255) NOT NULL,
                market VARCHAR(10) NOT NULL,
                exchange VARCHAR(20),
                currency VARCHAR(5) DEFAULT 'USD',
                is_default BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                popularity INTEGER DEFAULT 0,
                has_prediction BOOLEAN DEFAULT FALSE,
                last_price DOUBLE PRECISION,
                last_updated TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(symbol, market)
            )
        """))
        
        # Create indexes
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tracked_symbols_market_active 
            ON tracked_symbols (market, is_active)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tracked_symbols_popularity 
            ON tracked_symbols (popularity DESC)
        """))
        
        # 2. Create symbol_search_cache table
        logger.info("Creating symbol_search_cache table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS symbol_search_cache (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                symbol VARCHAR(30) NOT NULL,
                name VARCHAR(255) NOT NULL,
                market VARCHAR(10) NOT NULL,
                exchange VARCHAR(20),
                currency VARCHAR(5) DEFAULT 'USD',
                search_text VARCHAR(500),
                UNIQUE(symbol, market)
            )
        """))
        
        # 3. Add columns to market_research table
        logger.info("Adding columns to market_research...")
        
        # Add why_moving column
        try:
            await conn.execute(text("""
                ALTER TABLE market_research 
                ADD COLUMN IF NOT EXISTS why_moving JSONB DEFAULT '[]'
            """))
        except Exception as e:
            logger.warning(f"why_moving column may already exist: {e}")
        
        # Add risks column
        try:
            await conn.execute(text("""
                ALTER TABLE market_research 
                ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT '[]'
            """))
        except Exception as e:
            logger.warning(f"risks column may already exist: {e}")
        
        # Add opportunities column
        try:
            await conn.execute(text("""
                ALTER TABLE market_research 
                ADD COLUMN IF NOT EXISTS opportunities JSONB DEFAULT '[]'
            """))
        except Exception as e:
            logger.warning(f"opportunities column may already exist: {e}")
        
        # 4. Add columns to prediction_final table
        logger.info("Adding columns to prediction_final...")
        
        try:
            await conn.execute(text("""
                ALTER TABLE prediction_final 
                ADD COLUMN IF NOT EXISTS market VARCHAR(10)
            """))
        except Exception as e:
            logger.warning(f"market column may already exist: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE prediction_final 
                ADD COLUMN IF NOT EXISTS currency VARCHAR(5) DEFAULT 'USD'
            """))
        except Exception as e:
            logger.warning(f"currency column may already exist: {e}")
        
        # 5. Expand symbol column in prediction_final (for long VN symbols)
        try:
            await conn.execute(text("""
                ALTER TABLE prediction_final 
                ALTER COLUMN symbol TYPE VARCHAR(30)
            """))
        except Exception as e:
            logger.warning(f"symbol column expansion: {e}")
        
        # 6. Expand symbol column in market_research
        try:
            await conn.execute(text("""
                ALTER TABLE market_research 
                ALTER COLUMN symbol TYPE VARCHAR(30)
            """))
        except Exception as e:
            logger.warning(f"symbol column expansion in market_research: {e}")
        
        # 7. Expand symbol column in technical_indicators
        try:
            await conn.execute(text("""
                ALTER TABLE technical_indicators 
                ALTER COLUMN symbol TYPE VARCHAR(30)
            """))
        except Exception as e:
            logger.warning(f"symbol column expansion in technical_indicators: {e}")
        
        logger.info("Migration completed successfully!")


async def seed_default_symbols():
    """Seed default symbols to database."""
    
    from app.prediction.symbol_search import seed_all_symbols
    
    async with async_session_maker() as session:
        count = await seed_all_symbols(session)
        logger.info(f"Seeded {count} default symbols")
        return count


async def main():
    """Main migration runner."""
    logging.basicConfig(level=logging.INFO)
    
    logger.info("Starting database migration...")
    
    try:
        await run_migration()
        logger.info("Migration completed!")
        
        # Optionally seed data
        logger.info("Seeding default symbols...")
        await seed_default_symbols()
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

"""
Migration: Add unique constraint on title_hash for active articles.

This constraint prevents duplicate articles with the same title_hash
from being created when articles are in active processing states.

The constraint is a partial unique index that only applies to articles
that are not in terminal states (SKIPPED, EXPIRED, REJECTED, FAILED).

Run with: python migrations/add_title_hash_constraint.py
"""
import asyncio
import asyncpg
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run_migration():
    """Run the migration to add unique constraint on title_hash."""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "postgresql://linew:changeme@localhost:5432/linew")
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://").replace("@postgres:", "@localhost:")
    
    print(f"Connecting to: {database_url.split('@')[-1]}")
    
    conn = await asyncpg.connect(database_url)
    
    try:
        # Start transaction
        async with conn.transaction():
            # Check if index already exists
            index_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'uq_articles_title_hash_active'
                )
            """)
            
            if index_exists:
                print("Constraint 'uq_articles_title_hash_active' already exists. Skipping.")
                return
            
            # Step 1: Identify duplicate title_hashes that are in active states
            print("\n=== Step 1: Identifying duplicate title_hashes ===")
            
            duplicates = await conn.fetch("""
                SELECT title_hash, COUNT(*) as count, ARRAY_AGG(id) as ids
                FROM articles
                WHERE state NOT IN ('SKIPPED', 'EXPIRED', 'REJECTED', 'FAILED')
                AND title_hash IS NOT NULL
                GROUP BY title_hash
                HAVING COUNT(*) > 1
            """)
            
            if duplicates:
                print(f"Found {len(duplicates)} duplicate title_hash groups:")
                for dup in duplicates:
                    print(f"  - {dup['title_hash'][:16]}...: {dup['count']} articles")
                    # Keep the oldest, mark others as SKIPPED
                    ids = list(dup['ids'])
                    keep_id = ids[0]
                    skip_ids = ids[1:]
                    
                    print(f"    Keeping: {keep_id}")
                    print(f"    Skipping: {skip_ids}")
                    
                    # Mark duplicates as SKIPPED
                    await conn.execute("""
                        UPDATE articles 
                        SET state = 'SKIPPED', 
                            fail_reason = 'Duplicate: auto-resolved by migration',
                            updated_at = NOW()
                        WHERE id = ANY($1::uuid[])
                    """, skip_ids)
                
                print(f"\nResolved {sum(d['count'] - 1 for d in duplicates)} duplicate articles")
            else:
                print("No duplicate title_hashes found.")
            
            # Step 2: Create partial unique index
            print("\n=== Step 2: Creating unique constraint ===")
            
            await conn.execute("""
                CREATE UNIQUE INDEX CONCURRENTLY uq_articles_title_hash_active
                ON articles (title_hash)
                WHERE state NOT IN ('SKIPPED', 'EXPIRED', 'REJECTED', 'FAILED')
            """)
            
            print("Created unique index 'uq_articles_title_hash_active'")
            
            # Verify
            index_info = await conn.fetchrow("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE indexname = 'uq_articles_title_hash_active'
            """)
            
            if index_info:
                print(f"\nIndex created successfully:")
                print(f"  Name: {index_info['indexname']}")
                print(f"  Definition: {index_info['indexdef'][:100]}...")
            
            print("\n=== Migration completed successfully ===")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        await conn.close()


def rollback_migration():
    """Rollback the migration by dropping the constraint."""
    
    async def _rollback():
        database_url = os.getenv("DATABASE_URL", "postgresql://linew:changeme@localhost:5432/linew")
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://").replace("@postgres:", "@localhost:")
        
        print(f"Rolling back migration...")
        
        conn = await asyncpg.connect(database_url)
        
        try:
            await conn.execute("""
                DROP INDEX IF EXISTS uq_articles_title_hash_active
            """)
            print("Dropped index 'uq_articles_title_hash_active'")
        finally:
            await conn.close()
    
    asyncio.run(_rollback())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("Running rollback...")
        rollback_migration()
    else:
        print("Running migration: Add title_hash unique constraint")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("-" * 50)
        asyncio.run(run_migration())

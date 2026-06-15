#!/usr/bin/env python3
"""
Script to clean up duplicate Facebook posts and distribution logs.

Usage:
    python scripts/cleanup_facebook.py --dry-run
    python scripts/cleanup_facebook.py --stats
    python scripts/cleanup_facebook.py --no-dry-run
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import argparse
from sqlalchemy import select, and_, delete, func
from collections import defaultdict

from app.core.database import get_db_context
from app.models.distribution import DistributionLog


async def cleanup_duplicate_logs(channel: str = 'facebook', dry_run: bool = True):
    """Clean up duplicate distribution logs."""
    async with get_db_context() as session:
        # Find all success entries for the channel
        result = await session.execute(
            select(
                DistributionLog.id,
                DistributionLog.article_id,
                DistributionLog.channel,
                DistributionLog.created_at,
                DistributionLog.external_url
            )
            .where(
                and_(
                    DistributionLog.channel == channel,
                    DistributionLog.status == "success"
                )
            )
            .order_by(DistributionLog.created_at)
        )
        rows = result.fetchall()
        
        # Group by (article_id, channel)
        grouped = defaultdict(list)
        for row in rows:
            key = (str(row.article_id), row.channel)
            grouped[key].append({
                'id': str(row.id),
                'url': row.external_url,
                'created_at': row.created_at
            })
        
        # Find duplicates
        duplicates_to_delete = []
        articles_with_duplicates = 0
        
        for (article_id, ch), entries in grouped.items():
            if len(entries) > 1:
                articles_with_duplicates += 1
                # Keep the first one (oldest), delete the rest
                for entry in entries[1:]:
                    duplicates_to_delete.append(entry['id'])
                    if dry_run:
                        print(f"  [DRY RUN] Would delete duplicate:")
                        print(f"    Article ID: {article_id}")
                        print(f"    Created: {entry['created_at']}")
                        print(f"    URL: {entry['url']}")
        
        if dry_run:
            print(f"\n[DRY RUN MODE]")
            print(f"Channel: {channel}")
            print(f"Total success entries: {len(rows)}")
            print(f"Unique articles: {len([k for k, v in grouped.items() if len(v) == 1])}")
            print(f"Articles with duplicates: {articles_with_duplicates}")
            print(f"Duplicates to delete: {len(duplicates_to_delete)}")
        else:
            if duplicates_to_delete:
                await session.execute(
                    delete(DistributionLog)
                    .where(DistributionLog.id.in_(duplicates_to_delete))
                )
                await session.commit()
                print(f"\nDeleted {len(duplicates_to_delete)} duplicate entries for channel '{channel}'")
            else:
                print(f"\nNo duplicate entries found for channel '{channel}'")
        
        return {
            'total': len(rows),
            'unique': len([k for k, v in grouped.items() if len(v) == 1]),
            'with_duplicates': articles_with_duplicates,
            'duplicates_deleted': len(duplicates_to_delete)
        }


async def show_facebook_stats():
    """Show Facebook distribution statistics."""
    async with get_db_context() as session:
        result = await session.execute(
            select(
                func.count(DistributionLog.id).label('count'),
                DistributionLog.status
            )
            .where(DistributionLog.channel == 'facebook')
            .group_by(DistributionLog.status)
        )
        rows = result.fetchall()
        
        print("\nFacebook Distribution Stats:")
        print("-" * 40)
        total = 0
        for count, status in rows:
            print(f"  {status}: {count}")
            total += count
        
        print(f"  Total: {total}")
        
        # Show recent posts
        recent_result = await session.execute(
            select(DistributionLog)
            .where(
                and_(
                    DistributionLog.channel == 'facebook',
                    DistributionLog.status == 'success'
                )
            )
            .order_by(DistributionLog.created_at.desc())
            .limit(10)
        )
        recent = recent_result.scalars().all()
        
        print(f"\nRecent Facebook Posts (last 10):")
        print("-" * 40)
        for log in recent:
            print(f"  {log.created_at.strftime('%Y-%m-%d %H:%M')} | {log.external_url[:60] if log.external_url else 'N/A'}...")


async def main():
    parser = argparse.ArgumentParser(description='Clean up duplicate Facebook posts')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted (default)')
    parser.add_argument('--channel', default='facebook', help='Channel to clean')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--no-dry-run', action='store_true', help='Actually delete duplicates')
    
    args = parser.parse_args()
    
    if args.stats:
        await show_facebook_stats()
    else:
        dry_run = not args.no_dry_run
        await cleanup_duplicate_logs(channel=args.channel, dry_run=dry_run)


if __name__ == '__main__':
    asyncio.run(main())

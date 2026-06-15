"""
CLI commands for Linew.
"""
import click
import asyncio
from sqlalchemy import select, and_, delete
from app.core.database import async_session
from app.models.distribution import DistributionLog


@click.group()
def cli():
    """Linew CLI commands."""
    pass


@cli.command()
@click.option('--channel', default='facebook', help='Channel to clean (default: facebook)')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without actually deleting')
def cleanup_duplicates(channel: str, dry_run: bool):
    """
    Clean up duplicate distribution logs.
    
    Keeps only the first successful post per article per channel.
    """
    async def _cleanup():
        async with async_session() as session:
            # Find all duplicate success entries
            # Group by article_id and channel, keep the first one (lowest created_at)
            result = await session.execute(
                select(
                    DistributionLog.article_id,
                    DistributionLog.channel,
                    DistributionLog.id,
                    DistributionLog.created_at
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
            
            # Group by (article_id, channel) and find duplicates
            from collections import defaultdict
            grouped = defaultdict(list)
            for article_id, ch, log_id, created_at in rows:
                grouped[(str(article_id), ch)].append((str(log_id), created_at))
            
            # Find duplicates to delete
            duplicates_to_delete = []
            for (article_id, ch), entries in grouped.items():
                if len(entries) > 1:
                    # Keep the first one (sorted by created_at), delete the rest
                    entries_to_delete = entries[1:]  # Skip first, delete the rest
                    for log_id, _ in entries_to_delete:
                        duplicates_to_delete.append(log_id)
            
            if dry_run:
                click.echo(f"\n[DRY RUN] Found {len(duplicates_to_delete)} duplicate entries to delete:")
                for log_id in duplicates_to_delete[:10]:
                    click.echo(f"  - {log_id}")
                if len(duplicates_to_delete) > 10:
                    click.echo(f"  ... and {len(duplicates_to_delete) - 10} more")
            else:
                if duplicates_to_delete:
                    await session.execute(
                        delete(DistributionLog)
                        .where(DistributionLog.id.in_(duplicates_to_delete))
                    )
                    await session.commit()
                    click.echo(f"\nDeleted {len(duplicates_to_delete)} duplicate entries for channel '{channel}'")
                else:
                    click.echo(f"\nNo duplicate entries found for channel '{channel}'")
            
            # Summary
            click.echo(f"\nSummary:")
            click.echo(f"  Channel: {channel}")
            click.echo(f"  Total success entries: {len(rows)}")
            click.echo(f"  Unique articles: {len(grouped)}")
            click.echo(f"  Duplicates: {len(duplicates_to_delete)}")

    asyncio.run(_cleanup())


@cli.command()
def stats():
    """Show distribution statistics."""
    async def _stats():
        async with async_session() as session:
            result = await session.execute(
                select(
                    DistributionLog.channel,
                    DistributionLog.status,
                    sqlalchemy.func.count(DistributionLog.id)
                )
                .group_by(DistributionLog.channel, DistributionLog.status)
            )
            rows = result.fetchall()
            
            click.echo("\nDistribution Statistics:")
            click.echo("-" * 50)
            
            stats = {}
            for channel, status, count in rows:
                if channel not in stats:
                    stats[channel] = {'success': 0, 'failed': 0, 'total': 0}
                stats[channel][status] = count
                stats[channel]['total'] += count
            
            for channel, data in stats.items():
                click.echo(f"\n{channel.upper()}:")
                click.echo(f"  Total: {data['total']}")
                click.echo(f"  Success: {data['success']}")
                click.echo(f"  Failed: {data['failed']}")

    import sqlalchemy
    asyncio.run(_stats())


if __name__ == '__main__':
    cli()

"""
Article state constants for deduplication.

This module defines which article states should be checked
when detecting duplicates. This prevents race conditions
where multiple workers process similar articles simultaneously.
"""
from app.models.article import ArticleState


# States that indicate an article is being actively processed
# Articles in these states should be checked for deduplication
IN_PROGRESS_STATES = {
    ArticleState.SIGNAL_COLLECTED.value,
    ArticleState.CATEGORIZED.value,
    ArticleState.TRENDING.value,
    ArticleState.RESEARCHED.value,
    ArticleState.WRITTEN.value,
    ArticleState.GOVERNED.value,
    ArticleState.APPROVED.value,
    ArticleState.PUBLISHED.value,
}


# States that indicate an article is "done" or "dead"
# Articles in these states should NOT be considered for dedup
TERMINAL_STATES = {
    ArticleState.SKIPPED.value,
    ArticleState.EXPIRED.value,
    ArticleState.REJECTED.value,
    ArticleState.FAILED.value,
}


# States to check when looking for duplicates
# This is the union of active states for comprehensive dedup
# FIX: Added REJECTED and FAILED to prevent reprocessing of duplicates
DEDUP_CHECK_STATES = IN_PROGRESS_STATES | TERMINAL_STATES


# States that indicate an article was successfully published
# These are the most critical for dedup checking
PUBLISHED_LIKE_STATES = {
    ArticleState.APPROVED.value,
    ArticleState.PUBLISHED.value,
}

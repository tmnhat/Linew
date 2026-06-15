#!/usr/bin/env python3
"""
Stop all Linew Pipelines Script

Usage:
    python scripts/stop_pipelines.py

This script stops all running pipelines by:
1. Setting Redis stop signal (hard stop)
2. Revoking running Celery tasks
3. Setting pipeline state to STOPPED
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pipeline.hard_stop import trigger_user_stop
from app.pipeline.control import stop_pipeline, get_pipeline_state
import asyncio


async def main():
    print("=" * 50)
    print("LINEW PIPELINE STOP SCRIPT")
    print("=" * 50)
    
    # Get current state
    try:
        state = await get_pipeline_state()
        print(f"\nCurrent pipeline state: {state.value}")
    except Exception as e:
        print(f"\nCould not get pipeline state: {e}")
        state = None
    
    # Trigger hard stop (this is immediate and affects all workers)
    print("\nTriggering hard stop...")
    stop_result = trigger_user_stop(reason="User requested stop - pausing all pipelines")
    if stop_result.get("success"):
        print(f"  ✓ Hard stop signal set successfully")
    else:
        print(f"  ✗ Hard stop failed: {stop_result.get('error')}")
    
    # Stop pipeline control
    print("\nStopping pipeline control...")
    try:
        result = await stop_pipeline(reason="User requested stop - pausing all pipelines")
        print(f"  ✓ Pipeline stopped: {result.get('message')}")
    except Exception as e:
        print(f"  ✗ Stop failed: {e}")
    
    # Final state
    print("\n" + "-" * 50)
    try:
        final_state = await get_pipeline_state()
        print(f"Final pipeline state: {final_state.value}")
    except Exception as e:
        print(f"Could not verify final state: {e}")
    
    print("\n" + "=" * 50)
    print("All pipelines have been paused!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

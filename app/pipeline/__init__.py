"""
Pipeline module - categorize, write, govern, publish.

Updated với Hard Stop mechanism:
- Pipeline chỉ dừng khi user bấm Stop HOẶC Redis/DB down
- KHÔNG BAO GIỜ dừng vì AI fail
"""
from app.pipeline.control import (
    PipelineState,
    PipelineMode,
    start_pipeline,
    stop_pipeline,
    pause_pipeline,
    resume_pipeline,
    get_pipeline_state,
    get_pipeline_info,
    is_pipeline_running,
    acquire_pipeline_lock,
    release_pipeline_lock,
)

# Export hard stop functions
from app.pipeline.hard_stop import (
    should_stop_pipeline,
    trigger_user_stop,
    clear_user_stop,
    get_stop_status,
)

__all__ = [
    # Control
    "PipelineState",
    "PipelineMode",
    "start_pipeline",
    "stop_pipeline",
    "pause_pipeline",
    "resume_pipeline",
    "get_pipeline_state",
    "get_pipeline_info",
    "is_pipeline_running",
    "acquire_pipeline_lock",
    "release_pipeline_lock",
    # Hard stop
    "should_stop_pipeline",
    "trigger_user_stop",
    "clear_user_stop",
    "get_stop_status",
]

"""Alembic migration script: Prediction System - 3 new tables.

Creates technical_indicators, market_research, and prediction_final tables.
"""
from datetime import datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create technical_indicators table
    op.create_table(
        'technical_indicators',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('rsi_14', sa.Numeric(10, 4), nullable=True),
        sa.Column('macd_line', sa.Numeric(20, 8), nullable=True),
        sa.Column('macd_signal', sa.Numeric(20, 8), nullable=True),
        sa.Column('macd_histogram', sa.Numeric(20, 8), nullable=True),
        sa.Column('bb_upper', sa.Numeric(20, 8), nullable=True),
        sa.Column('bb_middle', sa.Numeric(20, 8), nullable=True),
        sa.Column('bb_lower', sa.Numeric(20, 8), nullable=True),
        sa.Column('sma_20', sa.Numeric(20, 8), nullable=True),
        sa.Column('sma_50', sa.Numeric(20, 8), nullable=True),
        sa.Column('sma_200', sa.Numeric(20, 8), nullable=True),
        sa.Column('ema_12', sa.Numeric(20, 8), nullable=True),
        sa.Column('ema_26', sa.Numeric(20, 8), nullable=True),
        sa.Column('atr_14', sa.Numeric(20, 8), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('volume_sma_20', sa.Numeric(20, 8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('symbol', 'date', name='uq_technical_indicators_symbol_date'),
        sa.Index('idx_technical_indicators_symbol_date', 'symbol', 'date'),
    )

    # 2. Create market_research table
    op.create_table(
        'market_research',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('analysis_date', sa.Date(), nullable=False),
        sa.Column('sentiment', sa.String(20), nullable=True),
        sa.Column('sentiment_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('analysis_text', sa.Text(), nullable=True),
        sa.Column('analysis_vi', sa.Text(), nullable=True),
        sa.Column('key_factors', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('risk_factors', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('support_levels', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('resistance_levels', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('fear_greed_index', sa.Integer(), nullable=True),
        sa.Column('fear_greed_value', sa.String(20), nullable=True),
        sa.Column('model_used', sa.String(50), nullable=False, server_default='minimax-m2.5'),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Index('idx_market_research_symbol_date', 'symbol', 'analysis_date'),
        sa.Index('idx_market_research_generated', 'generated_at'),
    )

    # 3. Create prediction_final table
    op.create_table(
        'prediction_final',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('prediction_date', sa.Date(), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False),
        sa.Column('current_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('predicted_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('predicted_low', sa.Numeric(20, 8), nullable=True),
        sa.Column('predicted_high', sa.Numeric(20, 8), nullable=True),
        sa.Column('change_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('timesfm_prediction', sa.Numeric(20, 8), nullable=True),
        sa.Column('chronos_prediction', sa.Numeric(20, 8), nullable=True),
        sa.Column('ensemble_weight_timesfm', sa.Numeric(5, 4), nullable=True),
        sa.Column('ensemble_weight_chronos', sa.Numeric(5, 4), nullable=True),
        sa.Column('ai_sentiment', sa.String(20), nullable=True),
        sa.Column('ai_sentiment_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('ai_adjustment_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('technical_signals', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('model_used', sa.String(50), nullable=False),
        sa.Column('actual_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('accuracy_error_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('symbol', 'prediction_date', 'horizon_days', name='uq_prediction_final_symbol_date_horizon'),
        sa.Index('idx_prediction_final_symbol_date', 'symbol', 'prediction_date'),
        sa.Index('idx_prediction_final_horizon', 'horizon_days'),
        sa.Index('idx_prediction_final_generated', 'generated_at'),
    )


def downgrade() -> None:
    op.drop_table('prediction_final')
    op.drop_table('market_research')
    op.drop_table('technical_indicators')

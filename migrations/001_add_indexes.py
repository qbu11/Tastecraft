"""
Database migration script for adding indexes and constraints.

根据 CEO Review Section 7.3 的建议添加必要的索引。
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '001_add_indexes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加索引和约束。"""

    # ============================================================================
    # Contents 表索引
    # ============================================================================

    # 按状态查询（常用于列表过滤）
    op.create_index(
        'idx_contents_status',
        'contents',
        ['status'],
    )

    # 按创建时间排序（常用于列表排序）
    op.create_index(
        'idx_contents_created_at',
        'contents',
        ['created_at'],
    )

    # 按用户 ID 查询（权限检查）
    op.create_index(
        'idx_contents_user_id',
        'contents',
        ['user_id'],
    )

    # 组合索引：用户 + 状态（常用查询模式）
    op.create_index(
        'idx_contents_user_status',
        'contents',
        ['user_id', 'status'],
    )

    # ============================================================================
    # Publish Logs 表索引
    # ============================================================================

    # 按内容 ID 查询（查看发布记录）
    op.create_index(
        'idx_publish_logs_content_id',
        'publish_logs',
        ['content_id'],
    )

    # 按平台查询（平台统计）
    op.create_index(
        'idx_publish_logs_platform',
        'publish_logs',
        ['platform'],
    )

    # 按状态查询（失败重试）
    op.create_index(
        'idx_publish_logs_status',
        'publish_logs',
        ['status'],
    )

    # 按发布时间排序（时间线）
    op.create_index(
        'idx_publish_logs_published_at',
        'publish_logs',
        ['published_at'],
    )

    # 组合索引：内容 + 平台（查询特定内容在特定平台的发布状态）
    op.create_index(
        'idx_publish_logs_content_platform',
        'publish_logs',
        ['content_id', 'platform'],
    )

    # ============================================================================
    # Analytics 表索引
    # ============================================================================

    # 按发布记录 ID 查询（关联查询）
    op.create_index(
        'idx_analytics_publish_log_id',
        'analytics',
        ['publish_log_id'],
    )

    # 按采集时间排序（趋势分析）
    op.create_index(
        'idx_analytics_collected_at',
        'analytics',
        ['collected_at'],
    )

    # 组合索引：发布记录 + 采集时间（时间序列查询）
    op.create_index(
        'idx_analytics_log_time',
        'analytics',
        ['publish_log_id', 'collected_at'],
    )

    # ============================================================================
    # Hotspots 表索引
    # ============================================================================

    # 按来源平台查询
    op.create_index(
        'idx_hotspots_source',
        'hotspots',
        ['source'],
    )

    # 按评分排序（热点排名）
    op.create_index(
        'idx_hotspots_score',
        'hotspots',
        ['score'],
    )

    # 按采集时间排序（时效性）
    op.create_index(
        'idx_hotspots_collected_at',
        'hotspots',
        ['collected_at'],
    )

    # 按过期时间查询（清理过期数据）
    op.create_index(
        'idx_hotspots_expires_at',
        'hotspots',
        ['expires_at'],
    )


def downgrade() -> None:
    """删除索引。"""

    # Contents 表
    op.drop_index('idx_contents_user_status', table_name='contents')
    op.drop_index('idx_contents_user_id', table_name='contents')
    op.drop_index('idx_contents_created_at', table_name='contents')
    op.drop_index('idx_contents_status', table_name='contents')

    # Publish Logs 表
    op.drop_index('idx_publish_logs_content_platform', table_name='publish_logs')
    op.drop_index('idx_publish_logs_published_at', table_name='publish_logs')
    op.drop_index('idx_publish_logs_status', table_name='publish_logs')
    op.drop_index('idx_publish_logs_platform', table_name='publish_logs')
    op.drop_index('idx_publish_logs_content_id', table_name='publish_logs')

    # Analytics 表
    op.drop_index('idx_analytics_log_time', table_name='analytics')
    op.drop_index('idx_analytics_collected_at', table_name='analytics')
    op.drop_index('idx_analytics_publish_log_id', table_name='analytics')

    # Hotspots 表
    op.drop_index('idx_hotspots_expires_at', table_name='hotspots')
    op.drop_index('idx_hotspots_collected_at', table_name='hotspots')
    op.drop_index('idx_hotspots_score', table_name='hotspots')
    op.drop_index('idx_hotspots_source', table_name='hotspots')

"""Read-only diagnostics. Do not retrieve SQL text, credentials, or customer records."""
from time import perf_counter
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError
from database.db import engine


def local_database_health():
    started = perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1')).scalar_one()
            ping_ms = round((perf_counter()-started)*1000, 3)
            began = perf_counter()
            count = connection.execute(text('SELECT COUNT(*) FROM analysis_runs')).scalar_one()
            connection.execute(text('SELECT id, created_at FROM analysis_runs ORDER BY created_at DESC LIMIT 20')).all()
            query_ms = round((perf_counter()-began)*1000, 3)
            plan = []
            if engine.dialect.name == 'sqlite':
                plan = [list(row) for row in connection.execute(text('EXPLAIN QUERY PLAN SELECT id, created_at FROM analysis_runs ORDER BY created_at DESC LIMIT 20'))]
            return {'connected': True, 'engine': engine.dialect.name, 'ping_ms': ping_ms, 'dashboard_query_ms': query_ms, 'stored_runs': count,
                    'query_plan': plan, 'note': 'Analytics storage timing only. This does not measure the banking application database.'}
    except SQLAlchemyError:
        return {'connected': False, 'error': 'Analytics database query failed. Check connection and migration status.'}


def postgres_evidence(url):
    if not url:
        return {'status': 'not_configured', 'next_step': 'Set MONITORED_DATABASE_URL to a PostgreSQL read-only monitoring connection.'}
    monitored = None
    try:
        if url.startswith('postgresql://'):
            url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
        monitored = create_engine(url, connect_args={'connect_timeout': 5}, pool_pre_ping=True)
        if monitored.dialect.name != 'postgresql':
            return {'status': 'unsupported_engine', 'supported': ['postgresql']}
        with monitored.connect() as connection:
            connection.execute(text('SET TRANSACTION READ ONLY'))
            connection.execute(text("SET LOCAL statement_timeout = '5000ms'"))
            activity = connection.execute(text("""
                SELECT state, wait_event_type, wait_event, COUNT(*) AS sessions,
                       MAX(EXTRACT(EPOCH FROM (clock_timestamp()-query_start))*1000) AS max_query_age_ms
                FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()
                GROUP BY state, wait_event_type, wait_event
            """)).mappings().all()
            blockers = connection.execute(text("""
                SELECT COUNT(*) FROM pg_stat_activity
                WHERE datname=current_database() AND cardinality(pg_blocking_pids(pid))>0
            """)).scalar_one()
            stats = connection.execute(text("""
                SELECT numbackends, xact_commit, xact_rollback, blks_read, blks_hit,
                       deadlocks, temp_files, temp_bytes, blk_read_time, blk_write_time, stats_reset
                FROM pg_stat_database WHERE datname=current_database()
            """)).mappings().one()
            return {'status': 'observed', 'source': 'postgresql_system_views', 'activity': [dict(row) for row in activity],
                    'blocked_sessions': blockers, 'cumulative_statistics': dict(stats),
                    'limitations': 'Cumulative counters require two time-separated snapshots for rates. Restricted roles may not see all sessions; zero I/O timing may mean track_io_timing is disabled.'}
    except (SQLAlchemyError, ImportError):
        return {'status': 'unavailable', 'error': 'Read-only PostgreSQL diagnostics failed. Check driver, connectivity, monitoring role, and session visibility.'}
    finally:
        if monitored:
            monitored.dispose()

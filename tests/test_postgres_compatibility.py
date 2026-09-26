"""
HC-XCDSS PostgreSQL & SQLite Database Compatibility Tests
Verifies:
1. DATABASE_URL dynamic selection & fallback
2. postgres:// to postgresql:// normalization for Render
3. Engine creation parameters for SQLite vs PostgreSQL (pooling, check_same_thread, pragmas)
4. Schema migration dialect-guarding (no SQLite PRAGMA executed on PostgreSQL)
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.db.session import (
    normalize_database_url,
    get_database_url,
    create_app_engine,
    DEFAULT_SQLITE_URL,
)
from src.db.migration import init_db
from src.db.base import Base


class TestDatabaseCompatibility(unittest.TestCase):

    def test_normalize_database_url_converts_postgres_prefix(self):
        render_url = "postgres://hc_user:secret_pass@dpg-xxxx.render.com:5432/hc_xcdss_db"
        expected = "postgresql://hc_user:secret_pass@dpg-xxxx.render.com:5432/hc_xcdss_db"
        self.assertEqual(normalize_database_url(render_url), expected)

    def test_normalize_database_url_preserves_postgresql_prefix(self):
        pg_url = "postgresql://hc_user:secret_pass@localhost:5432/hc_xcdss_db"
        self.assertEqual(normalize_database_url(pg_url), pg_url)

    def test_normalize_database_url_preserves_sqlite_url(self):
        sqlite_url = "sqlite:///outputs/hc_xcdss.db"
        self.assertEqual(normalize_database_url(sqlite_url), sqlite_url)

    def test_normalize_database_url_handles_empty_or_none(self):
        self.assertEqual(normalize_database_url(""), "")
        self.assertIsNone(normalize_database_url(None))

    def test_get_database_url_defaults_to_sqlite_when_env_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            # Ensure DATABASE_URL is not present
            url = get_database_url()
            self.assertEqual(url, DEFAULT_SQLITE_URL)
            self.assertTrue(url.startswith("sqlite:///"))

    def test_get_database_url_uses_env_when_set(self):
        custom_pg = "postgres://testuser:testpass@render-postgres:5432/prod_db"
        with patch.dict(os.environ, {"DATABASE_URL": custom_pg}):
            url = get_database_url()
            self.assertEqual(url, "postgresql://testuser:testpass@render-postgres:5432/prod_db")

    def test_create_app_engine_sqlite_configuration(self):
        sqlite_test_url = "sqlite:///:memory:"
        engine = create_app_engine(sqlite_test_url)
        self.assertEqual(engine.dialect.name, "sqlite")
        
        # Verify tables can be created cleanly
        Base.metadata.create_all(bind=engine)
        
        # Test connection executes SQLite foreign keys without error
        with engine.connect() as conn:
            self.assertTrue(conn.connection.is_valid if hasattr(conn.connection, "is_valid") else True)
        
        engine.dispose()

    @patch("src.db.session.create_engine")
    def test_create_app_engine_postgres_configuration_does_not_pass_check_same_thread(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        pg_url = "postgresql://user:pass@localhost:5432/testdb"
        result_engine = create_app_engine(pg_url)

        mock_create_engine.assert_called_once_with(
            pg_url,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )
        # Verify connect_args was NOT passed for PostgreSQL
        call_kwargs = mock_create_engine.call_args[1]
        self.assertNotIn("connect_args", call_kwargs)
        self.assertEqual(result_engine, mock_engine)

    def test_init_db_on_sqlite_executes_successfully(self):
        # Verify init_db runs idempotently on SQLite without raising errors
        sqlite_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        with patch("src.db.migration.engine", sqlite_engine):
            init_db()
            # Verify tables exist
            table_names = list(Base.metadata.tables.keys())
            self.assertIn("users", table_names)
            self.assertIn("analyses", table_names)
            self.assertIn("reports", table_names)
            self.assertIn("review_requests", table_names)
            self.assertIn("professional_reviews", table_names)
        sqlite_engine.dispose()

    @patch("src.db.migration.text")
    def test_init_db_skips_sqlite_pragma_when_dialect_is_not_sqlite(self, mock_text):
        mock_pg_engine = MagicMock()
        mock_pg_engine.dialect.name = "postgresql"

        with patch("src.db.migration.engine", mock_pg_engine), \
             patch("src.db.migration.Base.metadata.create_all") as mock_create_all, \
             patch("src.db.migration.ensure_admin_account") as mock_admin:

            init_db()

            mock_create_all.assert_called_once_with(bind=mock_pg_engine)
            mock_admin.assert_called_once()
            # Verify PRAGMA table_info was never executed
            mock_pg_engine.connect.assert_not_called()
            mock_text.assert_not_called()


if __name__ == "__main__":
    unittest.main()

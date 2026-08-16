"""Integration contract for the PHASE-0.3 PostgreSQL schema migration."""

import subprocess
import time
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = PROJECT_ROOT / "db" / "migrations"
UP_MIGRATION = MIGRATIONS_DIR / "V001__init_schema.sql"
DOWN_MIGRATION = MIGRATIONS_DIR / "V001__init_schema.down.sql"
EXPECTED_TABLES = {
    "users", "brands", "campaigns", "content_assets", "scheduled_posts",
    "analytics_metrics", "social_auth", "provider_keys", "job_queue",
    "agent_logs", "audit_trail", "backups", "policy_rules",
}


class Phase03DatabaseSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container_name = f"canon-os-v001-{uuid.uuid4().hex[:12]}"
        cls.run_docker("run", "--detach", "--rm", "--name", cls.container_name,
                       "-e", "POSTGRES_PASSWORD=postgres", "postgres:15-alpine")
        for _ in range(30):
            ready = cls.run_docker("exec", cls.container_name, "pg_isready", "-U", "postgres",
                                   check=False)
            if ready.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError("PostgreSQL test container did not become ready")

    @classmethod
    def tearDownClass(cls):
        cls.run_docker("rm", "--force", cls.container_name, check=False)

    @classmethod
    def run_docker(cls, *args, check=True):
        result = subprocess.run(["docker", *args], check=False, text=True,
                                capture_output=True)
        if check and result.returncode:
            command = " ".join(("docker", *args))
            raise RuntimeError(
                f"Docker command failed ({result.returncode}): {command}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def psql_file(self, migration):
        self.run_docker("cp", str(migration), f"{self.container_name}:/tmp/{migration.name}")
        self.run_docker("exec", self.container_name, "psql", "-v", "ON_ERROR_STOP=1",
                        "-U", "postgres", "-d", "postgres", "-f", f"/tmp/{migration.name}")

    def psql_scalar(self, query):
        result = self.run_docker("exec", self.container_name, "psql", "-At",
                                 "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "postgres",
                                 "-c", query)
        return result.stdout.strip()

    def test_v001_applies_full_schema_and_rolls_back(self):
        self.assertTrue(UP_MIGRATION.is_file())
        self.assertTrue(DOWN_MIGRATION.is_file())

        self.psql_file(UP_MIGRATION)

        tables = set(self.psql_scalar(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
        ).splitlines())
        self.assertSetEqual(tables, EXPECTED_TABLES)
        self.assertEqual(self.psql_scalar("SELECT extname FROM pg_extension WHERE extname = 'pgcrypto';"),
                         "pgcrypto")
        self.assertEqual(self.psql_scalar(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' "
            "AND indexname = 'idx_job_queue_priority';"
        ), "idx_job_queue_priority")
        self.assertEqual(self.psql_scalar(
            "SELECT confdeltype FROM pg_constraint WHERE conname = 'brands_user_id_fkey';"
        ), "c")

        self.psql_file(DOWN_MIGRATION)
        self.assertEqual(self.psql_scalar(
            "SELECT count(*) FROM pg_tables WHERE schemaname = 'public';"
        ), "0")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python
import sys
from pathlib import Path

from alembic.script import ScriptDirectory
from alembic.config import Config


def check_migrations():
    """Check if migrations are in a valid state."""
    # Get the path to alembic.ini
    backend_dir = Path(__file__).parent.parent
    alembic_ini = backend_dir / "alembic.ini"
    if not alembic_ini.exists():
        print("Error: alembic.ini not found")
        sys.exit(1)

    # Create Alembic config
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_dir / "alembic"))

    # Get the script directory
    script = ScriptDirectory.from_config(config)

    # Get all revisions
    revisions = list(script.walk_revisions())

    # Check for duplicate revision IDs
    revision_ids = [rev.revision for rev in revisions]
    if len(revision_ids) != len(set(revision_ids)):
        print("Error: Duplicate revision IDs found")
        sys.exit(1)

    # Check for missing dependencies
    for rev in revisions:
        if rev.down_revision and rev.down_revision not in revision_ids:
            print(f"Error: Missing dependency for revision {rev.revision}")
            sys.exit(1)

    print("Migration check passed!")
    return 0


if __name__ == "__main__":
    sys.exit(check_migrations())

import gc
import sys
import os
import time

# Add the ontology module path to sys.path
source_path = os.path.join(
    os.path.dirname(__file__),
    '..', '..', 'python', 'src', 'base_practice', 'chatbi'
)
sys.path.insert(0, os.path.abspath(source_path))


def safe_unlink(db_path: str):
    """Safely delete a database file, handling Windows file locks."""
    gc.collect()
    for _ in range(3):
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
            return
        except PermissionError:
            time.sleep(0.1)

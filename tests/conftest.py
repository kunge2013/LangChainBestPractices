import sys
import os

# Add the ontology module path to sys.path so tests can import from ontology.*
source_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'python', 'src', 'base_practice', 'chatbi'
)
if source_path not in sys.path:
    sys.path.insert(0, source_path)

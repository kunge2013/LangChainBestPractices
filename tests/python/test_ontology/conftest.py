import sys
import os

# Add the ontology module path to sys.path
source_path = os.path.join(
    os.path.dirname(__file__),
    '..', '..', 'python', 'src', 'base_practice', '16.chatbi'
)
sys.path.insert(0, os.path.abspath(source_path))

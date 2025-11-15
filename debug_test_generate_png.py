"""
Debug script for testing PNG generation when Graphviz is not installed.
"""

from pathlib import Path
from app.services.export import export_as_image
from graphviz.backend import ExecutableNotFound

def debug_test_generate_png_graphviz_not_installed():
    graph_json = {
        "hosts": [
            {"id": "host1", "roles": ["universal_forwarder"], "labels": [], "apps": []},
            {"id": "host2", "roles": ["indexer"], "labels": [], "apps": []},
        ],
        "edges": [
            {
                "src_host": "host1",
                "dst_host": "host2",
                "protocol": "splunktcp",
                "indexes": ["main"],
                "tls": False,
                "weight": 1,
            }
        ],
        "meta": {},
    }

    export_format = "png"
    graph_id = 1

    try:
        export_as_image(graph_json, export_format, graph_id)
    except ExecutableNotFound as e:
        print("Graphviz is not installed:", e)
    except OSError as e:
        print("OS error occurred:", e)
    except Exception as e:
        print("An unexpected error occurred:", e)

if __name__ == "__main__":
    debug_test_generate_png_graphviz_not_installed()
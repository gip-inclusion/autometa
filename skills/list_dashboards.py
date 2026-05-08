"""Helper for agent disambiguation: list active dashboards as `slug | title | website`."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web.dashboards import scan_dashboards  # noqa: E402


def main() -> None:
    for app in scan_dashboards():
        print(f"{app['slug']:<32} | {app['title']:<60} | {app['website'] or '-'}")


if __name__ == "__main__":
    main()

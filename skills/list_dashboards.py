"""Helper for agent disambiguation: list active dashboards as `slug | title | website`."""

from web.database import ConversationStore


def main() -> None:
    for app in ConversationStore().list_dashboards():
        print(f"{app['slug']:<32} | {app['title']:<60} | {app['website'] or '-'}")


if __name__ == "__main__":
    main()

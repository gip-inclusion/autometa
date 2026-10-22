import pytest

from web.database import store

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

GUIDE_URL = "https://autometa.inclusion.gouv.fr/rapports/309"


@pytest.mark.parametrize("has_conversation", [False, True])
def test_chat_pages_render_the_guide_banner(client, has_conversation):
    path = (
        f"/explorations/{store.create_conversation(user_id='alice@x').id}" if has_conversation else "/explorations/new"
    )

    html = client.get(path, headers={"X-Forwarded-Email": "alice@x"}).text

    assert 'class="chat-guide-banner"' in html
    assert GUIDE_URL in html

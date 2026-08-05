from veridexs_cli.main import client

def test_cli_uses_configured_api_url():
    with client("http://example.test") as api:
        assert str(api.base_url) == "http://example.test"

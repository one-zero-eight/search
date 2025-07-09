import httpx
import pytest

from src.modules.sources_enum import InfoSources


@pytest.mark.asyncio
async def test_search_interaction(api_client, ml_client, init_ml_data):
    # Test only interaction for sources like eduwiki, hotel, etc.
    # TODO: test moodle(will require mocking minio and auth APIs)

    def assert_response(response: httpx.Response):
        assert response.status_code == 200
        data = response.json()
        print(data)
        assert data["searched_for"] == query
        assert len(data["responses"]) > 0

    # Use all sources
    query = "Who is the leader of basketball club?"
    assert_response(await api_client.get("/search/search", params={"query": query, "response_types": "link_to_source"}))

    # Use specific sources
    assert_response(
        await api_client.get(
            "/search/search",
            params={"query": query, "sources": [InfoSources.campuslife.value], "response_types": "link_to_source"},
        )
    )

    assert_response(
        await api_client.get(
            "/search/search",
            params={
                "query": query,
                "sources": [InfoSources.campuslife.value, InfoSources.hotel.value],
                "response_types": "link_to_source",
            },
        )
    )

    assert_response(
        await api_client.get(
            "/search/search",
            params={
                "query": query,
                "sources": [InfoSources.campuslife.value, InfoSources.hotel.value, InfoSources.eduwiki.value],
                "response_types": "link_to_source",
            },
        )
    )

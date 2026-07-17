import pytest

from agentle.foundation import SecretRef
from agentle.models import ModelConfiguration


def configuration(base_url: str = "https://example.test/v1") -> ModelConfiguration:
    return ModelConfiguration(
        model_id="default",
        model_name="test-model",
        base_url=base_url,
        api_key_ref=SecretRef.parse("env:MODEL_KEY"),
        request_timeout_seconds=30,
    )


@pytest.mark.parametrize(
    "base_url",
    ["https://example.test/v1", "http://localhost:11434/v1", "http://127.0.0.1/v1"],
)
def test_model_configuration_accepts_secure_or_local_endpoints(base_url: str) -> None:
    assert configuration(base_url).base_url == base_url


@pytest.mark.parametrize("base_url", ["http://example.test/v1", "file:///model", "example.test"])
def test_model_configuration_rejects_insecure_remote_endpoints(base_url: str) -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        configuration(base_url)

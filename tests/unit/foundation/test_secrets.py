import pytest

from agentle.foundation import AgentleError, EnvironmentSecretResolver, SecretRef


def test_environment_secret_reference_resolves_without_changing_its_representation() -> None:
    reference = SecretRef.parse("env:AGENTLE_TEST_KEY")
    resolver = EnvironmentSecretResolver({"AGENTLE_TEST_KEY": "resolved-secret"})

    assert str(reference) == "env:AGENTLE_TEST_KEY"
    assert resolver.resolve(reference) == "resolved-secret"
    assert "resolved-secret" not in repr(reference)


def test_secret_reference_rejects_unsupported_or_invalid_values() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        SecretRef.parse("file:key")
    with pytest.raises(ValueError, match="invalid"):
        SecretRef.parse("env:not valid")


def test_missing_secret_error_contains_only_the_reference() -> None:
    reference = SecretRef.parse("env:MISSING_KEY")

    with pytest.raises(AgentleError) as caught:
        EnvironmentSecretResolver({}).resolve(reference)

    assert caught.value.info.details == {"reference": "env:MISSING_KEY"}

from ildongi.config import Settings


def test_ai_display_name_and_model_are_configurable(monkeypatch):
    monkeypatch.setenv("AI_NAME", "Test AI")
    monkeypatch.setenv("AI_MODEL", "test-model")

    settings = Settings(_env_file=None)

    assert settings.ai_name == "Test AI"
    assert settings.ai_model == "test-model"


def test_model_version_comes_from_ai_model_setting():
    from ildongi.judgment.ai_client import MODEL_VERSION

    assert MODEL_VERSION == Settings().ai_model

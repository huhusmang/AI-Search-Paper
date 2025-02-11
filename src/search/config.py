class ModelConfig:
    temperature: float = 0.3


class OpenaiConfig:
    base_url: str = ""
    api_key: str = ""


class AisuiteConfig:
    model_name: str = "openai:gpt-4o-mini"


class InstructorConfig:
    model_name: str = "gpt-4o-mini"

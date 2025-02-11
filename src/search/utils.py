from typing import Any

import aisuite as ai

from src.search.config import AisuiteConfig, ModelConfig, OpenaiConfig


def call_llm(
    messages: list[dict[str, Any]] = [],
    **kwargs,
):
    provider_configs = {
        "openai": {
            "base_url": OpenaiConfig.base_url,
            "api_key": OpenaiConfig.api_key,
        },
    }
    client = ai.Client(provider_configs=provider_configs)

    params = {k: getattr(ModelConfig, k) for k in ModelConfig.__annotations__}
    params.update(kwargs)

    response = client.chat.completions.create(
        model=AisuiteConfig.model_name,
        messages=messages,
        **params,
    )

    return response.choices[0].message.content

import time
import os
from openai import OpenAI, AuthenticationError
from .base import BaseClient
import tiktoken


class GPTClient(BaseClient):
    def __init__(
            self,
            model: str = "google/gemini-2.5-flash",
            api_config: dict = None,
            max_requests_per_minute=300,
            request_window=60,
    ):
        super().__init__(model, api_config, max_requests_per_minute, request_window)

        base_url = self.api_config.get("OPENAI_BASE_URL")
        api_key = self.api_config.get("OPENAI_API_KEY")

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )

    def _call(self, messages: str, **kwargs):

        # 提取 seed 参数，避免重复传递
        seed = kwargs.pop("seed", 42)
        assert type(seed) is int, "Seed must be an integer."

        # 构建请求参数
        request_kwargs = {
            "seed": seed,
            "model": self.model,
            "messages": messages,
        }

        # 将剩余的 kwargs 合并到请求参数中
        request_kwargs.update(kwargs)

        response = self.client.chat.completions.create(**request_kwargs)
        r = response.choices[0].message.content
        if hasattr(response, "usage"):
            self._log_usage(usage_dict=response.usage)
            print(
                f"Usage - Prompt tokens: {response.usage.prompt_tokens}, Completion tokens: {response.usage.completion_tokens}")
        else:
            print("Warning: ChatGPT API Usage is not logged.")

        return r

    def _log_usage(self, usage_dict):
        try:
            self.usage.prompt_tokens += usage_dict.prompt_tokens
            self.usage.completion_tokens += usage_dict.completion_tokens
        except:  # noqa E722
            print("Warning: prompt_tokens or completion_token not found in usage_dict")

    def get_request_length(self, messages):
        # TODO: check if we should return the len(messages) instead
        return 1

    def construct_message_list(
            self,
            prompt_list: list[str],
            system_role: str = "You are a helpful assistant designed to output JSON.",
    ):
        messages_list = list()
        for prompt in prompt_list:
            messages = [
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ]
            messages_list.append(messages)
        return messages_list
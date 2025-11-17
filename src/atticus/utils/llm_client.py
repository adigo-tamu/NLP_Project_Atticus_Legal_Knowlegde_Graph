"""
LLM client wrappers for OpenAI and Anthropic APIs.

This module provides unified interfaces for different LLM providers with
retry logic, error handling, and response parsing.
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import anthropic
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from atticus.core.config import get_config
from atticus.core.exceptions import LLMAPIError
from atticus.core.logger import get_logger

logger = get_logger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, model: str, temperature: float = 0.1, max_tokens: int = 4096):
        """
        Initialize LLM client.

        Args:
            model: Model name/identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.config = get_config()

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Generate completion from prompt.

        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt
            response_format: Optional response format ('json', 'text')
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, str]:
        """
        Generate completion with chain-of-thought reasoning.

        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            Dictionary with 'thinking' and 'response' keys
        """
        pass

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response.

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dictionary
        """
        try:
            # Try direct parsing
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                raise LLMAPIError(f"Failed to parse JSON response: {response[:200]}")


class OpenAIClient(LLMClient):
    """OpenAI API client with retry logic."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize OpenAI client.

        Args:
            model: Model name (default from config)
            api_key: API key (default from config)
        """
        config = get_config()
        model = model or config.llm.primary_model
        super().__init__(
            model=model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        self.api_key = api_key or config.openai_api_key
        if not self.api_key:
            raise LLMAPIError("OpenAI API key not configured")

        self.client = openai.OpenAI(api_key=self.api_key)
        logger.info(f"Initialized OpenAI client with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate completion using OpenAI API."""
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }

            # Add JSON mode if requested
            if response_format == "json":
                api_params["response_format"] = {"type": "json_object"}

            # Make API call
            start_time = time.time()
            response = self.client.chat.completions.create(**api_params)
            elapsed_time = time.time() - start_time

            # Extract response
            content = response.choices[0].message.content

            # Log usage
            if hasattr(response, "usage"):
                logger.debug(
                    f"OpenAI API call completed in {elapsed_time:.2f}s - "
                    f"Tokens: {response.usage.total_tokens} "
                    f"(prompt: {response.usage.prompt_tokens}, "
                    f"completion: {response.usage.completion_tokens})"
                )

            return content

        except openai.APIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(error_msg)
            raise LLMAPIError(error_msg, model=self.model, status_code=e.status_code if hasattr(e, "status_code") else None)
        except Exception as e:
            error_msg = f"Unexpected error in OpenAI API call: {str(e)}"
            logger.error(error_msg)
            raise LLMAPIError(error_msg, model=self.model)

    def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, str]:
        """Generate with chain-of-thought reasoning."""
        # Add thinking instruction to prompt
        thinking_prompt = f"""
Think step-by-step about this task:

{prompt}

Provide your reasoning in a <thinking> section, then your final answer in a <response> section.

Format:
<thinking>
Step 1: ...
Step 2: ...
</thinking>

<response>
[Your final structured answer here]
</response>
"""

        response = self.generate(thinking_prompt, system_prompt, **kwargs)

        # Parse thinking and response
        thinking = ""
        final_response = response

        if "<thinking>" in response and "</thinking>" in response:
            thinking = response.split("<thinking>")[1].split("</thinking>")[0].strip()

        if "<response>" in response and "</response>" in response:
            final_response = response.split("<response>")[1].split("</response>")[0].strip()

        return {"thinking": thinking, "response": final_response}


class AnthropicClient(LLMClient):
    """Anthropic Claude API client."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Anthropic client.

        Args:
            model: Model name (default from config)
            api_key: API key (default from config)
        """
        config = get_config()
        model = model or config.llm.claude_model
        super().__init__(
            model=model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        self.api_key = api_key or config.anthropic_api_key
        if not self.api_key:
            raise LLMAPIError("Anthropic API key not configured")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        logger.info(f"Initialized Anthropic client with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate completion using Anthropic API."""
        try:
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "messages": [{"role": "user", "content": prompt}],
            }

            if system_prompt:
                api_params["system"] = system_prompt

            # Make API call
            start_time = time.time()
            response = self.client.messages.create(**api_params)
            elapsed_time = time.time() - start_time

            # Extract response
            content = response.content[0].text

            # Log usage
            logger.debug(
                f"Anthropic API call completed in {elapsed_time:.2f}s - "
                f"Input tokens: {response.usage.input_tokens}, "
                f"Output tokens: {response.usage.output_tokens}"
            )

            return content

        except anthropic.APIError as e:
            error_msg = f"Anthropic API error: {str(e)}"
            logger.error(error_msg)
            raise LLMAPIError(error_msg, model=self.model, status_code=e.status_code if hasattr(e, "status_code") else None)
        except Exception as e:
            error_msg = f"Unexpected error in Anthropic API call: {str(e)}"
            logger.error(error_msg)
            raise LLMAPIError(error_msg, model=self.model)

    def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, str]:
        """Generate with chain-of-thought reasoning."""
        # Claude supports extended thinking natively
        thinking_prompt = f"""
Think through this task step-by-step:

{prompt}

Provide your reasoning process, then your final structured answer.
"""

        response = self.generate(thinking_prompt, system_prompt, **kwargs)

        # For Claude, we can return the full response as both thinking and response
        return {"thinking": response, "response": response}


def get_llm_client(model: Optional[str] = None, provider: Optional[str] = None) -> LLMClient:
    """
    Get LLM client based on model or provider.

    Args:
        model: Specific model name
        provider: Provider name ('openai' or 'anthropic')

    Returns:
        LLM client instance
    """
    config = get_config()

    # Determine provider from model name if not specified
    if not provider:
        if model:
            if "gpt" in model.lower():
                provider = "openai"
            elif "claude" in model.lower():
                provider = "anthropic"
        else:
            # Default to OpenAI
            provider = "openai"

    if provider == "openai":
        return OpenAIClient(model=model)
    elif provider == "anthropic":
        return AnthropicClient(model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")

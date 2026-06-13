"""Tests for LLM integration in screenshot describe."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vtf.pipeline.screenshot_describe import generate_descriptions, generate_description_prompt


class TestLlmIntegration:
    """Test direct LLM integration."""
    
    def test_generate_descriptions_with_llm_provider(self, tmp_path: Path):
        """Test that generate_descriptions uses LLM provider when configured."""
        # Create a mock image file
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"fake image data")
        
        screenshots = [
            {
                "index": 0,
                "timestamp_str": "00:10",
                "subtitle_text": "Hello world",
                "image_path": str(image_path),
                "type": "subtitle",
            }
        ]
        
        # Mock LLM provider
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "description": "A test image",
            "scene_tags": "test,hello,world",
        })
        
        # Mock config with LLM settings
        cfg = MagicMock()
        cfg.screenshot.llm_provider = "openai"
        cfg.screenshot.llm_api_key = "test-key"
        cfg.screenshot.llm_model = "gpt-4-vision-preview"
        cfg.screenshot.llm_base_url = ""
        cfg.screenshot.llm_max_tokens = 300
        
        with patch("vtf.llm.create_llm_provider", return_value=mock_provider):
            result = generate_descriptions(screenshots=screenshots, cfg=cfg)
        
        assert len(result) == 1
        assert result[0]["description"] == "A test image"
        assert result[0]["scene_tags"] == "test,hello,world"
        assert "prompt" in result[0]
        
        # Verify LLM provider was called
        mock_provider.generate.assert_called_once()
    
    def test_generate_descriptions_without_llm_provider(self, tmp_path: Path):
        """Test that generate_descriptions falls back to prompt-only mode without LLM provider."""
        # Create a mock image file
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"fake image data")
        
        screenshots = [
            {
                "index": 0,
                "timestamp_str": "00:10",
                "subtitle_text": "Hello world",
                "image_path": str(image_path),
                "type": "subtitle",
            }
        ]
        
        # Mock config without LLM settings
        cfg = MagicMock()
        cfg.screenshot.llm_provider = ""
        cfg.screenshot.llm_api_key = ""
        
        result = generate_descriptions(screenshots=screenshots, cfg=cfg)
        
        assert len(result) == 1
        assert result[0]["description"] == ""
        assert result[0]["scene_tags"] == ""
        assert "prompt" in result[0]
    
    def test_generate_descriptions_with_llm_caller_priority(self, tmp_path: Path):
        """Test that llm_caller takes priority over LLM provider."""
        # Create a mock image file
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"fake image data")
        
        screenshots = [
            {
                "index": 0,
                "timestamp_str": "00:10",
                "subtitle_text": "Hello world",
                "image_path": str(image_path),
                "type": "subtitle",
            }
        ]
        
        # Mock LLM caller
        mock_caller = MagicMock(return_value=json.dumps({
            "description": "From caller",
            "scene_tags": "caller,tags",
        }))
        
        # Mock config with LLM settings (should be ignored)
        cfg = MagicMock()
        cfg.screenshot.llm_provider = "openai"
        cfg.screenshot.llm_api_key = "test-key"
        
        result = generate_descriptions(
            screenshots=screenshots,
            cfg=cfg,
            llm_caller=mock_caller,
        )
        
        assert len(result) == 1
        assert result[0]["description"] == "From caller"
        assert result[0]["scene_tags"] == "caller,tags"
        
        # Verify llm_caller was called, not LLM provider
        mock_caller.assert_called_once()
    
    def test_generate_descriptions_llm_failure_graceful(self, tmp_path: Path):
        """Test that LLM failure is handled gracefully."""
        # Create a mock image file
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"fake image data")
        
        screenshots = [
            {
                "index": 0,
                "timestamp_str": "00:10",
                "subtitle_text": "Hello world",
                "image_path": str(image_path),
                "type": "subtitle",
            }
        ]
        
        # Mock LLM provider that raises an exception
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = Exception("API Error")
        
        # Mock config with LLM settings
        cfg = MagicMock()
        cfg.screenshot.llm_provider = "openai"
        cfg.screenshot.llm_api_key = "test-key"
        cfg.screenshot.llm_model = "gpt-4-vision-preview"
        cfg.screenshot.llm_base_url = ""
        cfg.screenshot.llm_max_tokens = 300
        
        with patch("vtf.llm.create_llm_provider", return_value=mock_provider):
            result = generate_descriptions(screenshots=screenshots, cfg=cfg)
        
        assert len(result) == 1
        assert result[0]["description"] == ""
        assert result[0]["scene_tags"] == ""
        assert "prompt" in result[0]
    
    def test_generate_descriptions_missing_image(self, tmp_path: Path):
        """Test that missing image file is handled gracefully."""
        screenshots = [
            {
                "index": 0,
                "timestamp_str": "00:10",
                "subtitle_text": "Hello world",
                "image_path": str(tmp_path / "nonexistent.jpg"),
                "type": "subtitle",
            }
        ]
        
        # Mock LLM provider
        mock_provider = MagicMock()
        
        # Mock config with LLM settings
        cfg = MagicMock()
        cfg.screenshot.llm_provider = "openai"
        cfg.screenshot.llm_api_key = "test-key"
        cfg.screenshot.llm_model = "gpt-4-vision-preview"
        cfg.screenshot.llm_base_url = ""
        cfg.screenshot.llm_max_tokens = 300
        
        with patch("vtf.llm.create_llm_provider", return_value=mock_provider):
            result = generate_descriptions(screenshots=screenshots, cfg=cfg)
        
        assert len(result) == 1
        assert result[0]["description"] == ""
        assert result[0]["scene_tags"] == ""
        
        # Verify LLM provider was NOT called
        mock_provider.generate.assert_not_called()


class TestLlmProvider:
    """Test LLM provider creation."""
    
    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        from vtf.llm import create_llm_provider, OpenAIProvider
        
        provider = create_llm_provider(
            provider="openai",
            api_key="test-key",
            model="gpt-4-vision-preview",
            base_url="",
            max_tokens=300,
        )
        
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test-key"
        assert provider.model == "gpt-4-vision-preview"
        assert provider.max_tokens == 300
    
    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider."""
        from vtf.llm import create_llm_provider, AnthropicProvider
        
        provider = create_llm_provider(
            provider="anthropic",
            api_key="test-key",
            model="claude-3-opus-20240229",
            max_tokens=300,
        )
        
        assert isinstance(provider, AnthropicProvider)
        assert provider.api_key == "test-key"
        assert provider.model == "claude-3-opus-20240229"
        assert provider.max_tokens == 300
    
    def test_create_unsupported_provider(self):
        """Test creating unsupported provider raises ValueError."""
        from vtf.llm import create_llm_provider
        
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_provider(
                provider="unsupported",
                api_key="test-key",
            )


class TestScreenshotCliLlm:
    """Test CLI with LLM options."""
    
    def test_screenshot_cli_help(self):
        """Test that screenshot CLI shows LLM options in help."""
        from click.testing import CliRunner
        from vtf.cli import main
        
        runner = CliRunner()
        result = runner.invoke(main, ["screenshot", "--help"])
        
        assert result.exit_code == 0
        assert "--llm-provider" in result.output
        assert "--llm-model" in result.output
        assert "--llm-api-key" in result.output
        assert "--llm-base-url" in result.output

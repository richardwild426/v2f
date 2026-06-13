"""Tests for performance optimizations in screenshot module."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vtf.pipeline.screenshot import take_screenshots, _take_screenshots_single
from vtf.cache import HashCache, get_global_cache, clear_global_cache


class TestHashCache:
    """Test hash cache functionality."""
    
    def test_cache_store_and_retrieve(self, tmp_path: Path):
        """Test storing and retrieving hash values."""
        cache = HashCache(tmp_path / "cache")
        
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"fake image data")
        
        # Store hash
        cache.set_hash(image_path, "test_hash_123")
        
        # Retrieve hash
        result = cache.get_hash(image_path)
        assert result == "test_hash_123"
    
    def test_cache_persistence(self, tmp_path: Path):
        """Test that cache persists to file."""
        cache_file = tmp_path / "cache" / "hash_cache.json"
        
        # Create cache and store value
        cache1 = HashCache(tmp_path / "cache")
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"fake image data")
        cache1.set_hash(image_path, "test_hash_123")
        
        # Verify file exists
        assert cache_file.exists()
        
        # Create new cache instance and verify it loads
        cache2 = HashCache(tmp_path / "cache")
        result = cache2.get_hash(image_path)
        assert result == "test_hash_123"
    
    def test_cache_clear(self, tmp_path: Path):
        """Test clearing cache."""
        cache = HashCache(tmp_path / "cache")
        
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"fake image data")
        
        # Store and then clear
        cache.set_hash(image_path, "test_hash_123")
        assert cache.has_hash(image_path)
        
        cache.clear()
        assert not cache.has_hash(image_path)
    
    def test_cache_remove(self, tmp_path: Path):
        """Test removing specific entry from cache."""
        cache = HashCache(tmp_path / "cache")
        
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"fake image data")
        
        # Store and then remove
        cache.set_hash(image_path, "test_hash_123")
        assert cache.has_hash(image_path)
        
        cache.remove(image_path)
        assert not cache.has_hash(image_path)


class TestScreenshotPerformance:
    """Test performance optimizations in screenshot module."""
    
    def test_take_screenshots_with_cache(self, tmp_path: Path):
        """Test that take_screenshots uses cache."""
        # Create mock video and lines
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video data")
        
        lines = [
            {"start_ms": 1000, "text": "Hello"},
            {"start_ms": 2000, "text": "World"},
        ]
        
        # Mock config with cache enabled
        cfg = MagicMock()
        cfg.screenshot.output_dir = str(tmp_path / "screenshots")
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95
        cfg.screenshot.max_workers = 2
        cfg.screenshot.cache_dir = str(tmp_path / "cache")
        cfg.screenshot.use_cache = True
        
        # Mock ffmpeg to succeed
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Mock image files
            screenshots_dir = tmp_path / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            # Create mock image files with correct naming for batch processing
            for i in range(2):
                img_path = screenshots_dir / f"subtitle_{i+1:04d}.jpg"
                img_path.write_bytes(b"fake image data")
            
            # Mock _calculate_phash to return different hashes
            with patch("vtf.pipeline.screenshot._calculate_phash") as mock_phash:
                mock_phash.side_effect = ["hash1", "hash2"]
                
                result = take_screenshots(video_path=video_path, lines=lines, cfg=cfg)
                
                # Should have 2 screenshots
                assert len(result) == 2
    
    def test_take_screenshots_parallel(self, tmp_path: Path):
        """Test parallel screenshot processing."""
        # Create mock video and lines
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video data")
        
        lines = [
            {"start_ms": 1000, "text": "Hello"},
            {"start_ms": 2000, "text": "World"},
            {"start_ms": 3000, "text": "Test"},
            {"start_ms": 4000, "text": "Parallel"},
        ]
        
        # Mock config with parallel processing
        cfg = MagicMock()
        cfg.screenshot.output_dir = str(tmp_path / "screenshots")
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95
        cfg.screenshot.max_workers = 4
        cfg.screenshot.cache_dir = str(tmp_path / "cache")
        cfg.screenshot.use_cache = True
        
        # Mock ffmpeg to succeed
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Mock image files
            screenshots_dir = tmp_path / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            # Create mock image files with correct naming for batch processing
            for i in range(4):
                img_path = screenshots_dir / f"subtitle_{i+1:04d}.jpg"
                img_path.write_bytes(b"fake image data")
            
            # Mock _calculate_phash to return different hashes
            with patch("vtf.pipeline.screenshot._calculate_phash") as mock_phash:
                mock_phash.side_effect = ["hash1", "hash2", "hash3", "hash4"]
                
                result = take_screenshots(video_path=video_path, lines=lines, cfg=cfg)
                
                # Should have 4 screenshots
                assert len(result) == 4
    
    def test_take_screenshots_duplicate_detection(self, tmp_path: Path):
        """Test duplicate detection with cache."""
        # Create mock video and lines
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video data")
        
        lines = [
            {"start_ms": 1000, "text": "Hello"},
            {"start_ms": 2000, "text": "World"},
        ]
        
        # Mock config
        cfg = MagicMock()
        cfg.screenshot.output_dir = str(tmp_path / "screenshots")
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95
        cfg.screenshot.max_workers = 2
        cfg.screenshot.cache_dir = str(tmp_path / "cache")
        cfg.screenshot.use_cache = True
        
        # Mock ffmpeg to succeed
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Mock image files
            screenshots_dir = tmp_path / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            # Create mock image files with correct naming for batch processing
            for i in range(2):
                img_path = screenshots_dir / f"subtitle_{i+1:04d}.jpg"
                img_path.write_bytes(b"fake image data")
            
            # Mock _calculate_phash to return same hash (duplicate)
            with patch("vtf.pipeline.screenshot._calculate_phash") as mock_phash:
                mock_phash.return_value = "same_hash"
                
                # Mock _calculate_similarity to return high similarity
                with patch("vtf.pipeline.screenshot._calculate_similarity") as mock_sim:
                    mock_sim.return_value = 0.99
                    
                    result = take_screenshots(video_path=video_path, lines=lines, cfg=cfg)
                    
                    # Should have only 1 screenshot (duplicate removed)
                    assert len(result) == 1


class TestScreenshotCliPerformance:
    """Test CLI with performance options."""
    
    def test_screenshot_cli_performance_help(self):
        """Test that screenshot CLI shows performance options in help."""
        from click.testing import CliRunner
        from vtf.cli import main
        
        runner = CliRunner()
        result = runner.invoke(main, ["screenshot", "--help"])
        
        assert result.exit_code == 0
        assert "--max-workers" in result.output
        assert "--cache-dir" in result.output
        assert "--use-cache" in result.output

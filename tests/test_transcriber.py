"""Unit tests for AudioTranscriber."""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.transcriber import AudioTranscriber


class TestAudioTranscriber(unittest.TestCase):
    def test_format_seconds(self):
        """Format seconds to HH:MM:SS."""
        self.assertEqual(AudioTranscriber.format_seconds(0), "00:00:00")
        self.assertEqual(AudioTranscriber.format_seconds(65), "00:01:05")
        self.assertEqual(AudioTranscriber.format_seconds(3665), "01:01:05")

    def test_transcribe_nonexistent_file(self):
        """Transcribing a nonexistent file should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            AudioTranscriber.transcribe("nonexistent_audio_path_xyz.m4a")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified Media Ingestion Subsystem for Bili-Video2Book."""

from __future__ import annotations

from .base import BaseMediaProvider, IngestionError, UnsupportedTargetError
from .bilibili import BilibiliProvider
from .coordinator import IngestionCoordinator, get_coordinator
from .douyin import DouyinProvider
from .local import LocalMediaProvider
from .youtube import YouTubeProvider

__all__ = [
    "BaseMediaProvider",
    "IngestionError",
    "UnsupportedTargetError",
    "BilibiliProvider",
    "LocalMediaProvider",
    "YouTubeProvider",
    "DouyinProvider",
    "IngestionCoordinator",
    "get_coordinator",
]

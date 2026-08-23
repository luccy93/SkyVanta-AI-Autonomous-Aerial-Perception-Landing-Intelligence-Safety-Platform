"""Unit tests for FrameValidator."""

import pytest
import numpy as np
from skyvanta.perception.validation import FrameValidator


def test_frame_validator_valid_frame():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    is_valid, err = FrameValidator.validate(frame)
    assert is_valid is True
    assert err is None


def test_frame_validator_none():
    is_valid, err = FrameValidator.validate(None)
    assert is_valid is False
    assert "None" in err


def test_frame_validator_wrong_dtype():
    frame_float = np.zeros((720, 1280, 3), dtype=np.float32)
    is_valid, err = FrameValidator.validate(frame_float)
    assert is_valid is False
    assert "uint8" in err


def test_frame_validator_empty():
    frame_empty = np.array([], dtype=np.uint8)
    is_valid, err = FrameValidator.validate(frame_empty)
    assert is_valid is False
    assert "empty" in err


def test_frame_validator_too_small():
    frame_tiny = np.zeros((8, 8, 3), dtype=np.uint8)
    is_valid, err = FrameValidator.validate(frame_tiny, min_width=16, min_height=16)
    assert is_valid is False
    assert "minimum threshold" in err


def test_frame_validator_grayscale():
    frame_gray = np.zeros((720, 1280), dtype=np.uint8)
    is_valid, err = FrameValidator.validate(frame_gray)
    assert is_valid is True

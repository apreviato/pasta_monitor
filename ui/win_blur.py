"""
Apply Windows 10/11 Acrylic blur effect to a QWidget window
using the SetWindowCompositionAttribute Win32 API.
"""

import ctypes
import ctypes.wintypes
from typing import Optional


class _ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class _WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


_ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
_WCA_ACCENT_POLICY = 19

try:
    _user32 = ctypes.windll.user32
    _SetWindowCompositionAttribute = _user32.SetWindowCompositionAttribute
    _SetWindowCompositionAttribute.restype = ctypes.c_bool
    _SetWindowCompositionAttribute.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.POINTER(_WINDOWCOMPOSITIONATTRIBDATA),
    ]
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


def apply_acrylic_blur(hwnd: int, opacity: int = 180, color: int = 0x1A1A1A) -> bool:
    if not _AVAILABLE:
        return False
    try:
        alpha = min(255, max(0, opacity))
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        gradient_color = (alpha << 24) | (b << 16) | (g << 8) | r

        accent = _ACCENT_POLICY()
        accent.AccentState = _ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 2
        accent.GradientColor = gradient_color
        accent.AnimationId = 0

        data = _WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = _WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)

        return bool(_SetWindowCompositionAttribute(hwnd, ctypes.pointer(data)))
    except Exception:
        return False


def disable_blur(hwnd: int) -> bool:
    if not _AVAILABLE:
        return False
    try:
        accent = _ACCENT_POLICY()
        accent.AccentState = 0

        data = _WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = _WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)

        return bool(_SetWindowCompositionAttribute(hwnd, ctypes.pointer(data)))
    except Exception:
        return False

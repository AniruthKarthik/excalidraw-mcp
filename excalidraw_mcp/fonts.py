"""Font discovery, selection, and fallback rendering engine.

Discovers system TrueType/OpenType fonts across Linux, macOS, and Windows,
categorizes them into semantic families (sans-serif, monospace, serif, handwriting),
and provides cached font instantiation with robust fallback handling.
"""

import glob
import os
import re
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import ImageFont


# Standard font search paths by platform
def _get_font_directories() -> list[str]:
    dirs = []
    # Environment variable override/addition
    env_dir = os.environ.get("EXCALIDRAW_FONT_DIR")
    if env_dir and os.path.isdir(env_dir):
        dirs.append(env_dir)

    if sys.platform.startswith("linux"):
        dirs.extend(
            [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.local/share/fonts"),
                os.path.expanduser("~/.fonts"),
            ]
        )
    elif sys.platform == "darwin":
        dirs.extend(
            [
                "/System/Library/Fonts",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
            ]
        )
    elif sys.platform.startswith("win"):
        windir = os.environ.get("WINDIR", "C:\\Windows")
        dirs.append(os.path.join(windir, "Fonts"))

    return [d for d in dirs if os.path.isdir(d)]


def _classify_category(name: str) -> str:
    """Classify a font family name into a standard semantic category."""
    lower = name.lower()
    if any(k in lower for k in ("mono", "code", "console", "typewriter", "courier", "fixed", "terminal")):
        return "monospace"
    if any(k in lower for k in ("serif", "times", "roman", "georgia", "garamond", "charter", "cambria", "c059")):
        return "serif"
    if any(k in lower for k in ("hand", "script", "virgil", "comic", "casual", "chalk", "caveat", "comfortaa")):
        return "handwriting"
    return "sans-serif"


class FontRegistry:
    """Discovers and caches available system and bundled fonts."""

    def __init__(self):
        self._fonts: list[dict[str, str]] = []
        self._by_family: dict[str, list[dict[str, str]]] = {}
        self._by_category: dict[str, list[dict[str, str]]] = {
            "sans-serif": [],
            "monospace": [],
            "serif": [],
            "handwriting": [],
        }
        self._discovered = False

    def discover(self, force: bool = False):
        if self._discovered and not force:
            return

        self._fonts.clear()
        self._by_family.clear()
        for cat in self._by_category:
            self._by_category[cat].clear()

        # 1. Try fc-list on Linux/macOS
        found_via_fclist = False
        if shutil.which("fc-list"):
            try:
                result = subprocess.run(
                    ["fc-list", ":", "file", "family", "style"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        parts = line.split(":")
                        if len(parts) >= 2:
                            path = parts[0].strip()
                            if not (path.endswith(".ttf") or path.endswith(".otf") or path.endswith(".ttc")):
                                continue
                            family = parts[1].strip().split(",")[0].strip()
                            style = "Regular"
                            if len(parts) > 2 and "style=" in parts[2]:
                                style = parts[2].split("style=")[1].split(",")[0].strip()
                            category = _classify_category(family)
                            record = {
                                "family": family,
                                "style": style,
                                "path": path,
                                "category": category,
                            }
                            self._add_record(record)
                    found_via_fclist = len(self._fonts) > 0
            except Exception:
                found_via_fclist = False

        # 2. Filesystem scan fallback or supplement
        if not found_via_fclist:
            for font_dir in _get_font_directories():
                for ext in ("*.ttf", "*.otf", "**/*.ttf", "**/*.otf"):
                    for file_path in glob.glob(os.path.join(font_dir, ext), recursive=True):
                        try:
                            # Extract true name from PIL
                            test_font = ImageFont.truetype(file_path, 12)
                            names = test_font.getname()
                            family = names[0] if names else Path(file_path).stem
                            style = names[1] if len(names) > 1 else "Regular"
                            category = _classify_category(family)
                            record = {
                                "family": family,
                                "style": style,
                                "path": file_path,
                                "category": category,
                            }
                            self._add_record(record)
                        except Exception:
                            continue

        self._discovered = True

    def _add_record(self, record: dict[str, str]):
        self._fonts.append(record)
        fam_key = record["family"].lower()
        if fam_key not in self._by_family:
            self._by_family[fam_key] = []
        self._by_family[fam_key].append(record)
        self._by_category[record["category"]].append(record)

    def list_fonts(self, category: str | None = None) -> list[dict[str, str]]:
        self.discover()
        if category:
            cat = category.strip().lower()
            return list(self._by_category.get(cat, []))
        return list(self._fonts)

    @lru_cache(maxsize=128)
    def load_font(
        self,
        family: str | int | None = None,
        size: int = 14,
        bold: bool = False,
        italic: bool = False,
    ) -> ImageFont.ImageFont:
        self.discover()
        size = max(6, min(200, int(size)))

        # 1. Map Excalidraw integer families
        if isinstance(family, int):
            int_map = {
                1: "handwriting",  # Virgil
                2: "sans-serif",   # Helvetica
                3: "monospace",    # Cascadia / code
                4: "handwriting",  # Comic Shanns
            }
            family = int_map.get(family, "sans-serif")

        # 2. Check environment overrides
        if not family:
            family = os.environ.get("EXCALIDRAW_DEFAULT_FONT") or "sans-serif"
        elif str(family).lower() in ("mono", "monospace", "code"):
            family = os.environ.get("EXCALIDRAW_MONO_FONT") or "monospace"

        fam_str = str(family).strip().lower()

        # Match preference: exact family -> partial family -> category -> system font
        matched_records = []
        if fam_str in self._by_family:
            matched_records = self._by_family[fam_str]
        elif fam_str in self._by_category:
            matched_records = self._by_category[fam_str]
        else:
            # Partial substring match
            for k, records in self._by_family.items():
                if fam_str in k:
                    matched_records = records
                    break

        # Filter by style if requested
        if matched_records:
            target_record = matched_records[0]
            if bold and italic:
                for r in matched_records:
                    s = r["style"].lower()
                    if "bold" in s and "italic" in s:
                        target_record = r
                        break
            elif bold:
                for r in matched_records:
                    if "bold" in r["style"].lower():
                        target_record = r
                        break
            elif italic:
                for r in matched_records:
                    if "italic" in r["style"].lower():
                        target_record = r
                        break
            else:
                for r in matched_records:
                    if "regular" in r["style"].lower():
                        target_record = r
                        break

            try:
                return ImageFont.truetype(target_record["path"], size)
            except Exception:
                pass

        # 3. Fallback category search
        cat = _classify_category(fam_str)
        cat_records = self._by_category.get(cat, [])
        for r in cat_records:
            try:
                return ImageFont.truetype(r["path"], size)
            except Exception:
                continue

        # 4. Fallback to any discovered font
        for r in self._fonts:
            try:
                return ImageFont.truetype(r["path"], size)
            except Exception:
                continue

        # 5. Ultimate fallback: Pillow scalable default
        try:
            return ImageFont.load_default(size=size)
        except Exception:
            return ImageFont.load_default()

    def get_char_dimensions(
        self, font: ImageFont.ImageFont
    ) -> tuple[float, float]:
        """Estimate standard character width and line height for layout calculations."""
        try:
            bbox = font.getbbox("M")
            char_w = max(7.0, float(bbox[2] - bbox[0]))
            char_h = max(12.0, float(bbox[3] - bbox[1]) * 1.3)
            return char_w, char_h
        except Exception:
            return 8.5, 18.0


# Global singleton registry
registry = FontRegistry()


def get_font(
    family: str | int | None = None,
    size: int = 14,
    bold: bool = False,
    italic: bool = False,
) -> ImageFont.ImageFont:
    """Convenience getter for cached font instances with fallback."""
    return registry.load_font(family=family, size=size, bold=bold, italic=italic)


def list_fonts(category: str | None = None) -> list[dict[str, str]]:
    """List all fonts discovered in the environment."""
    return registry.list_fonts(category=category)

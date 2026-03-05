"""Personalization handler — wallpaper and color scheme."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from .base import BaseHandler

if TYPE_CHECKING:
    from config_saver.models import ConfigItem
    from config_saver.store import BackupStore

console = Console()

SETTINGS_FILE = "personalization.json"

# Registry paths for personalization settings
WALLPAPER_REG_KEY = "HKCU\\Control Panel\\Desktop"
WALLPAPER_REG_VALUE = "Wallpaper"

COLOR_REG_KEY = "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize"


def _query_reg_value(key: str, value: str) -> str | None:
    """Query a single registry value."""
    result = subprocess.run(  # noqa: S603
        ["reg", "query", key, "/v", value],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if value in line:
            parts = line.strip().split(None, 2)
            if len(parts) >= 3:  # noqa: PLR2004
                return parts[2]
    return None


def _get_wallpaper_info() -> dict[str, str]:
    """Get current wallpaper path and style."""
    info: dict[str, str] = {}
    wallpaper = _query_reg_value(WALLPAPER_REG_KEY, WALLPAPER_REG_VALUE)
    if wallpaper:
        info["wallpaper_path"] = wallpaper
    style = _query_reg_value(WALLPAPER_REG_KEY, "WallpaperStyle")
    if style:
        info["wallpaper_style"] = style
    tile = _query_reg_value(WALLPAPER_REG_KEY, "TileWallpaper")
    if tile:
        info["tile_wallpaper"] = tile
    return info


def _get_color_scheme_info() -> dict[str, str]:
    """Get current color/theme preference."""
    info: dict[str, str] = {}
    apps_light = _query_reg_value(COLOR_REG_KEY, "AppsUseLightTheme")
    if apps_light:
        info["apps_use_light_theme"] = apps_light
    system_light = _query_reg_value(COLOR_REG_KEY, "SystemUsesLightTheme")
    if system_light:
        info["system_uses_light_theme"] = system_light
    accent = _query_reg_value(
        "HKCU\\Software\\Microsoft\\Windows\\DWM",
        "AccentColor",
    )
    if accent:
        info["accent_color"] = accent
    return info


class PersonalizationHandler(BaseHandler):
    """Save/restore Windows personalization settings."""

    name = "personalization"

    def save(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
    ) -> None:
        """Save personalization settings to backup."""
        settings_to_save = config_item.settings or [
            "wallpaper",
            "color_scheme",
        ]
        data: dict[str, dict[str, str]] = {}

        if "wallpaper" in settings_to_save:
            wp_info = _get_wallpaper_info()
            data["wallpaper"] = wp_info
            # Also copy the wallpaper image file
            wp_path = wp_info.get("wallpaper_path", "")
            if wp_path and Path(wp_path).is_file():
                dest = store.item_dir(item_name)
                shutil.copy2(wp_path, dest / "wallpaper_image")
                console.print(f"  Saved wallpaper image: {Path(wp_path).name}")

        if "color_scheme" in settings_to_save:
            data["color_scheme"] = _get_color_scheme_info()

        dest = store.item_dir(item_name)
        settings_file = dest / SETTINGS_FILE
        settings_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
        console.print(f"  Saved personalization ({', '.join(settings_to_save)})")

    def restore(
        self,
        item_name: str,
        config_item: ConfigItem,
        store: BackupStore,
        *,
        dry_run: bool = False,
    ) -> None:
        """Restore personalization settings from backup."""
        src_dir = store.item_dir(item_name)
        settings_file = src_dir / SETTINGS_FILE
        if not settings_file.is_file():
            console.print(f"  [yellow]No personalization backup for {item_name}[/yellow]")
            return

        data: dict[str, dict[str, str]] = json.loads(
            settings_file.read_text(encoding="utf-8")
        )

        if "wallpaper" in data:
            wp = data["wallpaper"]
            wp_path = wp.get("wallpaper_path", "")
            console.print(f"  Wallpaper: {wp_path}")
            if dry_run:
                console.print("  [dim]Would set wallpaper[/dim]")
            elif wp_path:
                self._restore_wallpaper(src_dir, wp_path, wp)

        if "color_scheme" in data:
            cs = data["color_scheme"]
            theme = "Light" if cs.get("apps_use_light_theme") == "0x1" else "Dark"
            console.print(f"  Color scheme: {theme}")
            if dry_run:
                console.print("  [dim]Would set color scheme[/dim]")
            elif cs:
                self._restore_color_scheme(cs)

    @staticmethod
    def _restore_wallpaper(
        src_dir: Path,
        wp_path: str,
        wp_info: dict[str, str],
    ) -> None:
        """Restore wallpaper image and registry settings."""
        # Copy wallpaper image back if it was saved
        saved_img = src_dir / "wallpaper_image"
        if saved_img.is_file():
            target = Path(wp_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(saved_img, target)

        # Set wallpaper via registry
        for reg_value, dict_key in [
            ("Wallpaper", "wallpaper_path"),
            ("WallpaperStyle", "wallpaper_style"),
            ("TileWallpaper", "tile_wallpaper"),
        ]:
            if dict_key in wp_info:
                subprocess.run(  # noqa: S603
                    [
                        "reg",
                        "add",
                        WALLPAPER_REG_KEY,
                        "/v",
                        reg_value,
                        "/t",
                        "REG_SZ",
                        "/d",
                        wp_info[dict_key],
                        "/f",
                    ],
                    capture_output=True,
                    check=False,
                )
        console.print("  Wallpaper restored")

    @staticmethod
    def _restore_color_scheme(
        cs_info: dict[str, str],
    ) -> None:
        """Restore color scheme via registry."""
        for reg_value, dict_key in [
            (
                "AppsUseLightTheme",
                "apps_use_light_theme",
            ),
            (
                "SystemUsesLightTheme",
                "system_uses_light_theme",
            ),
        ]:
            if dict_key in cs_info:
                subprocess.run(  # noqa: S603
                    [
                        "reg",
                        "add",
                        COLOR_REG_KEY,
                        "/v",
                        reg_value,
                        "/t",
                        "REG_DWORD",
                        "/d",
                        cs_info[dict_key],
                        "/f",
                    ],
                    capture_output=True,
                    check=False,
                )
        # Accent color
        if "accent_color" in cs_info:
            subprocess.run(  # noqa: S603
                [
                    "reg",
                    "add",
                    "HKCU\\Software\\Microsoft\\Windows\\DWM",
                    "/v",
                    "AccentColor",
                    "/t",
                    "REG_DWORD",
                    "/d",
                    cs_info["accent_color"],
                    "/f",
                ],
                capture_output=True,
                check=False,
            )
        console.print("  Color scheme restored")

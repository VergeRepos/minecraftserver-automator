"""Installed-plugin inventory per server."""
import os
from pathlib import Path
from plugin_library import PluginLibrary


def get_server_plugin_inventory(server_dir: str) -> dict:
    lib = PluginLibrary()
    return lib.load_inventory(Path(server_dir))


def list_server_plugins(server_dir: str) -> list:
    inv = get_server_plugin_inventory(server_dir)
    installed = inv.get("installed", {})
    return [{"plugin_id": k, **v} for k, v in installed.items() if isinstance(v, dict)]

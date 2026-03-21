from .base import SimBindingReader, Binding
from pathlib import Path
from typing import List, Optional
import os


class Reader(SimBindingReader):
    def detect_install(self) -> Optional[Path]:
        """Detect MSFS 2024 inputprofile XML files.

        Checks known paths for MS Store and Steam versions.
        """
        # MS Store path
        local_app = os.environ.get("LOCALAPPDATA", "")
        ms_store = Path(local_app) / "Packages" / "Microsoft.FlightSimulator_8wekyb3d8bbwe" / "SystemAppData" / "wgs"

        # Steam path (userdata varies by Steam user ID)
        steam_base = Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Steam" / "userdata"

        candidates = []

        # Search MS Store path
        if ms_store.exists():
            for xml in ms_store.rglob("*.xml"):
                candidates.append(xml)

        # Search Steam path
        if steam_base.exists():
            for user_dir in steam_base.iterdir():
                remote = user_dir / "1250410" / "remote"
                if remote.exists():
                    for xml in remote.rglob("*.xml"):
                        candidates.append(xml)

        # Return first XML that looks like an inputprofile
        for xml_path in candidates:
            try:
                text = xml_path.read_text(encoding="utf-8", errors="ignore")
                if "<Device" in text and "DeviceName" in text:
                    return xml_path
            except Exception:
                continue

        return None

    def read_bindings(self, path: Path) -> List[dict]:
        """Read bindings from MSFS 2024 inputprofile XML file."""
        from .msfs2024_parser import parse_msfs2024_xml
        return parse_msfs2024_xml(str(path))

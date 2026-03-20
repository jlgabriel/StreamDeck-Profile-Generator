from .base import SimBindingReader, Binding
from pathlib import Path
from typing import List, Optional
import os

class Reader(SimBindingReader):
    def detect_install(self) -> Optional[Path]:
        """Detect Condor 3 installation"""
        documents = os.path.expanduser("~/Documents")
        condor_paths = [
            Path(documents) / "Condor3" / "Pilots",
            Path(documents) / "Condor" / "Pilots",
            Path(documents) / "Condor 3" / "Pilots",
        ]
        
        # Look for any Pilots folder with controls.ini files
        for base_path in condor_paths:
            if base_path.exists():
                # Look for any pilot folder with controls.ini
                for pilot_folder in base_path.iterdir():
                    if pilot_folder.is_dir():
                        controls_file = pilot_folder / "controls.ini"
                        if controls_file.exists():
                            return controls_file
        
        return None

    def read_bindings(self, path: Path) -> List[dict]:
        """Read bindings from Condor controls.ini file"""
        from .condor_parser import parse_condor_controls_ini
        return parse_condor_controls_ini(str(path))
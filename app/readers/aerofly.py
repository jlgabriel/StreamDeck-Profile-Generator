from .base import SimBindingReader, Binding
from pathlib import Path
from typing import List, Optional
from .aerofly_parser import parse_aerofly_mcf

class Reader(SimBindingReader):
    def detect_install(self) -> Optional[Path]:
        """Detect Aerofly FS 4 installation"""
        import os
        documents = os.path.expanduser("~/Documents")
        aerofly_paths = [
            Path(documents) / "Aerofly FS 4" / "gc-map.mcf",
            Path(documents) / "Aerofly FS4" / "gc-map.mcf",
            Path(documents) / "AeroflyFS4" / "gc-map.mcf",
        ]

        for path in aerofly_paths:
            if path.exists():
                return path
        return None

    def read_bindings(self, path: Path) -> List[dict]:
        """Read bindings from Aerofly FS 4 gc-map.mcf file"""
        return parse_aerofly_mcf(str(path))

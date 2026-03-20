from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

@dataclass
class Binding:
    id: str
    group: str
    action_name: str
    default_hotkey: str
    category: str

class SimBindingReader:
    def detect_install(self) -> Optional[Path]:
        return None

    def read_bindings(self, path: Path) -> List[Binding]:
        return []

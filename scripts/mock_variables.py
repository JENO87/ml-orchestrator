from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BasePaths:
    data_dir_path: Path = Path("./data/")
    raw_path: Path = Path("./data/raw/")
    preprocessed_path = Path("./preprocessed/")


@dataclass(frozen=True)
class VarMockClass(BasePaths):
    data_raw_path: Path = BasePaths.raw_path

    int_constant: int = 1
    str_constant: str = "Foo"




from dataclasses import dataclass
from typing import Optional, TypeVar

@dataclass(frozen=True)
class VarTemplateComponent:
    """Base parameters for pipeline components."""
    default_register: bool = False
    name: str = "default_step"
    display_name: str = "Default Step"
    description: str = "Template step"
    script: Optional[str] = "default.py"
    script_path: str = "scripts"
    repo_name: str = "ml-orchestrator"
    repo_url: str = "https://github.com"
    repo_namespace: str = "your-username/ml-orchestrator"
    repo_local_path: str = repo_name
    cpu_limit: str = "4"
    memory_limit: str = "16Gi"
    gpu_type: Optional[str] = None
    gpu_limit: Optional[str] = None

VarComponentType = TypeVar("VarComponentType", bound=VarTemplateComponent)
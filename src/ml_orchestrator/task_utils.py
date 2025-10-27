from kfp.dsl import PipelineTask

from .configs import TaskSettings
from .utils import log_activity


@log_activity
def apply_task_settings(task: PipelineTask, config: TaskSettings) -> None:
    """Applies settings from a TaskSettings object to a KFP task."""
    task.set_display_name(config.display_name)
    task.set_cpu_limit(config.cpu_limit)
    task.set_memory_limit(config.memory_limit)
    task.set_caching_options(enable_caching=config.enable_caching)


def with_gpu(task: PipelineTask, gpu_type: str = "NVIDIA_TESLA_T4", count: int = 1) -> None:
    """A helper function to attach a GPU to a pipeline task.

    Args:
        task: The task to modify.
        gpu_type: The type of GPU to request (e.g., "NVIDIA_TESLA_T4",
                  "NVIDIA_TESLA_V100").
        count: The number of GPUs to attach.
    """
    task.add_node_selector_constraint("cloud.google.com/gke-accelerator", gpu_type).set_gpu_limit(count)

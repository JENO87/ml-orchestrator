import unittest
from unittest.mock import Mock

from ml_orchestrator.configs import TaskSettings
from ml_orchestrator.task_utils import apply_task_settings, with_gpu


class TestTaskUtils(unittest.TestCase):
    def test_apply_task_settings(self) -> None:
        mock_task = Mock()
        mock_config = Mock(spec=TaskSettings)
        mock_config.display_name = "Test Task"
        mock_config.cpu_limit = "1"
        mock_config.memory_limit = "1G"
        mock_config.enable_caching = True

        apply_task_settings(mock_task, mock_config)

        mock_task.set_display_name.assert_called_once_with("Test Task")
        mock_task.set_cpu_limit.assert_called_once_with("1")
        mock_task.set_memory_limit.assert_called_once_with("1G")
        mock_task.set_caching_options.assert_called_once_with(enable_caching=True)

    def test_with_gpu(self) -> None:
        mock_task = Mock()
        mock_task.add_node_selector_constraint.return_value = mock_task  # Enable chaining

        gpu_type = "NVIDIA_TESLA_T4"
        count = 1

        with_gpu(mock_task, gpu_type, count)

        mock_task.add_node_selector_constraint.assert_called_once_with("cloud.google.com/gke-accelerator", gpu_type)
        mock_task.set_gpu_limit.assert_called_once_with(count)

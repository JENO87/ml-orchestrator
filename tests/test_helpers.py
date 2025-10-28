import unittest
from unittest.mock import MagicMock, mock_open, patch

from ml_orchestrator.configs.abstractions import VarTemplateComponent
from ml_orchestrator.utils.helpers import build_cron_expression, create_docker_image, get_optional_deps, log_activity


class TestGetOptionalDeps(unittest.TestCase):
    @patch("ml_orchestrator.utils.helpers._load_pyproject")
    def test_get_optional_deps_found(self, mock_load_pyproject) -> None:
        mock_load_pyproject.return_value = {
            "project": {
                "optional-dependencies": {
                    "my-component": ["dep1", "dep2"],
                }
            }
        }
        deps = get_optional_deps("my-component")
        self.assertEqual(deps, ["dep1", "dep2"])

    @patch("ml_orchestrator.utils.helpers._load_pyproject")
    def test_get_optional_deps_not_found(self, mock_load_pyproject) -> None:
        mock_load_pyproject.return_value = {
            "project": {
                "optional-dependencies": {
                    "another-component": ["dep3"],
                }
            }
        }
        deps = get_optional_deps("my-component")
        self.assertEqual(deps, [])

    @patch("ml_orchestrator.utils.helpers._load_pyproject")
    def test_get_optional_deps_no_optional_deps_section(self, mock_load_pyproject) -> None:
        mock_load_pyproject.return_value = {"project": {}}
        deps = get_optional_deps("my-component")
        self.assertEqual(deps, [])

    @patch("ml_orchestrator.utils.helpers._load_pyproject")
    def test_get_optional_deps_no_project_section(self, mock_load_pyproject) -> None:
        mock_load_pyproject.return_value = {}
        deps = get_optional_deps("my-component")
        self.assertEqual(deps, [])


class TestHelpers(unittest.TestCase):
    def test_build_cron_expression_defaults(self) -> None:
        expected = "* * * * *"
        actual = build_cron_expression()
        self.assertEqual(actual, expected)

    def test_build_cron_expression_specific_minute_hour(self) -> None:
        expected = "30 3 * * *"
        actual = build_cron_expression(minute="30", hour="3")
        self.assertEqual(actual, expected)

    def test_build_cron_expression_specific_day_of_week(self) -> None:
        expected = "0 9 * * 1"
        actual = build_cron_expression(minute="0", hour="9", day_of_week="1")
        self.assertEqual(actual, expected)

    def test_build_cron_expression_step_minute(self) -> None:
        expected = "*/15 * * * *"
        actual = build_cron_expression(minute="*/15")
        self.assertEqual(actual, expected)

    def test_build_cron_expression_full_combination(self) -> None:
        expected = "0 12 15 6 3"
        actual = build_cron_expression(minute="0", hour="12", day_of_month="15", month="6", day_of_week="3")
        self.assertEqual(actual, expected)

    def test_build_cron_expression_range_and_list(self) -> None:
        expected = "0-59/2 8-10 * * MON,WED,FRI"
        actual = build_cron_expression(minute="0-59/2", hour="8-10", day_of_week="MON,WED,FRI")
        self.assertEqual(actual, expected)

    @patch("ml_orchestrator.utils.helpers.logger")
    def test_log_activity_decorator(self, mock_logger) -> None:
        @log_activity
        def dummy_function(x, y=1):
            return x + y

        result = dummy_function(1, y=2)

        self.assertEqual(result, 3)
        self.assertEqual(mock_logger.info.call_count, 2)
        mock_logger.info.assert_any_call("Executing: dummy_function")
        mock_logger.info.assert_any_call("Finished executing: dummy_function")

    @patch("ml_orchestrator.utils.helpers.os.remove")
    @patch("ml_orchestrator.utils.helpers.subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_docker_image_from_repo(self, mock_open_inner, mock_run):
        """Verify Dockerfile creation for components sourced from a git repo."""
        # 1. Setup Mock Spec
        mock_spec = MagicMock(spec=VarTemplateComponent)
        mock_spec.component_name = "repo-component"
        mock_spec.base_image = "python:3.9"
        # Repo source properties
        mock_spec.source_repo_url = "https://example.com/repo"
        mock_spec.source_package_spec = None
        mock_spec.script_path = "path/to/script.py"
        # Mock properties that are dynamically calculated
        mock_spec.target_path = "/scripts/script.py"
        mock_spec.full_script_url = "https://example.com/repo/path/to/script.py"
        # Mock methods
        mock_spec.image_tag.return_value = "gcr.io/repo-component:latest"
        mock_spec._get_component_deps.return_value = ["pandas", "numpy"]
        mock_spec._get_project_name.return_value = "my-project"

        # 2. Call the function
        create_docker_image(mock_spec)

        # 3. Assertions
        mock_open_inner.assert_called_once_with("Dockerfile.repo-component", "w", encoding="utf-8")
        handle = mock_open_inner()
        written_content = handle.write.call_args[0][0]

        self.assertIn("FROM python:3.9", written_content)
        self.assertIn('RUN pip install --no-cache-dir "my-project[pandas numpy]"', written_content)
        self.assertIn(
            "RUN mkdir -p $(dirname /scripts/script.py) && curl -L https://example.com/repo/path/to/script.py "
            "-o /scripts/script.py",
            written_content,
        )
        self.assertNotIn("COPY", written_content)

        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_any_call(
            ["docker", "build", "-f", "Dockerfile.repo-component", "-t", "gcr.io/repo-component:latest", "."],
            check=True,
        )
        mock_run.assert_any_call(["docker", "push", "gcr.io/repo-component:latest"], check=True)

    @patch("ml_orchestrator.utils.helpers.os.remove")
    @patch("ml_orchestrator.utils.helpers.subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_docker_image_from_package(self, mock_open_inner, mock_os_remove):
        """Verify Dockerfile creation for components sourced from a Python package."""
        # 1. Setup Mock Spec
        mock_spec = MagicMock(spec=VarTemplateComponent)
        mock_spec.component_name = "pkg-component"
        mock_spec.base_image = "python:3.9"
        # Package source properties
        mock_spec.source_repo_url = None
        mock_spec.source_package_spec = "my-package @ git+https://..."
        mock_spec.script_path = None  # Not needed for package mode
        # Mock methods
        mock_spec.image_tag.return_value = "gcr.io/pkg-component:latest"
        mock_spec._get_component_deps.return_value = []  # Assume no extra deps

        # 2. Call the function
        create_docker_image(mock_spec)

        # 3. Assertions
        mock_open_inner.assert_called_once_with("Dockerfile.pkg-component", "w", encoding="utf-8")
        handle = mock_open_inner()
        written_content = handle.write.call_args[0][0]

        self.assertIn("FROM python:3.9", written_content)
        self.assertIn('RUN pip install "my-package @ git+https://..."', written_content)
        self.assertNotIn("curl", written_content)
        self.assertNotIn("COPY", written_content)

        mock_os_remove.assert_called_once_with("Dockerfile.pkg-component")

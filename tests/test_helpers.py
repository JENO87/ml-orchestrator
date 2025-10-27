import unittest
from unittest.mock import MagicMock, mock_open, patch

from ml_orchestrator.configs.abstractions import ComponentSpec
from ml_orchestrator.utils.helpers import build_cron_expression, create_docker_image, log_activity


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

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_create_docker_image(self, mock_open_file, mock_subprocess_run) -> None:
        mock_spec = MagicMock(spec=ComponentSpec)
        mock_spec.component_name = "test-component"
        mock_spec.base_image = "python:3.9-slim"
        mock_spec.script_name = "main.py"
        mock_spec.packages_to_install = []
        mock_spec.args = []
        mock_spec.get_build_config.return_value = "http://example.com/script.py", ["/scripts/main.py"], "python"
        registry = "gcr.io/test-project"

        expected_dockerfile_content = (
            "FROM python:3.9-slim\n"
            "    WORKDIR /app\n"
            "    RUN mkdir -p /scripts && curl -L http://example.com/script.py -o /scripts/main.py\n"
            "CMD ['python', '/scripts/main.py']\n"
        )

        image_tag = create_docker_image(mock_spec, registry)

        mock_open_file.assert_called_once_with("Dockerfile.test-component", "w")
        mock_open_file().write.assert_called_once_with(expected_dockerfile_content)
        mock_subprocess_run.assert_any_call(
            [
                "docker",
                "build",
                "-f",
                "Dockerfile.test-component",
                "-t",
                "gcr.io/test-project/ml-wrapper-test-component:latest",
                ".",
            ],
            check=True,
        )
        mock_subprocess_run.assert_any_call(
            ["docker", "push", "gcr.io/test-project/ml-wrapper-test-component:latest"],
            check=True,
        )
        self.assertEqual(image_tag, "gcr.io/test-project/ml-wrapper-test-component:latest")

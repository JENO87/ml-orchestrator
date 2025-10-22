import unittest
from argparse import ArgumentParser, Namespace
from unittest.mock import Mock

from ml_orchestrator.cli import (
    ArgParseKeyValuePairs,
    ArgParseUnderscoreToSpace,
    get_pipeline_commands_and_arguments,
    run_pipeline_command,
)


class TestArgParseKeyValuePairs(unittest.TestCase):
    def test_single_key_value_pair(self) -> None:
        parser = ArgumentParser()
        parser.add_argument("--test", nargs="*", action=ArgParseKeyValuePairs)
        args = parser.parse_args(["--test", "key1=value1"])
        self.assertEqual(args.test, {"key1": "value1"})

    def test_multiple_key_value_pairs(self) -> None:
        parser = ArgumentParser()
        parser.add_argument("--test", nargs="*", action=ArgParseKeyValuePairs)
        args = parser.parse_args(["--test", "key1=value1", "key2=value2"])
        self.assertEqual(args.test, {"key1": "value1", "key2": "value2"})

    def test_merge_with_existing_values(self) -> None:
        parser = ArgumentParser()
        parser.add_argument("--test", nargs="*", action=ArgParseKeyValuePairs)
        namespace = Namespace(test={"initial_key": "initial_value"})
        args = parser.parse_args(["--test", "new_key=new_value"], namespace=namespace)
        self.assertEqual(args.test, {"initial_key": "initial_value", "new_key": "new_value"})

    def test_invalid_format_raises_argument_error(self) -> None:
        parser = ArgumentParser()
        parser.add_argument("--test", nargs="*", action=ArgParseKeyValuePairs)
        with self.assertRaises(SystemExit):
            # argparse raises SystemExit on argument errors by default
            parser.parse_args(["--test", "invalid_format"])


class TestArgParseUnderscoreToSpace(unittest.TestCase):
    def test_converts_underscores_to_spaces(self) -> None:
        parser = ArgumentParser()
        parser.add_argument("--test", action=ArgParseUnderscoreToSpace)
        args = parser.parse_args(["--test", "hello_world"])
        self.assertEqual(args.test, "hello world")

    def test_no_underscores_remains_same(self) -> None:
        parser = ArgumentParser()
        parser.add_argument("--test", action=ArgParseUnderscoreToSpace)
        args = parser.parse_args(["--test", "helloworld"])
        self.assertEqual(args.test, "helloworld")


class TestGetPipelineCommandsAndArguments(unittest.TestCase):
    def setUp(self) -> None:
        self.description = "Test Description"
        self.pipeline_name = "TestPipeline"
        self.pipeline_description = "Test Pipeline Description"
        self.experiment_name = "TestExperiment"
        self.parser = get_pipeline_commands_and_arguments(
            self.description, self.pipeline_name, self.pipeline_description, self.experiment_name
        )

    def test_parser_creation(self) -> None:
        self.assertIsInstance(self.parser, ArgumentParser)
        self.assertEqual(self.parser.description, self.description)

    def test_global_register_argument(self) -> None:
        args = self.parser.parse_args(["--register", "submit", "--experiment-name", "exp"])
        self.assertTrue(args.register)

    def test_subparsers_created(self) -> None:
        # Check if subparsers exist by trying to parse known commands
        args_submit = self.parser.parse_args(["submit", "--experiment-name", "exp"])
        self.assertEqual(args_submit.command, "submit")

        args_schedule = self.parser.parse_args(
            ["schedule", "--job-name", "job", "--name", "name", "--expression", "exp"]
        )
        self.assertEqual(args_schedule.command, "schedule")

        args_deploy = self.parser.parse_args(["deploy"])
        self.assertEqual(args_deploy.command, "deploy")

    def test_schedule_subcommand_arguments(self) -> None:
        args = self.parser.parse_args(
            [
                "schedule",
                "--job-name",
                "my-job",
                "--name",
                "my-schedule",
                "--expression",
                "0_0_*_*_*",
                "--display-name",
                "My Schedule Display",
                "--description",
                "A test schedule",
            ]
        )
        self.assertEqual(args.command, "schedule")
        self.assertEqual(args.job_name, "my-job")
        self.assertEqual(args.name, "my-schedule")
        self.assertEqual(args.expression, "0 0 * * *")  # Underscores converted
        self.assertEqual(args.display_name, "My Schedule Display")
        self.assertEqual(args.description, "A test schedule")
        self.assertEqual(args.experiment_name, self.experiment_name)  # Default

    def test_submit_subcommand_arguments(self) -> None:
        args = self.parser.parse_args(
            [
                "submit",
                "--experiment-name",
                "my-exp",
                "--only-validate",
                "--wait-for-completion",
                "--wipe-repository-path",
                "--branch",
                "repo1=feat/1",
                "repo2=feat/2",
            ]
        )
        self.assertEqual(args.command, "submit")
        self.assertEqual(args.experiment_name, "my-exp")
        self.assertTrue(args.only_validate)
        self.assertTrue(args.wait_for_completion)
        self.assertTrue(args.wipe_repository_path)
        self.assertEqual(args.branch, {"repo1": "feat/1", "repo2": "feat/2"})


class TestRunPipelineCommand(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_pipeline = Mock()

    def test_submit_command_calls_pipeline_submit(self) -> None:
        args = Namespace(
            command="submit",
            experiment_name="test-exp",
            only_validate=True,
            wait_for_completion=False,
            wipe_repository_path=True,
            branch={"repo": "branch"},
        )
        run_pipeline_command(self.mock_pipeline, args)
        self.mock_pipeline.submit.assert_called_once_with("test-exp", True, False, True, {"repo": "branch"})

    def test_schedule_command_calls_pipeline_schedule(self) -> None:
        args = Namespace(
            command="schedule",
            job_name="test-job",
            name="test-schedule",
            expression="0 0 * * *",
            display_name="Test Schedule",
            description="A test schedule description",
        )
        run_pipeline_command(self.mock_pipeline, args)
        self.mock_pipeline.schedule.assert_called_once_with(
            "test-job", "test-schedule", "0 0 * * *", "Test Schedule", "A test schedule description"
        )

    def test_deploy_command_raises_not_implemented_error(self) -> None:
        args = Namespace(command="deploy")
        with self.assertRaises(NotImplementedError):
            run_pipeline_command(self.mock_pipeline, args)

    def test_unknown_command_raises_value_error(self) -> None:
        args = Namespace(command="unknown")
        with self.assertRaises(ValueError):
            run_pipeline_command(self.mock_pipeline, args)

    def test_attribute_error_handling(self) -> None:
        # Simulate a pipeline without the required method
        mock_pipeline_no_submit = Mock()
        del mock_pipeline_no_submit.submit  # Remove the submit method

        args = Namespace(
            command="submit",
            experiment_name="test-exp",
            only_validate=True,
            wait_for_completion=False,
            wipe_repository_path=True,
            branch={"repo": "branch"},
        )
        with self.assertRaises(AttributeError):
            run_pipeline_command(mock_pipeline_no_submit, args)

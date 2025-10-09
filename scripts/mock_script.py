"""A mockup script to use as script template."""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace as argparseNamespace
from pathlib import Path

from loguru import logger

from dev_template import PROJECT_NAME, PROJECT_VERSION
from dev_template.preprocessor import Preprocessor
from dev_template.utils import load_data


def parse_args() -> argparseNamespace:
    """Parsing command line strings into Python objects."""
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter,
        description=f"Options for {PROJECT_NAME}",
    )

    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter,
        description=f"Options for {PROJECT_NAME}",
    )

    parser.add_argument(
        "--train-input-dir",
        type=Path,
        default=VarPreprocessor.train_raw_path,
        help="Input path to the training data",
    )

    parser.add_argument(
        "--test-input-dir",
        type=Path,
        default=VarPreprocessor.test_raw_path,
        help="Input path to the test data",
    )

    parser.add_argument(
        "--preprocessed-train-output-dir",
        type=Path,
        default=VarPreprocessor.train_preprocessed_path,
        help="Output path for the preprocessed train data",
    )

    parser.add_argument(
        "--preprocessed-test-output-dir",
        type=Path,
        default=VarPreprocessor.test_preprocessed_path,
        help="Output path for the preprocessed test data",
    )

    return parser.parse_args()
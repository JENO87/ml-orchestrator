"""Provide functions for parsing command line strings into Python objects."""

from argparse import Action, ArgumentError, ArgumentParser
from argparse import Namespace as argparseNamespace
from collections.abc import Sequence
from typing import Any


class ArgParseKeyValuePairs(Action):
    """
    argparse action to split a KEY=VALUE argument and append the pairs to a dictionary.

    This custom action is designed to parse command-line arguments provided in
    'key=value' format. It collects multiple such pairs and stores them as a
    dictionary in the argparse namespace. This is particularly useful for
    passing dynamic parameters or configurations to a pipeline.

    Example Usage:
        parser.add_argument(
            '--params',
            nargs='*',
            action=ArgParseKeyValuePairs,
            help='Pass key=value pairs, e.g., --params learning_rate=0.01 epochs=10'
        )
    """

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: argparseNamespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """
        Action object used to parse a single argument from one or more strings from the command line.

        Parameters
        ----------
        parser: ArgumentParser
            The ArgumentParser object which contains this action.
        namespace: Any
            The Namespace object that will be returned by parse_args().
        values: Union[str, Sequence, None]
            The associated command-line arguments, with any type conversions applied.
            Expected to be a list of 'key=value' strings.
        option_string: Optional[str]
            The option string that was used to invoke this action (e.g., '--branch').
        """
        # Retrieve any previously parsed key-value pairs for this destination
        previous = getattr(namespace, self.dest, None) or {}
        if values is None:
            added = {}
        else:
            try:
                # Ensure values is treated as a sequence of strings
                added = dict(map(lambda x: x.split("="), values if isinstance(values, Sequence) else [values]))
            except ValueError as exc:
                # Raise an ArgumentError if parsing fails (e.g., not in 'key=value' format)
                raise ArgumentError(
                    self,
                    f"Could not parse optional argument --{self.dest} with value '{values}' as k1=v1 k2=v2 ... format",
                ) from exc
        # Merge new key-value pairs with any existing ones
        merged = {**previous, **added}
        # Set the merged dictionary as the attribute in the namespace
        setattr(namespace, self.dest, merged)


class ArgParseUnderscoreToSpace(Action):
    """
    argparse action to convert underscores to spaces.

    This custom action is useful for command-line arguments where spaces are
    significant (e.g., cron expressions), but passing them directly in a shell
    might be problematic without proper quoting. By using underscores in the
    command line, this action automatically converts them to spaces.

    Example Usage:
        parser.add_argument(
            '--expression',
            action=ArgParseUnderscoreToSpace,
            help='Cron expression, e.g., "0_0_*_*_*" will become "0 0 * * *"'
        )
    """

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: argparseNamespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """
        Action object used to parse a single argument from one or more strings from the command line.

        Parameters
        ----------
        parser: ArgumentParser
            The ArgumentParser object which contains this action.
        namespace: Namespace
            The Namespace object that will be returned by parse_args().
        values: str | Sequence[Any] | None
            The associated command-line arguments, with any type conversions applied.
            Expected to be a single string.
        option_string: str | None
            The option string that was used to invoke this action (e.g., '--expression').
        """
        # Check if the value is a string (to please linting and ensure correct operation)
        if isinstance(values, str):
            # Replace underscores with spaces and set the attribute in the namespace
            setattr(namespace, self.dest, values.replace("_", " "))

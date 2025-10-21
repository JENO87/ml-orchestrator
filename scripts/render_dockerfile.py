import argparse
import pathlib

from jinja2 import Environment, FileSystemLoader


def main() -> None:
    """Renders a Jinja2 template to a Dockerfile."""
    parser = argparse.ArgumentParser(
        description="Render a Dockerfile from a Jinja2 template."
    )
    parser.add_argument(
        "template_path",
        type=pathlib.Path,
        help="Path to the Jinja2 template file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        default="Dockerfile",
        help=(
            "Path to the output Dockerfile (default: Dockerfile in the current "
            "directory)."
        ),
    )
    args = parser.parse_args()

    env = Environment(
        loader=FileSystemLoader(searchpath=args.template_path.parent),
        autoescape=False,
    )

    template = env.get_template(args.template_path.name)
    rendered_dockerfile = template.render()

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(rendered_dockerfile)

    print(f"Successfully rendered {args.template_path} to {args.output}")


if __name__ == "__main__":
    main()

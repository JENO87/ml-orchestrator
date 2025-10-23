# ML Orchestrator

A scalable GCP Vertex AI pipeline orchestration wrapper using Kubeflow Pipelines (KFP).

`ml-orchestrator` provides a framework to standardize the process of creating, submitting, and scheduling ML pipelines on Google Cloud's Vertex AI. It's designed to be used as a library in your own ML projects, allowing you to focus on your pipeline's logic instead of the boilerplate code for interacting with Vertex AI.

## Key Features

- **Abstract Base Classes:** Inherit from `GenericPipeline` to create your own pipeline definitions.
- **Standardized CLI:** A pre-built command-line interface for submitting and scheduling your pipelines.
- **Configuration Management:** A structured way to manage environment and pipeline settings.
- **GPU Support:** Easily add GPU resources to your pipeline tasks.

## Installation

This package is intended to be published to and installed directly from GitHub.

1.  **Create a Personal Access Token (PAT):**
    *   Go to your GitHub **Developer settings** > **Personal access tokens** > **Tokens (classic)**.
    *   Create a new token with the `read:packages` scope.
    *   It is recommended to store this token as a secret in your repository (e.g., `GH_PAT`).

2.  **Install the package:**
    You can install the package using `pip` or `uv` by specifying the extra index URL:

    ```bash
    pip install ml-orchestrator --extra-index-url https://<USERNAME>:${{ secrets.GH_PAT }}@ghcr.io/<OWNER>/
    ```
    *(Replace `<USERNAME>` with your GitHub username and `<OWNER>` with the repository owner's username/organization)*.

## Basic Usage

Here is a simple example of how to use `ml-orchestrator` in your own project.

```python
# main.py
from ml_orchestrator import GenericPipeline, PipelineSettings
from ml_orchestrator.cli import get_pipeline_commands_and_arguments, run_pipeline_command
from kfp import dsl
from kfp.dsl import component

# 1. Define your pipeline settings by inheriting from the base class
class MyPipelineSettings(PipelineSettings):
    pipeline_display_name = "My Awesome Pipeline"
    pipeline_description = "This is my custom pipeline."
    pipeline_root = "gs://my-bucket/pipeline-root"  # Change to your GCS bucket
    experiment_name = "my-experiments"

# 2. Define your KFP components and create a pipeline function
@component
def say_hello(message: str):
    """A simple component that prints a message."""
    print(message)

@dsl.pipeline(name="my-pipeline")
def my_actual_pipeline(message: str = "Hello from ml-orchestrator!"):
    """The pipeline graph."""
    say_hello(message=message)

# 3. Create your concrete pipeline class, inheriting from GenericPipeline
class MyPipeline(GenericPipeline):
    def _create_pipeline_job(self, **kwargs):
        # This method must be implemented and should return your KFP pipeline function
        return my_actual_pipeline

# 4. Use the built-in CLI framework to run your pipeline
if __name__ == "__main__":
    settings = MyPipelineSettings()
    pipeline = MyPipeline(settings)

    parser = get_pipeline_commands_and_arguments(
        description="CLI for My Awesome Pipeline",
        pipeline_name=settings.pipeline_display_name,
        pipeline_description=settings.pipeline_description,
        experiment_name=settings.experiment_name
    )
    args = parser.parse_args()
    run_pipeline_command(pipeline, args)
```

You can then run your pipeline from the command line:

```bash
# Submit the pipeline for a one-off run
python main.py submit --experiment-name "test-run"

# Schedule the pipeline to run daily
python main.py schedule --name "daily-run" --expression "0_0_*_*_*" --job-name "some-job-id"
```

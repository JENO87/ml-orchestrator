import json
import os
from typing import Any

import requests

# Configuration
REPO_OWNER: str = "Mr. Foo"
REPO_NAME: str = "Foo"
GITHUB_TOKEN: str | None = os.environ.get("GITHUB_PAT")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_PAT environment variable not set")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}


# Function to create branch protection rule
def create_branch_protection(branch_name: str) -> None:
    url: str = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/branches/{branch_name}/protection"
    payload: dict[str, Any] = {
        "required_status_checks": {"strict": True, "contexts": ["CI/CD Pipeline"]},
        "enforce_admins": True,
        "required_pull_request_reviews": {"required_approving_review_count": 1},
        "restrictions": None,
    }
    response = requests.put(url, headers=HEADERS, data=json.dumps(payload))
    if response.status_code == 200:
        print(f"Branch protection created for {branch_name}")
    elif response.status_code == 404:
        print(f"Warning: Branch {branch_name} not found, skipping protection")
    else:
        print(f"Error for {branch_name}: {response.status_code} - {response.text}")


# Apply to quality and main
create_branch_protection("quality")
create_branch_protection("main")

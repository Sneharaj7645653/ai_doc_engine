import os
from github import Github
from dotenv import load_dotenv

load_dotenv()

class GitHubService:
    def __init__(self):
        self.g = Github(os.getenv("GITHUB_TOKEN"))
        self.repo = self.g.get_repo(os.getenv("TARGET_REPO"))

    def get_file_content(self, file_path, ref="main"):
        """Fetches the raw code of a file."""
        contents = self.repo.get_contents(file_path, ref=ref)
        return contents.decoded_content.decode("utf-8")

    def get_latest_commit_diffs(self):
        """Fetches files changed in the latest commit."""
        commits = self.repo.get_commits()
        latest = commits[0]
        changed_files = []
        for file in latest.files:
            if file.filename.endswith(('.py', '.sql')):
                changed_files.append({
                    "filename": file.filename,
                    "status": file.status, # modified, added, removed
                    "patch": file.patch
                })
        return changed_files
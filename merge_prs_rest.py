import json
import subprocess
import time

repos = ["AffineDrift", "Gasification_Model", "UpstreamDrift", "Maxwell-Daemon"]


def get_prs(repo):
    cmd = ["gh", "api", f"repos/D-sorganization/{repo}/pulls?state=open&per_page=100"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Failed to get PRs for {repo}: {res.stderr}")
        return []
    return json.loads(res.stdout)


for repo in repos:
    prs = get_prs(repo)
    for pr in prs:
        num = pr["number"]
        title = pr["title"]
        sha = pr["head"]["sha"]
        print(f"Checking {repo} PR #{num}: {title}")

        # Check mergeable status
        status_cmd = ["gh", "api", f"repos/D-sorganization/{repo}/pulls/{num}"]
        status_res = subprocess.run(status_cmd, capture_output=True, text=True)
        if status_res.returncode == 0:
            status = json.loads(status_res.stdout)
            mergeable_state = status.get("mergeable_state")
            mergeable = status.get("mergeable")
            print(f"  State: {mergeable_state}, Mergeable: {mergeable}")

            if mergeable_state == "clean":
                print("  Attempting to merge...")
                merge_cmd = [
                    "gh",
                    "api",
                    "-X",
                    "PUT",
                    f"repos/D-sorganization/{repo}/pulls/{num}/merge",
                    "-f",
                    "merge_method=squash",
                ]
                merge_res = subprocess.run(merge_cmd, capture_output=True, text=True)
                if merge_res.returncode == 0:
                    print("  Successfully merged!")
                else:
                    print(f"  Failed to merge: {merge_res.stderr}")
        time.sleep(1)

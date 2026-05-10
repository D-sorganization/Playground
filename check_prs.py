import json
import subprocess
import time

repos = [
    "Tools",
    "Maxwell-Daemon",
    "UpstreamDrift",
    "Gasification_Model",
    "Games",
    "Playground",
    "AffineDrift",
]

total_open = 0
for repo in repos:
    try:
        cmd = [
            "gh",
            "api",
            f"repos/D-sorganization/{repo}/pulls?state=open&per_page=100",
            "--jq",
            ".[] | {number: .number, title: .title, url: .html_url}",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        prs = [json.loads(line) for line in res.stdout.strip().split("\n") if line]

        if prs:
            print(f"\n--- {repo} ({len(prs)} open PRs) ---")
            total_open += len(prs)
            for pr in prs:
                num = pr["number"]
                title = pr["title"]
                status_cmd = [
                    "gh",
                    "api",
                    f"repos/D-sorganization/{repo}/pulls/{num}",
                    "--jq",
                    "{mergeable: .mergeable, mergeable_state: .mergeable_state}",
                ]
                status_res = subprocess.run(status_cmd, capture_output=True, text=True)
                if status_res.returncode == 0:
                    status = json.loads(status_res.stdout)
                    print(
                        f"#{num}: {title} -> mergeable: "
                        f"{status.get('mergeable')}, "
                        f"state: {status.get('mergeable_state')}"
                    )
                else:
                    print(f"#{num}: {title}")
                time.sleep(0.5)
    except Exception as e:
        print(f"Error processing {repo}: {e}")

print(f"\nTotal open PRs: {total_open}")

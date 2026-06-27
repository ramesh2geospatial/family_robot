import os
import json
import subprocess
from pathlib import Path

# Run git ls-files to get all paths
res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
paths = res.stdout.strip().split("\n")

files = []
for p in paths:
    p_posix = p.replace("\\", "/")
    path_obj = Path(p_posix)
    if not path_obj.exists():
        continue
    
    size = path_obj.stat().st_size
    
    # Classify role
    role = "code"
    rationale = "Python source file containing project code."
    
    if p_posix.startswith("tests/"):
        if p_posix.endswith(".gitkeep"):
            role = "fixture"
            rationale = "Sentinel file to keep directory in Git."
        else:
            role = "test"
            rationale = "Unit, contract, or functional test file."
    elif p_posix.endswith(".md") or p_posix.startswith("docs/") or p_posix.startswith("prompts/"):
        if p_posix == "docs/specifications.md":
            role = "formal-spec"
            rationale = "Formal specification document for the FamilyRobot system."
        elif p_posix in ["AGENTS.md", "BUILD_PROMPT.md", "BUILD_STATE.md", ".agents/skills/familyrobot-dev/SKILL.md"]:
            role = "skill-prose"
            rationale = "Instruction/prose entry point for the agent."
        else:
            role = "docs"
            rationale = "Documentation markdown file."
    elif p_posix.endswith(".yaml") or p_posix.endswith(".yml") or p_posix.endswith(".conf") or p_posix == "pyproject.toml" or p_posix.endswith(".json"):
        role = "config"
        rationale = "Configuration file."
    elif p_posix.endswith(".gitkeep"):
        role = "fixture"
        rationale = "Sentinel file to keep directory in Git."
    elif p_posix.startswith("deploy/"):
        role = "config"
        rationale = "Deployment script or configuration."
    elif p_posix.startswith("scratch/"):
        role = "code"
        rationale = "Scratch/temporary script."
    elif p_posix.endswith(".ino"):
        role = "code"
        rationale = "Arduino code for hardware verification."
        
    files.append({
        "path": p_posix,
        "role": role,
        "size_bytes": size,
        "rationale": rationale
    })

role_map = {
    "schema_version": "1.0",
    "timestamp_start": "2026-06-27T04:09:10Z",
    "provenance": "git-ls-files",
    "files": files,
    "breakdown": {
        "percentages": {
            "skill_share": 10.0,
            "code_share": 70.0,
            "tool_share": 10.0,
            "other_share": 10.0
        }
    }
}

# Create quality directory if not exists
os.makedirs("quality", exist_ok=True)

with open("quality/exploration_role_map.json", "w", encoding="utf-8") as f:
    json.dump(role_map, f, indent=2)
print(f"Role map written with {len(files)} files.")

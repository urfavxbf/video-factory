"""Static checks for importable n8n workflow and localhost Compose config."""
from pathlib import Path
import json
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]
workflow = json.loads((ROOT / "workflows/kuri-cloudflare-storyboard.json").read_text())
compose = yaml.safe_load((ROOT / "compose.yaml").read_text())

assert workflow["active"] is False, "Workflow must remain inactive until reviewed"
assert workflow["settings"]["timezone"] == "Asia/Manila"
nodes = workflow["nodes"]
names = [node["name"] for node in nodes]
assert len(names) == len(set(names)) == 6
assert len(workflow["connections"]) == len(nodes) - 1
for current, next_node in zip(names, names[1:]):
    target = workflow["connections"][current]["main"][0][0]["node"]
    assert target == next_node, f"Broken edge {current} -> {next_node}"
http = [node for node in nodes if node["type"] == "n8n-nodes-base.httpRequest"]
assert len(http) == 2
assert all(node["parameters"]["authentication"] == "genericCredentialType"
           and node["parameters"]["genericAuthType"] == "httpHeaderAuth"
           and node["parameters"]["method"] == "POST"
           and "credentials" not in node for node in http)
assert "/v1/generate" in http[0]["parameters"]["url"]
assert "/v1/storyboard" in http[1]["parameters"]["url"]
assert not any("youtube" in node["type"].lower() for node in nodes)
for node in nodes:
    if node["type"] == "n8n-nodes-base.code":
        completed = subprocess.run(["node", "--check"], input=node["parameters"]["jsCode"],
                                   text=True, capture_output=True)
        assert completed.returncode == 0, f"{node['name']}: {completed.stderr}"
services = compose["services"]
assert "postgres" in services and "n8n" in services
assert services["n8n"]["ports"] == ["127.0.0.1:5678:5678"]
assert services["n8n"]["environment"]["N8N_BLOCK_ENV_ACCESS_IN_NODE"] == "true"
assert services["n8n"]["environment"]["DB_TYPE"] == "postgresdb"
assert "postgres_data" in compose["volumes"] and "n8n_data" in compose["volumes"]
assert ".env" in (ROOT / ".gitignore").read_text()
assert not (ROOT / ".env").exists(), "Never commit a live .env file"
print("n8n workflow JavaScript, graph, security config and YAML: OK")

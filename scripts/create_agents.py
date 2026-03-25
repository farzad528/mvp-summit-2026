"""
Creates Foundry IQ knowledge sources, knowledge bases, RBAC assignments,
MCP connections, and prompt agents.

Implements the latest Foundry Agent Service v2 pattern:
  Knowledge Source → Knowledge Base → RemoteTool MCP Connection → MCPTool Agent

Prerequisites:
  - Search indexes already created (run setup_indexes.py first)
  - You must be Owner or User Access Administrator to assign RBAC roles

Usage:
  python scripts/create_agents.py

Docs:
  https://learn.microsoft.com/azure/ai-foundry/agents/how-to/foundry-iq-connect
  https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-knowledge-base
"""

import json
import os
import subprocess

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "code", ".env"))

SEARCH_ENDPOINT = os.environ["AZURE_AI_SEARCH_ENDPOINT"]
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
MODEL = os.getenv("MODEL_DEPLOYMENT", "gpt-4.1")
SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY", "")

API_VERSION = "2025-11-01-preview"

# ── Derived values ───────────────────────────────────────────────────────────
# Extract search service name from endpoint for RBAC
_search_host = SEARCH_ENDPOINT.replace("https://", "").rstrip("/")
SEARCH_SERVICE_NAME = _search_host.split(".")[0]


def _az_token(scope: str) -> str:
    """Get a bearer token via `az account get-access-token`."""
    result = subprocess.run(
        ["az", "account", "get-access-token", "--scope", scope, "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _search_headers() -> dict:
    """Headers for Azure AI Search REST calls."""
    if SEARCH_KEY:
        return {"api-key": SEARCH_KEY, "Content-Type": "application/json"}
    token = _az_token("https://search.azure.com/.default")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _mgmt_headers() -> dict:
    token = _az_token("https://management.azure.com/.default")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _foundry_headers() -> dict:
    token = _az_token("https://ai.azure.com/.default")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── Step 1: Knowledge Sources ────────────────────────────────────────────────

KNOWLEDGE_SOURCES = [
    {
        "name": "mvp-summit-ks",
        "description": "MVP Summit 2026 session catalog and campus guide.",
        "kind": "searchIndex",
        "searchIndexParameters": {
            "searchIndexName": "mvp-summit-kb",
            "semanticConfigurationName": "my-semantic-config",
            "sourceDataFields": [{"name": "id"}, {"name": "title"}, {"name": "category"}],
        },
    },
    {
        "name": "contoso-policy-ks",
        "description": "Contoso Insurance claims and returns policy.",
        "kind": "searchIndex",
        "searchIndexParameters": {
            "searchIndexName": "contoso-policy-kb",
            "semanticConfigurationName": "my-semantic-config",
            "sourceDataFields": [{"name": "id"}, {"name": "title"}],
        },
    },
]


def create_knowledge_sources():
    print("\n── Knowledge Sources ──")
    headers = _search_headers()
    for ks in KNOWLEDGE_SOURCES:
        url = f"{SEARCH_ENDPOINT}/knowledgesources/{ks['name']}?api-version={API_VERSION}"
        resp = requests.put(url, headers=headers, json=ks)
        resp.raise_for_status()
        print(f"  ✓ {ks['name']}")


# ── Step 2: Knowledge Bases ──────────────────────────────────────────────────

KNOWLEDGE_BASES = [
    {
        "name": "mvp-summit-knowledge-base",
        "description": "MVP Summit 2026 sessions and campus logistics.",
        "retrievalInstructions": "Use this for questions about MVP Summit sessions, speakers, tracks, campus buildings, cafeterias, shuttle, and logistics.",
        "answerInstructions": "Provide concise answers with specific session names, times, buildings, and room numbers. Cite sources.",
        "outputMode": "answerSynthesis",
        "knowledgeSources": [{"name": "mvp-summit-ks"}],
        "models": [{"kind": "azureOpenAI", "azureOpenAIParameters": {"resourceUri": OPENAI_ENDPOINT.rstrip("/"), "deploymentId": MODEL, "modelName": MODEL}}],
        "retrievalReasoningEffort": {"kind": "low"},
    },
    {
        "name": "contoso-policy-knowledge-base",
        "description": "Contoso Insurance claims and returns policy.",
        "retrievalInstructions": "Use this for questions about return windows, refund calculations, escalation criteria, fraud detection, and special categories.",
        "answerInstructions": "Provide policy-grounded answers citing specific sections. Include actual constraints when generating code.",
        "outputMode": "answerSynthesis",
        "knowledgeSources": [{"name": "contoso-policy-ks"}],
        "models": [{"kind": "azureOpenAI", "azureOpenAIParameters": {"resourceUri": OPENAI_ENDPOINT.rstrip("/"), "deploymentId": MODEL, "modelName": MODEL}}],
        "retrievalReasoningEffort": {"kind": "low"},
    },
]


def create_knowledge_bases():
    print("\n── Knowledge Bases ──")
    headers = _search_headers()
    for kb in KNOWLEDGE_BASES:
        url = f"{SEARCH_ENDPOINT}/knowledgebases/{kb['name']}?api-version={API_VERSION}"
        resp = requests.put(url, headers=headers, json=kb)
        resp.raise_for_status()
        print(f"  ✓ {kb['name']}")


# ── Step 3: RBAC ─────────────────────────────────────────────────────────────

def setup_rbac():
    """Assign required roles. Requires Owner or User Access Administrator."""
    print("\n── RBAC ──")

    # Get resource IDs and managed identity principal IDs
    sub_id = subprocess.run(
        ["az", "account", "show", "--query", "id", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    # Find the search service resource group
    search_rg = subprocess.run(
        ["az", "resource", "list", "--name", SEARCH_SERVICE_NAME, "--query", "[0].resourceGroup", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    # Get search service managed identity
    search_mi = subprocess.run(
        ["az", "search", "service", "show", "--name", SEARCH_SERVICE_NAME, "--resource-group", search_rg,
         "--query", "identity.principalId", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    # Parse the Foundry account and project from PROJECT_ENDPOINT
    # Example: https://acct.services.ai.azure.com/api/projects/proj
    parts = PROJECT_ENDPOINT.replace("https://", "").split("/")
    account_name = parts[0].split(".")[0]
    project_name = parts[-1]

    # Get the Foundry account resource group
    foundry_rg = subprocess.run(
        ["az", "resource", "list", "--name", account_name, "--resource-type", "Microsoft.CognitiveServices/accounts",
         "--query", "[0].resourceGroup", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    # Get project managed identity
    project_mi = subprocess.run(
        ["az", "rest", "--method", "get",
         "--url", f"/subscriptions/{sub_id}/resourceGroups/{foundry_rg}/providers/Microsoft.CognitiveServices/accounts/{account_name}/projects/{project_name}?api-version=2025-06-01",
         "--query", "identity.principalId", "-o", "tsv"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    search_scope = f"/subscriptions/{sub_id}/resourceGroups/{search_rg}/providers/Microsoft.Search/searchServices/{SEARCH_SERVICE_NAME}"
    foundry_scope = f"/subscriptions/{sub_id}/resourceGroups/{foundry_rg}/providers/Microsoft.CognitiveServices/accounts/{account_name}"

    # Search MI → Cognitive Services User on Foundry (for LLM access in KB)
    _assign_role(search_mi, "a97b65f3-24c7-4388-baec-2e87135dc908", foundry_scope, "Search MI → Cognitive Services User")

    # Project MI → Search Index Data Reader on Search (for MCP retrieval)
    _assign_role(project_mi, "1407120a-92aa-4202-b7e9-c0e197c71c8f", search_scope, "Project MI → Search Index Data Reader")

    return sub_id, foundry_rg, account_name, project_name


def _assign_role(principal_id: str, role_id: str, scope: str, label: str):
    try:
        subprocess.run(
            ["az", "role", "assignment", "create",
             "--assignee-object-id", principal_id,
             "--assignee-principal-type", "ServicePrincipal",
             "--role", role_id,
             "--scope", scope],
            capture_output=True, text=True, check=True,
        )
        print(f"  ✓ {label}")
    except subprocess.CalledProcessError:
        print(f"  ⚠ {label} (may already exist)")


# ── Step 4: MCP Connections ──────────────────────────────────────────────────

MCP_CONNECTIONS = [
    {"name": "mvp-summit-kb-mcp", "kb": "mvp-summit-knowledge-base"},
    {"name": "contoso-policy-kb-mcp", "kb": "contoso-policy-knowledge-base"},
]


def create_mcp_connections(sub_id: str, foundry_rg: str, account_name: str, project_name: str):
    print("\n── MCP Connections ──")
    headers = _mgmt_headers()
    project_id = f"/subscriptions/{sub_id}/resourceGroups/{foundry_rg}/providers/Microsoft.CognitiveServices/accounts/{account_name}/projects/{project_name}"

    for conn in MCP_CONNECTIONS:
        mcp_url = f"{SEARCH_ENDPOINT}/knowledgebases/{conn['kb']}/mcp?api-version={API_VERSION}"
        body = {
            "name": conn["name"],
            "properties": {
                "authType": "ProjectManagedIdentity",
                "category": "RemoteTool",
                "target": mcp_url,
                "isSharedToAll": True,
                "audience": "https://search.azure.com/",
                "metadata": {"ApiType": "Azure"},
            },
        }
        url = f"https://management.azure.com{project_id}/connections/{conn['name']}?api-version=2025-10-01-preview"
        resp = requests.put(url, headers=headers, json=body)
        resp.raise_for_status()
        print(f"  ✓ {conn['name']} → {conn['kb']}")


# ── Step 5: Prompt Agents ────────────────────────────────────────────────────

AGENTS = [
    {
        "name": "mvp-summit-concierge",
        "kb": "mvp-summit-knowledge-base",
        "mcp_conn": "mvp-summit-kb-mcp",
        "instructions": (
            "You are an MVP Summit 2026 Concierge Agent.\n\n"
            "Use the knowledge base tool to answer user questions.\n"
            "If the knowledge base doesn't contain the answer, respond with \"I don't know\".\n"
            "When you use information from the knowledge base, include citations.\n\n"
            "Rules:\n"
            "- Cite specific session names, times, buildings, and room numbers\n"
            "- When recommending sessions, explain why based on the attendee's interests\n"
            "- For logistics, reference specific buildings and facilities"
        ),
    },
    {
        "name": "contoso-policy-assistant",
        "kb": "contoso-policy-knowledge-base",
        "mcp_conn": "contoso-policy-kb-mcp",
        "instructions": (
            "You are a developer assistant for Contoso Insurance.\n\n"
            "Use the knowledge base tool to answer user questions.\n"
            "If the knowledge base doesn't contain the answer, respond with \"I don't know\".\n"
            "When you use information from the knowledge base, include citations.\n\n"
            "Rules:\n"
            "- Ground all business rules in the actual policy\n"
            "- Cite specific policy sections when implementing validation logic\n"
            "- If a constraint is ambiguous, flag it rather than assuming\n"
            "- Generate production-quality Python code with proper error handling"
        ),
    },
]


def create_agents():
    print("\n── Prompt Agents ──")
    headers = _foundry_headers()

    for agent in AGENTS:
        mcp_url = f"{SEARCH_ENDPOINT}/knowledgebases/{agent['kb']}/mcp?api-version={API_VERSION}"
        body = {
            "name": agent["name"],
            "definition": {
                "kind": "prompt",
                "model": MODEL,
                "instructions": agent["instructions"],
                "tools": [
                    {
                        "type": "mcp",
                        "server_label": "knowledge-base",
                        "server_url": mcp_url,
                        "require_approval": "never",
                        "allowed_tools": ["knowledge_base_retrieve"],
                        "project_connection_id": agent["mcp_conn"],
                    }
                ],
            },
        }
        url = f"{PROJECT_ENDPOINT}/agents?api-version=v1"
        resp = requests.post(url, headers=headers, json=body)
        resp.raise_for_status()
        print(f"  ✓ {agent['name']}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n═══ Foundry IQ — Full Agent Setup ═══")

    create_knowledge_sources()
    create_knowledge_bases()
    sub_id, foundry_rg, account_name, project_name = setup_rbac()
    create_mcp_connections(sub_id, foundry_rg, account_name, project_name)
    create_agents()

    print("\n═══ Setup Complete ═══")
    print("  Agents ready in Foundry portal playground and via API.")
    print("  Open code/demo_notebook.ipynb to try them.\n")


if __name__ == "__main__":
    main()

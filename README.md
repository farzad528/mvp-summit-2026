# Foundry IQ — One Knowledge Base, Three Surfaces

End-to-end sample showing how a single [Foundry IQ](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/what-is-foundry-iq) knowledge base powers:

1. **Foundry Agent Service** — a prompt agent grounded via MCP
2. **Python code** — the same agent called from a Jupyter notebook
3. **GitHub Copilot CLI** — the KB as dev-time context for code generation

> _"I created one Knowledge Base. It powers my agent in Foundry. It powers my agent in code.
> And it helps my developers write better code. That's Foundry IQ interoperability."_

## Architecture

```
┌─────────────────┐        ┌──────────────────────────┐
│  Azure AI Search │◄──MCP──│  Foundry Agent Service   │
│  (S2, semantic)  │        │  (gpt-4.1, MCPTool)      │
│                  │        └──────────────────────────┘
│  Knowledge Bases │        ┌──────────────────────────┐
│  ├ mvp-summit    │◄──MCP──│  Jupyter notebook        │
│  └ contoso-policy│        │  (AIProjectClient)       │
│                  │        └──────────────────────────┘
│  Knowledge Srcs  │        ┌──────────────────────────┐
│  ├ mvp-summit-ks │        │  GitHub Copilot CLI      │
│  └ contoso-ks    │        │  (KB as context)         │
└─────────────────┘        └──────────────────────────┘
```

## Prerequisites

| Resource | Requirement |
|----------|-------------|
| Azure subscription | With [Azure AI Foundry](https://learn.microsoft.com/azure/ai-foundry/) access |
| Azure AI Search | S1+ with [semantic search enabled](https://learn.microsoft.com/azure/search/semantic-how-to-enable-disable) |
| Azure AI Foundry project | `kind: AIServices` with a deployed LLM (`gpt-4.1` or `gpt-4o`) and `text-embedding-3-large` |
| Python | 3.10+ |

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/<you>/mvp-summit-2026.git
cd mvp-summit-2026
pip install -r code/requirements.txt
az login
```

### 2. Configure

```bash
cp code/.env.sample code/.env
# Edit code/.env with your endpoints and model deployment names
```

### 3. Create search indexes and push data

```bash
python scripts/setup_indexes.py
```

This creates two indexes (`mvp-summit-kb`, `contoso-policy-kb`), generates embeddings with `text-embedding-3-large`, and uploads all documents.

### 4. Create knowledge sources, knowledge bases, and agents

```bash
python scripts/create_agents.py
```

This script:
- Creates [knowledge sources](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-search-index) on your search service
- Creates [knowledge bases](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-knowledge-base) with LLM-powered answer synthesis
- Sets up [RBAC](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/foundry-iq-connect#authentication-and-permissions) (Search MI → Cognitive Services User; Project MI → Search Index Data Reader)
- Creates [RemoteTool MCP connections](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/foundry-iq-connect#create-a-project-connection) on your Foundry project
- Creates two prompt agents with [MCPTool](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/foundry-iq-connect#create-an-agent-with-the-mcp-tool) grounding

### 5. Run the notebook

Open `code/demo_notebook.ipynb` and run the cells.

## Repo Structure

```
├── data/
│   ├── sessions.json              # 33 sessions across 5 tracks
│   ├── campus-guide.json          # Buildings, shuttle, meals, WiFi
│   └── contoso-returns-policy.md  # Insurance policy (7 sections)
├── scripts/
│   ├── setup_indexes.py           # Step 3 — indexes + embeddings
│   └── create_agents.py           # Step 4 — KBs + RBAC + agents
├── code/
│   ├── demo_notebook.ipynb        # Interactive demo notebook
│   ├── demo_codegen.py            # Standalone code-gen demo
│   ├── requirements.txt
│   └── .env.sample
└── README.md
```

## Key Concepts

| Concept | What it is | Docs |
|---------|-----------|------|
| Knowledge Base | Top-level object on Azure AI Search that orchestrates agentic retrieval | [Create a knowledge base](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-knowledge-base) |
| Knowledge Source | Points a KB at a search index with semantic config | [Search index knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-search-index) |
| MCPTool | Connects a Foundry agent to a KB via Model Context Protocol | [Connect KB to Agent Service](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/foundry-iq-connect) |
| RemoteTool connection | Project connection using managed identity for MCP auth | [Project connections](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/foundry-iq-connect#create-a-project-connection) |

## Sample Questions

**MVP Summit Concierge**
- _"What sessions are about RAG?"_
- _"Where should I grab lunch if my afternoon sessions are in Building 33?"_
- _"I'm an ISV building a SaaS app with RAG. Which 3 sessions should I prioritize?"_

**Contoso Policy Assistant**
- _"What is the maximum refund period for defective electronics?"_
- _"When should a claim be auto-escalated to a supervisor?"_
- _"Write a Python function that validates a return claim using the actual policy rules."_

## Related Resources

- [Foundry IQ overview](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/what-is-foundry-iq)
- [Agentic retrieval overview](https://learn.microsoft.com/azure/search/agentic-retrieval-overview)
- [Foundry Agent Service](https://learn.microsoft.com/azure/ai-foundry/agents/overview)
- [Azure AI Projects Python SDK](https://learn.microsoft.com/python/api/overview/azure/ai-projects-readme)
- [agentic-retrieval-pipeline-example (GitHub)](https://github.com/Azure-Samples/azure-search-python-samples/tree/main/agentic-retrieval-pipeline-example)

"""
Contoso Policy — Code Generation Demo
Uses the Foundry Agent Service to generate policy-grounded Python code.

Usage: python code/demo_codegen.py
"""

import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]

credential = DefaultAzureCredential()
project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
openai_client = project_client.get_openai_client()


def ask_policy_agent(question: str) -> str:
    conversation = openai_client.conversations.create()
    response = openai_client.responses.create(
        conversation=conversation.id,
        input=question,
        extra_body={"agent_reference": {"name": "contoso-policy-assistant", "type": "agent_reference"}},
    )
    return response.output_text


if __name__ == "__main__":
    print("=" * 60)
    print("DEMO 1: Generate a claims validation function")
    print("=" * 60)
    print()
    print(ask_policy_agent(
        "Write a Python function called validate_return_claim that takes a claim dict with keys: "
        "purchase_date, claim_date, item_condition, item_price, is_electronic, is_defective, "
        "customer_claim_count_12mo. The function should return a dict with: approved (bool), "
        "refund_percentage (float), needs_escalation (bool), and reason (str). "
        "Use the actual policy rules from the knowledge base."
    ))

    print("\n" + "=" * 60)
    print("DEMO 2: Escalation criteria")
    print("=" * 60)
    print()
    print(ask_policy_agent(
        "According to the policy, when should a claim be auto-escalated to a supervisor? "
        "List all criteria with the specific thresholds."
    ))

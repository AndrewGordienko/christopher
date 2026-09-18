"""Route the sender's current role; never supply a stored biography as fact."""

MODES = {"technical_contract", "technical_work", "wapahki_pilot", "wapahki_investor",
         "factory_learning", "outagehub_acquisition", "outagehub_api", "outagehub",
         "warm_personal", "unknown"}


def normalized(value):
    return str(value or "").casefold().strip().replace("-", "_").replace(" ", "_")


def route_sender_mode(context):
    explicit = context.get("sender_mode")
    if explicit:
        if explicit not in MODES:
            raise ValueError("Unknown sender_mode; resolve the objective instead of inventing a biography")
        return explicit
    objective = normalized(context.get("objective"))
    project = normalized(context.get("project"))
    kind = normalized(context.get("type"))
    if objective in {"personal_reconnection", "personal_reply"} or kind == "warm_relationship":
        return "warm_personal"
    if project == "outagehub":
        if objective in {"acquisition", "strategic_buyer"}:
            return "outagehub_acquisition"
        if objective in {"api_sales", "customer", "sales"}:
            return "outagehub_api"
        return "outagehub"
    if project == "wapahki" and objective in {"investor", "fundraising", "investor_update"}:
        return "wapahki_investor"
    if objective == "research_visit" and (project == "wapahki" or "factory_integrator" in kind):
        return "factory_learning"
    if project == "wapahki" and objective in {"pilot", "design_partner", "customer", "partnership"}:
        return "wapahki_pilot"
    if objective in {"technical_contract", "contract", "research_project", "technical_side_project", "research_collaboration"}:
        return "technical_contract"
    if kind == "technical_research":
        return "technical_work"
    return "unknown"


def select_sender_context(context):
    """Validate Codex's selection of up to three current facts, not their truth.

    No historical identity, fundraising status, employer or availability is added.
    """
    facts = context.get("current_facts", [])
    indices = context.get("sender_fact_indices", [])
    if not isinstance(facts, list) or not isinstance(indices, list) or len(indices) > 3:
        raise ValueError("Select at most three sender facts from current_facts")
    if any(type(i) is not int or i < 0 or i >= len(facts) for i in indices) or len(set(indices)) != len(indices):
        raise ValueError("sender_fact_indices must identify distinct current facts")
    if any(not isinstance(facts[i], str) or not facts[i].strip() for i in indices):
        raise ValueError("Selected sender facts must contain current factual text")
    mode = route_sender_mode(context)
    instruction = "Use only relevant current facts; preserve the task draft's useful meaning. Before composing, express these raw facts at the highest useful abstraction for this recipient, following references/human-compression.md. Keep the concrete reason Andrew is relevant without copying an implementation inventory or becoming generic. This is context, not a mandatory introduction. Do not import an unrelated company, biography or fundraising status."
    if mode == "technical_contract":
        instruction += " For exploratory contract outreach, default to Andrew as an individual: his background, interest and a project he could own. Do not introduce a team merely because one exists. Ownership does not promise sole execution; explain actual collaborators when the recipient asks or the scope calls for them. Do not invent collaborators, capacity or availability. Current instructions and the actual thread prevail."
    return {"mode": mode, "project": context.get("project"),
            "objective": context.get("objective"), "recipient": context.get("recipient"),
            "relationship": context.get("relationship"),
            "identity": [{"text": facts[i], "source": f"current_facts[{i}]"} for i in indices],
            "instruction": instruction}

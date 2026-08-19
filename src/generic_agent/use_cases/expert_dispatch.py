"""Expert dispatch use case: triage and routing to domain specialists."""

from typing import ClassVar, Dict

from ..graphs.router import RouterStrategy
from .base import BaseUseCaseAgent


class ExpertDispatchUseCaseAgent(BaseUseCaseAgent):
    """Triages user requests and routes them dynamically to domain-specific specialist agents."""

    use_case = "expert_dispatch"
    title = "Expert Specialist Dispatcher"
    when_to_use = "When requests span distinct functional areas (e.g. billing, technical support, legal, security)."
    aliases = ("router", "dispatcher", "triage", "specialists")
    strategy = RouterStrategy()
    defaults: ClassVar[Dict] = {
        "specialists": ("billing", "technical", "general"),
    }

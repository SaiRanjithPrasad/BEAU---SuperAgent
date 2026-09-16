def test_actor_config_defaults():
    import beau.core.config as cfg
    assert hasattr(cfg, "TAVILY_API_KEY")
    assert hasattr(cfg, "USE_EMAIL")

def test_prompts_models_importable():
    from beau.tools.actor.prompts import WORKER_PROMPT, EVALUATOR_PROMPT
    assert len(WORKER_PROMPT) > 20
    from beau.tools.actor.models import EvaluatorOutput
    assert EvaluatorOutput.model_fields["is_success"]

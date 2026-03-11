from kernel.graph_fitness import GraphFitnessScorer
from kernel.graph_registry import GraphRegistry
from kernel.graph_planner import GraphPlanner
from kernel.kernel import Kernel
from kernel.llm_graph_planner import LLMGraphPlanner
from kernel.task_graph import TaskGraphRunner
from providers.async_worker_stub import AsyncWorkerStub
from providers.base import BaseProvider
from providers.ollama_provider import OllamaProvider

from hades.graph_fitness import GraphFitnessScorer as HadesGraphFitnessScorer
from hades.graph_planner import GraphPlanner as HadesGraphPlanner
from hades.graph_registry import GraphRegistry as HadesGraphRegistry
from hades.kernel import HadesKernel
from hades.llm_graph_planner import LLMGraphPlanner as HadesLLMGraphPlanner
from hades.task_graph import TaskGraphRunner as HadesTaskGraphRunner


def test_kernel_facades_point_to_existing_runtime() -> None:
    assert Kernel is HadesKernel
    assert GraphPlanner is HadesGraphPlanner
    assert LLMGraphPlanner is HadesLLMGraphPlanner
    assert GraphRegistry is HadesGraphRegistry
    assert GraphFitnessScorer is HadesGraphFitnessScorer
    assert TaskGraphRunner is HadesTaskGraphRunner


def test_provider_exports_have_expected_shape() -> None:
    assert issubclass(OllamaProvider, BaseProvider)


def test_async_worker_stub_round_trip() -> None:
    worker = AsyncWorkerStub()

    submission = worker.submit_job({"intent": "analyse btc funding"})

    assert submission["status"] == "accepted"

    status = worker.job_status(submission["job_id"])
    result = worker.job_result(submission["job_id"])

    assert status["status"] == "completed"
    assert result["status"] == "ok"
    assert result["payload"]["intent"] == "analyse btc funding"

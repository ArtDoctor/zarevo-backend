from worker.worker import ANALYSIS_EXAMPLE_LOADERS


def test_example_loaders_return_valid_responses_for_all_task_types() -> None:
    for task_type, loader in ANALYSIS_EXAMPLE_LOADERS.items():
        result = loader()
        assert result is not None
        assert hasattr(result, "model_dump")
        dumped = result.model_dump()
        assert isinstance(dumped, dict)
        assert len(dumped) > 0

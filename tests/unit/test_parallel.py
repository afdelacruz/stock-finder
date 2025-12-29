"""Unit tests for ParallelExecutor."""

import time
from concurrent.futures import TimeoutError
from unittest.mock import MagicMock

import pytest

from stock_finder.utils.parallel import ParallelExecutor, TaskResult


class TestParallelExecutor:
    """Tests for ParallelExecutor class."""

    def test_init_default_workers(self):
        """Test default worker count."""
        executor = ParallelExecutor()
        assert executor.max_workers == 10

    def test_init_custom_workers(self):
        """Test custom worker count."""
        executor = ParallelExecutor(max_workers=5)
        assert executor.max_workers == 5

    def test_execute_single_item(self):
        """Test executing a single item."""
        executor = ParallelExecutor(max_workers=2)

        def process(x):
            return x * 2

        results = executor.execute(process, [5])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result == 10
        assert results[0].item == 5
        assert results[0].error is None

    def test_execute_multiple_items(self):
        """Test executing multiple items."""
        executor = ParallelExecutor(max_workers=4)

        def process(x):
            return x ** 2

        items = [1, 2, 3, 4, 5]
        results = executor.execute(process, items)

        assert len(results) == 5
        # Results should be in order
        assert [r.result for r in results] == [1, 4, 9, 16, 25]
        assert all(r.success for r in results)

    def test_execute_preserves_order(self):
        """Test that results are returned in original order."""
        executor = ParallelExecutor(max_workers=4)

        def process(x):
            # Add variable delay to test ordering
            time.sleep(0.01 * (5 - x))  # Higher numbers finish faster
            return x

        items = [1, 2, 3, 4, 5]
        results = executor.execute(process, items)

        # Despite different completion times, results should be in order
        assert [r.item for r in results] == [1, 2, 3, 4, 5]
        assert [r.result for r in results] == [1, 2, 3, 4, 5]

    def test_execute_handles_errors(self):
        """Test that errors in individual items don't crash the batch."""
        executor = ParallelExecutor(max_workers=2)

        def process(x):
            if x == 3:
                raise ValueError("Error on item 3")
            return x * 2

        items = [1, 2, 3, 4, 5]
        results = executor.execute(process, items)

        assert len(results) == 5
        # Items 1, 2, 4, 5 should succeed
        assert results[0].success is True
        assert results[0].result == 2
        assert results[1].success is True
        assert results[1].result == 4
        # Item 3 should fail
        assert results[2].success is False
        assert results[2].result is None
        assert "Error on item 3" in str(results[2].error)
        # Items 4, 5 should succeed
        assert results[3].success is True
        assert results[3].result == 8
        assert results[4].success is True
        assert results[4].result == 10

    def test_execute_with_progress_callback(self):
        """Test progress callback is called for each item."""
        executor = ParallelExecutor(max_workers=2)
        progress_calls = []

        def on_progress(completed, total, item, result):
            progress_calls.append((completed, total, item, result))

        def process(x):
            return x * 2

        items = [1, 2, 3]
        executor.execute(process, items, on_progress=on_progress)

        assert len(progress_calls) == 3
        # All items should have been reported
        items_reported = {call[2] for call in progress_calls}
        assert items_reported == {1, 2, 3}

    def test_execute_empty_list(self):
        """Test executing with empty list."""
        executor = ParallelExecutor(max_workers=2)

        def process(x):
            return x * 2

        results = executor.execute(process, [])

        assert results == []

    def test_execute_with_on_result_callback(self):
        """Test on_result callback for incremental processing."""
        executor = ParallelExecutor(max_workers=2)
        results_received = []

        def on_result(task_result):
            results_received.append(task_result)

        def process(x):
            return x * 2

        items = [1, 2, 3, 4]
        executor.execute(process, items, on_result=on_result)

        assert len(results_received) == 4
        # All results should be successful
        assert all(r.success for r in results_received)

    def test_successful_results_only(self):
        """Test filtering for successful results only."""
        executor = ParallelExecutor(max_workers=2)

        def process(x):
            if x % 2 == 0:
                raise ValueError("Even number")
            return x

        items = [1, 2, 3, 4, 5]
        results = executor.execute(process, items)

        successful = [r for r in results if r.success]
        assert len(successful) == 3
        assert [r.result for r in successful] == [1, 3, 5]


class TestParallelExecutorPerformance:
    """Performance tests for ParallelExecutor."""

    def test_parallel_faster_than_sequential(self):
        """Test that parallel execution is faster than sequential."""
        executor = ParallelExecutor(max_workers=4)

        def slow_process(x):
            time.sleep(0.05)  # 50ms per item
            return x

        items = list(range(8))  # 8 items

        # Parallel execution
        start = time.time()
        executor.execute(slow_process, items)
        parallel_time = time.time() - start

        # Sequential would take 8 * 0.05 = 0.4s
        # Parallel with 4 workers should take ~0.1s (2 batches)
        # Allow some overhead, but should be significantly faster
        assert parallel_time < 0.3  # At least 25% faster than sequential


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_task_result_success(self):
        """Test successful TaskResult."""
        result = TaskResult(
            item="AAPL",
            success=True,
            result={"price": 150.0},
            error=None,
        )
        assert result.item == "AAPL"
        assert result.success is True
        assert result.result == {"price": 150.0}
        assert result.error is None

    def test_task_result_failure(self):
        """Test failed TaskResult."""
        result = TaskResult(
            item="INVALID",
            success=False,
            result=None,
            error="Ticker not found",
        )
        assert result.item == "INVALID"
        assert result.success is False
        assert result.result is None
        assert result.error == "Ticker not found"


class TestParallelExecutorMap:
    """Tests for map-style execution."""

    def test_map_returns_results_directly(self):
        """Test map method returns results directly."""
        executor = ParallelExecutor(max_workers=2)

        def process(x):
            return x * 2

        results = executor.map(process, [1, 2, 3, 4])

        # map should return just the results (not TaskResult objects)
        assert results == [2, 4, 6, 8]

    def test_map_with_errors_returns_none(self):
        """Test map with errors returns None for failed items."""
        executor = ParallelExecutor(max_workers=2)

        def process(x):
            if x == 2:
                raise ValueError("Error")
            return x * 2

        results = executor.map(process, [1, 2, 3])

        assert results == [2, None, 6]

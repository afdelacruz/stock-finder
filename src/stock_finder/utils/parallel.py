"""Parallel execution utilities for batch operations."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class TaskResult:
    """Result of a parallel task execution."""

    item: Any
    success: bool
    result: Any | None
    error: str | None


class ParallelExecutor:
    """
    Execute tasks in parallel using a thread pool.

    Uses ThreadPoolExecutor for I/O-bound operations like API calls.
    Handles errors gracefully - failed items don't crash the batch.
    """

    def __init__(self, max_workers: int = 10):
        """
        Initialize the parallel executor.

        Args:
            max_workers: Maximum number of concurrent workers (default: 10)
        """
        self.max_workers = max_workers

    def execute(
        self,
        func: Callable[[T], R],
        items: list[T],
        on_progress: Callable[[int, int, T, TaskResult], None] | None = None,
        on_result: Callable[[TaskResult], None] | None = None,
    ) -> list[TaskResult]:
        """
        Execute a function on each item in parallel.

        Args:
            func: Function to execute on each item
            items: List of items to process
            on_progress: Optional callback(completed, total, item, result)
            on_result: Optional callback(task_result) for incremental processing

        Returns:
            List of TaskResult objects in the same order as input items
        """
        if not items:
            return []

        total = len(items)
        # Track results by index to preserve order
        results: dict[int, TaskResult] = {}
        completed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks with their indices
            future_to_index = {
                executor.submit(self._execute_single, func, item): (i, item)
                for i, item in enumerate(items)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index, item = future_to_index[future]
                task_result = future.result()
                results[index] = task_result
                completed_count += 1

                # Call callbacks
                if on_result:
                    on_result(task_result)
                if on_progress:
                    on_progress(completed_count, total, item, task_result)

        # Return results in original order
        return [results[i] for i in range(len(items))]

    def _execute_single(self, func: Callable[[T], R], item: T) -> TaskResult:
        """
        Execute a function on a single item with error handling.

        Args:
            func: Function to execute
            item: Item to process

        Returns:
            TaskResult with success/failure info
        """
        try:
            result = func(item)
            return TaskResult(
                item=item,
                success=True,
                result=result,
                error=None,
            )
        except Exception as e:
            logger.debug(f"Error processing {item}: {e}")
            return TaskResult(
                item=item,
                success=False,
                result=None,
                error=str(e),
            )

    def map(
        self,
        func: Callable[[T], R],
        items: list[T],
    ) -> list[R | None]:
        """
        Map a function over items in parallel, returning results directly.

        Similar to built-in map(), but parallel. Failed items return None.

        Args:
            func: Function to execute on each item
            items: List of items to process

        Returns:
            List of results (or None for failed items) in input order
        """
        task_results = self.execute(func, items)
        return [r.result if r.success else None for r in task_results]

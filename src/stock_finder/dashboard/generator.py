"""Dashboard generator - creates static HTML from research data."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from stock_finder.data.database import Database
from stock_finder.dashboard.components import (
    get_summary_data,
    get_setup_quality_data,
    get_theme_data,
    get_watchlist_data,
)


class DashboardGenerator:
    """
    Generate static HTML dashboard from research findings.

    Usage:
        generator = DashboardGenerator()
        generator.generate("output/dashboard.html")
    """

    def __init__(self, db_path: Path | str = "data/stock_finder.db"):
        self.db = Database(db_path)

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
        )

    def generate(
        self,
        output_path: str = "output/dashboard.html",
        run_id: str | None = None,
    ) -> Path:
        """
        Generate the dashboard HTML file.

        Args:
            output_path: Where to save the HTML file
            run_id: Specific research run to use (latest if not provided)

        Returns:
            Path to the generated file
        """
        # Determine run_id
        if run_id is None:
            runs = self.db.get_research_runs(limit=1)
            if runs:
                run_id = runs[0]["id"]

        # Gather data from all components
        data = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "run_id": run_id,
            "data_range": "Dec 2018 - Dec 2025",  # TODO: Get from research run
            "summary": get_summary_data(self.db),
            "setup_quality": get_setup_quality_data(self.db),
            "themes": get_theme_data(self.db),
            "watchlist": get_watchlist_data(self.db),
        }

        # Render template
        template = self.env.get_template("dashboard.html")
        html = template.render(**data)

        # Write output
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html)

        return output

    def get_available_runs(self, limit: int = 10) -> list[dict]:
        """Get available research runs."""
        return self.db.get_research_runs(limit=limit)

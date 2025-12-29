"""Command-line interface for stock finder."""

from pathlib import Path

import click
from rich.console import Console

from stock_finder import __version__
from stock_finder.config import get_settings, load_settings
from stock_finder.data.ticker_source import (
    get_default_tickers,
    load_tickers_from_csv,
    load_tickers_from_list,
)
from stock_finder.data.nasdaq_ftp import (
    get_all_us_tickers,
    get_nasdaq_tickers,
    get_nyse_tickers,
)
from stock_finder.data.yfinance_provider import YFinanceProvider
from stock_finder.data.fmp_provider import FMPProvider
from stock_finder.data.database import Database
from stock_finder.data.cache import CacheManager
from stock_finder.data.cached_provider import CachedDataProvider
from stock_finder.output.formatters import format_as_csv, format_as_json, format_as_table, save_results
from stock_finder.scanners.gainer_scanner import GainerScanner
from stock_finder.utils.logging import setup_logging

console = Console()


def create_data_provider(settings, provider_choice: str | None, no_cache: bool = False):
    """
    Create a data provider with optional caching.

    Args:
        settings: Application settings
        provider_choice: Provider to use ('fmp' or 'yfinance')
        no_cache: If True, disable caching

    Returns:
        Tuple of (data_provider, provider_name)
    """
    provider_name = provider_choice or settings.default_provider

    # Create base provider
    if provider_name == "fmp":
        try:
            base_provider = FMPProvider(settings.fmp)
            console.print("[cyan]Using FMP data provider[/cyan]")
        except ValueError as e:
            console.print(f"[yellow]FMP unavailable ({e}), falling back to yfinance[/yellow]")
            base_provider = YFinanceProvider(settings.data)
            provider_name = "yfinance"
    else:
        base_provider = YFinanceProvider(settings.data)
        console.print("[cyan]Using yfinance data provider[/cyan]")

    # Wrap with caching if enabled
    cache_config = settings.data.cache
    if cache_config.enabled and not no_cache:
        cache_manager = CacheManager(cache_config)
        data_provider = CachedDataProvider(base_provider, cache_manager)
        console.print(f"[dim]Cache: enabled ({cache_config.cache_dir})[/dim]")
    else:
        data_provider = base_provider
        if no_cache:
            console.print("[dim]Cache: disabled (--no-cache)[/dim]")
        else:
            console.print("[dim]Cache: disabled[/dim]")

    return data_provider, provider_name


@click.group()
@click.version_option(version=__version__)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: str | None) -> None:
    """Stock Finder - Scan for high-momentum stocks."""
    ctx.ensure_object(dict)

    # Load settings
    settings = load_settings(config) if config else get_settings()
    ctx.obj["settings"] = settings

    # Setup logging
    log_level = "DEBUG" if verbose else settings.logging.level
    setup_logging(log_level)


@cli.command()
@click.option(
    "--min-gain",
    type=float,
    default=None,
    help="Minimum gain percentage (default: from config)",
)
@click.option(
    "--years",
    type=int,
    default=None,
    help="Years to look back (default: from config)",
)
@click.option(
    "--universe",
    type=str,
    help="Ticker universe: 'nasdaq', 'nyse', 'all', or path to CSV file",
)
@click.option(
    "--tickers",
    type=str,
    help="Comma-separated list of tickers to scan",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of tickers to scan (for testing)",
)
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "csv", "json"]),
    default="table",
    help="Output format",
)
@click.option(
    "--save",
    is_flag=True,
    help="Save results to file",
)
@click.option(
    "--save-dir",
    type=click.Path(),
    default=None,
    help="Directory to save results (default: from config)",
)
@click.option(
    "--db",
    "use_db",
    is_flag=True,
    help="Save results to SQLite database (incremental, survives crashes)",
)
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to database file (default: data/stock_finder.db)",
)
@click.option(
    "--provider",
    type=click.Choice(["fmp", "yfinance"]),
    default=None,
    help="Data provider to use (default: fmp, falls back to yfinance if FMP unavailable)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Bypass cache and fetch fresh data",
)
@click.option(
    "--workers",
    type=int,
    default=None,
    help="Number of parallel workers (default: 10, use 1 for sequential)",
)
@click.pass_context
def scan(
    ctx: click.Context,
    min_gain: float | None,
    years: int | None,
    universe: str | None,
    tickers: str | None,
    limit: int | None,
    output_format: str,
    save: bool,
    save_dir: str | None,
    use_db: bool,
    db_path: str | None,
    provider: str | None,
    no_cache: bool,
    workers: int | None,
) -> None:
    """Scan stocks for significant gains."""
    settings = ctx.obj["settings"]

    # Override config with CLI options
    scan_config = settings.scan.model_copy()
    if min_gain is not None:
        scan_config.min_gain_pct = min_gain
    if years is not None:
        scan_config.lookback_years = years

    # Determine ticker list
    if tickers:
        ticker_list = load_tickers_from_list(tickers.split(","))
    elif universe:
        universe_lower = universe.lower()
        if universe_lower == "nasdaq":
            console.print("[cyan]Fetching NASDAQ tickers...[/cyan]")
            ticker_list = get_nasdaq_tickers()
        elif universe_lower == "nyse":
            console.print("[cyan]Fetching NYSE tickers...[/cyan]")
            ticker_list = get_nyse_tickers()
        elif universe_lower == "all":
            console.print("[cyan]Fetching all US tickers...[/cyan]")
            ticker_list = get_all_us_tickers()
        else:
            # Assume it's a file path
            ticker_list = load_tickers_from_csv(universe)
    else:
        console.print("[yellow]No tickers specified, using default test set[/yellow]")
        ticker_list = get_default_tickers()

    if not ticker_list:
        console.print("[red]No tickers to scan[/red]")
        return

    # Apply limit if specified
    if limit and limit < len(ticker_list):
        console.print(f"[yellow]Limiting to first {limit} tickers[/yellow]")
        ticker_list = ticker_list[:limit]

    console.print(f"Scanning {len(ticker_list)} tickers for {scan_config.min_gain_pct}%+ gains over {scan_config.lookback_years} years...")

    # Create data provider with caching
    data_provider, _ = create_data_provider(settings, provider, no_cache)

    # Configure parallel processing
    parallel_config = settings.parallel.model_copy()
    if workers is not None:
        parallel_config.max_workers = workers
        parallel_config.enabled = workers > 1

    if parallel_config.enabled:
        console.print(f"[dim]Parallel: {parallel_config.max_workers} workers[/dim]")
    else:
        console.print("[dim]Parallel: disabled (sequential)[/dim]")

    scanner = GainerScanner(data_provider, scan_config, parallel_config)

    # Setup database if requested
    db = None
    scan_run_id = None
    if use_db:
        db = Database(db_path) if db_path else Database()
        scan_run_id = db.start_scan_run(
            min_gain_pct=scan_config.min_gain_pct,
            lookback_years=scan_config.lookback_years,
            universe=universe or "custom",
            ticker_count=len(ticker_list),
        )
        console.print(f"[cyan]Saving to database: {db.db_path} (run #{scan_run_id})[/cyan]")

        # Callback to save each result incrementally
        def on_result(result):
            db.add_result(scan_run_id, result)

        results = scanner.scan(ticker_list, show_progress=True, on_result=on_result)
        db.complete_scan_run(scan_run_id)
    else:
        results = scanner.scan(ticker_list, show_progress=True)

    if not results:
        console.print("[yellow]No stocks found meeting criteria[/yellow]")
        return

    # Output results
    if output_format == "table":
        console.print(format_as_table(results))
    elif output_format == "csv":
        click.echo(format_as_csv(results))
    elif output_format == "json":
        click.echo(format_as_json(results))

    # Save to CSV if requested
    if save:
        save_directory = Path(save_dir) if save_dir else Path(settings.output.save_dir)
        file_format = "csv" if output_format == "table" else output_format
        saved_path = save_results(results, save_directory, file_format)
        console.print(f"[green]Results saved to: {saved_path}[/green]")

    # Show database summary
    if use_db and db:
        console.print(f"[green]Results saved to database: {db.db_path}[/green]")
        console.print(f"[green]Scan run ID: {scan_run_id} | Total results: {len(results)}[/green]")


@cli.command()
@click.argument("ticker")
@click.option(
    "--years",
    type=int,
    default=3,
    help="Years to look back",
)
@click.option(
    "--provider",
    type=click.Choice(["fmp", "yfinance"]),
    default=None,
    help="Data provider to use",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Bypass cache and fetch fresh data",
)
@click.pass_context
def check(ctx: click.Context, ticker: str, years: int, provider: str | None, no_cache: bool) -> None:
    """Check a single ticker for gains."""
    settings = ctx.obj["settings"]

    scan_config = settings.scan.model_copy()
    scan_config.lookback_years = years
    scan_config.min_gain_pct = 0  # Show any gain

    # Create data provider with caching
    data_provider, _ = create_data_provider(settings, provider, no_cache)

    scanner = GainerScanner(data_provider, scan_config)

    console.print(f"Checking {ticker.upper()} over {years} years...")

    result = scanner.scan_single(ticker.upper())

    if result:
        console.print(f"\n[green]Max gain found:[/green]")
        console.print(f"  Gain: [cyan]{result.gain_pct:,.1f}%[/cyan]")
        console.print(f"  Low:  ${result.low_price:,.2f} on {result.low_date}")
        console.print(f"  High: ${result.high_price:,.2f} on {result.high_date}")
        console.print(f"  Current: ${result.current_price:,.2f}")
        console.print(f"  Days to peak: {result.days_to_peak}")
    else:
        console.print("[yellow]No significant gain found[/yellow]")


@cli.command()
@click.option(
    "--db-path",
    type=click.Path(exists=True),
    default=None,
    help="Path to database file (default: data/stock_finder.db)",
)
@click.option(
    "--run-id",
    type=int,
    default=None,
    help="Show results from specific scan run",
)
@click.option(
    "--top",
    type=int,
    default=50,
    help="Number of top gainers to show",
)
@click.option(
    "--min-gain",
    type=float,
    default=None,
    help="Filter by minimum gain percentage",
)
@click.option(
    "--runs",
    is_flag=True,
    help="List all scan runs",
)
def results(
    db_path: str | None,
    run_id: int | None,
    top: int,
    min_gain: float | None,
    runs: bool,
) -> None:
    """Query results from the database."""
    db = Database(db_path) if db_path else Database()

    if runs:
        # Show all scan runs
        scan_runs = db.get_all_scan_runs()
        if not scan_runs:
            console.print("[yellow]No scan runs found[/yellow]")
            return

        console.print("\n[bold]Scan Runs:[/bold]")
        for run in scan_runs:
            status_color = "green" if run["status"] == "completed" else "yellow"
            console.print(
                f"  #{run['id']}: {run['started_at']} | "
                f"[{status_color}]{run['status']}[/{status_color}] | "
                f"{run['results_count']} results | "
                f"{run['min_gain_pct']}%+ over {run['lookback_years']}y | "
                f"universe: {run['universe']}"
            )
        return

    # Get results
    if run_id:
        results_list = db.get_results(scan_run_id=run_id, min_gain=min_gain, limit=top)
        console.print(f"\n[bold]Results from scan run #{run_id}:[/bold]")
    else:
        results_list = db.get_top_gainers(limit=top)
        console.print(f"\n[bold]Top {top} gainers (all scans):[/bold]")

    if not results_list:
        console.print("[yellow]No results found[/yellow]")
        return

    # Format as table
    from rich.table import Table
    table = Table()
    table.add_column("Ticker", style="cyan")
    table.add_column("Gain %", justify="right", style="green")
    table.add_column("Low", justify="right")
    table.add_column("Low Date")
    table.add_column("High", justify="right")
    table.add_column("High Date")
    table.add_column("Current", justify="right")

    for r in results_list:
        table.add_row(
            r["ticker"],
            f"{r['gain_pct']:,.1f}%",
            f"${r['low_price']:.2f}",
            str(r["low_date"]),
            f"${r['high_price']:.2f}",
            str(r["high_date"]),
            f"${r['current_price']:.2f}",
        )

    console.print(table)


@cli.command()
@click.argument("csv_file", type=click.Path(exists=True))
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to database file (default: data/stock_finder.db)",
)
@click.option(
    "--min-gain",
    type=float,
    default=500.0,
    help="Min gain % used in the scan (for metadata)",
)
@click.option(
    "--years",
    type=int,
    default=7,
    help="Lookback years used in the scan (for metadata)",
)
@click.option(
    "--universe",
    type=str,
    default="imported",
    help="Universe name (for metadata)",
)
def import_csv(
    csv_file: str,
    db_path: str | None,
    min_gain: float,
    years: int,
    universe: str,
) -> None:
    """Import results from a CSV file into the database."""
    import csv
    from stock_finder.models.results import ScanResult

    db = Database(db_path) if db_path else Database()

    # Read CSV
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        console.print("[yellow]No data in CSV file[/yellow]")
        return

    console.print(f"[cyan]Importing {len(rows)} results from {csv_file}...[/cyan]")

    # Create scan run
    scan_run_id = db.start_scan_run(
        min_gain_pct=min_gain,
        lookback_years=years,
        universe=universe,
        ticker_count=len(rows),
    )

    # Import each row
    imported = 0
    for row in rows:
        try:
            result = ScanResult(
                ticker=row["ticker"],
                gain_pct=float(row["gain_pct"].replace(",", "").replace("%", "")),
                low_price=float(row["low_price"].replace("$", "").replace(",", "")),
                low_date=row["low_date"],
                high_price=float(row["high_price"].replace("$", "").replace(",", "")),
                high_date=row["high_date"],
                current_price=float(row["current_price"].replace("$", "").replace(",", "")),
                days_to_peak=int(row["days_to_peak"]),
            )
            db.add_result(scan_run_id, result)
            imported += 1
        except Exception as e:
            console.print(f"[red]Error importing {row.get('ticker', 'unknown')}: {e}[/red]")

    db.complete_scan_run(scan_run_id)

    console.print(f"[green]Imported {imported} results to database[/green]")
    console.print(f"[green]Database: {db.db_path} | Scan run ID: {scan_run_id}[/green]")


# =============================================================================
# Neumann Scoring Commands
# =============================================================================


@cli.group()
def neumann() -> None:
    """Neumann scoring commands - score stocks against Neumann's criteria."""
    pass


@neumann.command()
@click.option(
    "--scan-run-id",
    type=int,
    required=True,
    help="Scan run ID to score",
)
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to database file (default: data/stock_finder.db)",
)
@click.option(
    "--provider",
    type=click.Choice(["fmp", "yfinance"]),
    default="fmp",
    help="Data provider to use",
)
@click.option(
    "--save/--no-save",
    default=True,
    help="Save results to database",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of stocks to score (for testing)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Bypass cache and fetch fresh data",
)
@click.option(
    "--workers",
    type=int,
    default=None,
    help="Number of parallel workers (default: 10, use 1 for sequential)",
)
@click.pass_context
def score(
    ctx: click.Context,
    scan_run_id: int,
    db_path: str | None,
    provider: str,
    save: bool,
    limit: int | None,
    no_cache: bool,
    workers: int | None,
) -> None:
    """Score stocks from a scan run against Neumann's criteria."""
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

    from stock_finder.scoring.scorer import NeumannScorer

    settings = ctx.obj["settings"]
    db = Database(db_path) if db_path else Database()

    # Get scan run info
    scan_run = db.get_scan_run(scan_run_id)
    if not scan_run:
        console.print(f"[red]Scan run #{scan_run_id} not found[/red]")
        return

    console.print(f"[cyan]Scoring scan run #{scan_run_id}[/cyan]")
    console.print(f"  Results: {scan_run['results_count']}")
    console.print(f"  Universe: {scan_run['universe']}")

    # Create data provider with caching
    data_provider, _ = create_data_provider(settings, provider, no_cache)

    # Configure parallel processing
    parallel_config = settings.parallel.model_copy()
    if workers is not None:
        parallel_config.max_workers = workers
        parallel_config.enabled = workers > 1

    if parallel_config.enabled:
        console.print(f"[dim]Parallel: {parallel_config.max_workers} workers[/dim]")
    else:
        console.print("[dim]Parallel: disabled (sequential)[/dim]")

    # Create scorer
    scorer = NeumannScorer(provider=data_provider, db=db, parallel_config=parallel_config)

    # Get results to score
    scan_results = db.get_results(scan_run_id=scan_run_id)
    if limit:
        scan_results = scan_results[:limit]
        console.print(f"[yellow]Limited to first {limit} stocks[/yellow]")

    # Score with progress bar
    scores = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scoring stocks...", total=len(scan_results))

        for result in scan_results:
            try:
                score_result = scorer.score_stock(result)
                scores.append(score_result)

                if save:
                    db.add_neumann_score(score_result)

                progress.update(
                    task,
                    advance=1,
                    description=f"Scoring {result['ticker']}... (score: {score_result.score})",
                )
            except Exception as e:
                console.print(f"[red]Error scoring {result['ticker']}: {e}[/red]")
                progress.update(task, advance=1)

    # Show summary
    if scores:
        avg_score = sum(s.score for s in scores) / len(scores)
        console.print()
        console.print(f"[green]Scoring complete![/green]")
        console.print(f"  Scored: {len(scores)} stocks")
        console.print(f"  Average score: {avg_score:.2f} / 8")

        # Score distribution
        from collections import Counter
        dist = Counter(s.score for s in scores)
        console.print("  Distribution:")
        for score_val in sorted(dist.keys(), reverse=True):
            console.print(f"    Score {score_val}: {dist[score_val]} stocks")


@neumann.command()
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to database file",
)
def report(db_path: str | None) -> None:
    """Generate a report of Neumann scoring results."""
    from stock_finder.scoring.report import generate_report, print_report

    db = Database(db_path) if db_path else Database()

    # Check if we have any scores
    scores = db.get_neumann_scores(limit=1)
    if not scores:
        console.print("[yellow]No Neumann scores found. Run 'stock-finder neumann score' first.[/yellow]")
        return

    report_data = generate_report(db)
    print_report(report_data, console)


@neumann.command("results")
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to database file",
)
@click.option(
    "--min-score",
    type=int,
    default=None,
    help="Filter by minimum score",
)
@click.option(
    "--top",
    type=int,
    default=50,
    help="Number of results to show",
)
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "csv", "json"]),
    default="table",
    help="Output format",
)
def neumann_results(
    db_path: str | None,
    min_score: int | None,
    top: int,
    output_format: str,
) -> None:
    """View Neumann scoring results."""
    from rich.table import Table
    import json as json_module

    db = Database(db_path) if db_path else Database()

    scores = db.get_neumann_scores(min_score=min_score, limit=top)

    if not scores:
        console.print("[yellow]No scores found[/yellow]")
        return

    if output_format == "json":
        # Remove criteria_json (it's duplicated in criteria_results)
        for s in scores:
            s.pop("criteria_json", None)
        click.echo(json_module.dumps(scores, indent=2, default=str))
        return

    if output_format == "csv":
        import csv
        import sys
        writer = csv.writer(sys.stdout)
        writer.writerow(["ticker", "score", "gain_pct", "days_to_peak", "drawdown", "market_cap"])
        for s in scores:
            writer.writerow([
                s["ticker"],
                s["score"],
                s.get("gain_pct", ""),
                s.get("days_to_peak", ""),
                s.get("drawdown", ""),
                s.get("market_cap_estimate", ""),
            ])
        return

    # Table format
    table = Table(title=f"Neumann Scores (top {len(scores)})")
    table.add_column("Ticker", style="cyan")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Gain %", justify="right")
    table.add_column("Days", justify="right")
    table.add_column("Drawdown", justify="right")
    table.add_column("Mkt Cap", justify="right")

    for s in scores:
        drawdown = s.get("drawdown")
        drawdown_str = f"{drawdown*100:.0f}%" if drawdown else "-"

        mkt_cap = s.get("market_cap_estimate")
        if mkt_cap:
            if mkt_cap >= 1_000_000_000:
                mkt_cap_str = f"${mkt_cap/1_000_000_000:.1f}B"
            else:
                mkt_cap_str = f"${mkt_cap/1_000_000:.0f}M"
        else:
            mkt_cap_str = "-"

        table.add_row(
            s["ticker"],
            str(s["score"]),
            f"{s.get('gain_pct', 0):,.0f}%",
            str(s.get("days_to_peak", "-")),
            drawdown_str,
            mkt_cap_str,
        )

    console.print(table)


# =============================================================================
# Trendline Analysis Commands
# =============================================================================


@cli.group()
def trendline() -> None:
    """Trendline analysis commands - analyze post-ignition price structure."""
    pass


@trendline.command()
@click.option(
    "--scan-run-id",
    type=int,
    required=True,
    help="Scan run ID to analyze",
)
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to database file (default: data/stock_finder.db)",
)
@click.option(
    "--provider",
    type=click.Choice(["fmp", "yfinance"]),
    default="fmp",
    help="Data provider to use",
)
@click.option(
    "--timeframe",
    type=click.Choice(["daily", "weekly", "both"]),
    default="daily",
    help="Timeframe for analysis",
)
@click.option(
    "--save/--no-save",
    default=True,
    help="Save results to database",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of stocks to analyze (for testing)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Bypass cache and fetch fresh data",
)
@click.option(
    "--workers",
    type=int,
    default=None,
    help="Number of parallel workers (default: 10, use 1 for sequential)",
)
@click.pass_context
def analyze(
    ctx: click.Context,
    scan_run_id: int,
    db_path: str | None,
    provider: str,
    timeframe: str,
    save: bool,
    limit: int | None,
    no_cache: bool,
    workers: int | None,
) -> None:
    """Analyze trendlines for stocks from a scan run."""
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

    from stock_finder.analysis.analyzer import TrendlineAnalyzer
    from stock_finder.analysis.models import TrendlineConfig

    settings = ctx.obj["settings"]
    db = Database(db_path) if db_path else Database()

    # Get scan run info
    scan_run = db.get_scan_run(scan_run_id)
    if not scan_run:
        console.print(f"[red]Scan run #{scan_run_id} not found[/red]")
        return

    console.print(f"[cyan]Analyzing trendlines for scan run #{scan_run_id}[/cyan]")
    console.print(f"  Results: {scan_run['results_count']}")
    console.print(f"  Timeframe: {timeframe}")

    # Create data provider with caching
    data_provider, _ = create_data_provider(settings, provider, no_cache)

    # Configure parallel processing
    parallel_config = settings.parallel.model_copy()
    if workers is not None:
        parallel_config.max_workers = workers
        parallel_config.enabled = workers > 1

    if parallel_config.enabled:
        console.print(f"[dim]Parallel: {parallel_config.max_workers} workers[/dim]")
    else:
        console.print("[dim]Parallel: disabled (sequential)[/dim]")

    # Create analyzer
    config = TrendlineConfig()
    analyzer = TrendlineAnalyzer(provider=data_provider, db=db, config=config, parallel_config=parallel_config)

    # Get results to analyze
    scan_results = db.get_results(scan_run_id=scan_run_id)
    if limit:
        scan_results = scan_results[:limit]
        console.print(f"[yellow]Limited to first {limit} stocks[/yellow]")

    # Analyze with progress bar
    analyses = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing trendlines...", total=len(scan_results))

        for result in scan_results:
            try:
                if timeframe == "both":
                    daily = analyzer.analyze_stock(result, "daily", save=save)
                    weekly = analyzer.analyze_stock(result, "weekly", save=save)
                    analyses.extend([daily, weekly])
                else:
                    analysis = analyzer.analyze_stock(result, timeframe, save=save)
                    analyses.append(analysis)

                progress.update(
                    task,
                    advance=1,
                    description=f"Analyzing {result['ticker']}...",
                )
            except Exception as e:
                console.print(f"[red]Error analyzing {result['ticker']}: {e}[/red]")
                progress.update(task, advance=1)

    # Show summary
    formed = sum(1 for a in analyses if a.trendline_formed)
    console.print()
    console.print(f"[green]Analysis complete![/green]")
    console.print(f"  Analyzed: {len(scan_results)} stocks")
    console.print(f"  Trendlines formed: {formed} ({formed/len(analyses)*100:.1f}%)" if analyses else "")


@trendline.command()
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to database file",
)
@click.option(
    "--timeframe",
    type=click.Choice(["daily", "weekly"]),
    default=None,
    help="Filter by timeframe",
)
def report(db_path: str | None, timeframe: str | None) -> None:
    """Generate a report of trendline analysis results."""
    from rich.table import Table

    db = Database(db_path) if db_path else Database()

    stats = db.get_trendline_stats(timeframe=timeframe)

    if stats["total"] == 0:
        console.print("[yellow]No trendline analyses found. Run 'stock-finder trendline analyze' first.[/yellow]")
        return

    console.print()
    console.print("[bold]Trendline Analysis Report[/bold]")
    console.print("=" * 50)

    # Formation stats
    console.print()
    console.print("[bold cyan]Formation Statistics:[/bold cyan]")
    console.print(f"  Total analyzed: {stats['total']}")
    console.print(f"  Trendlines formed: {stats['formed']} ({stats['formed_pct']:.1f}%)")
    if stats['avg_days_to_form']:
        console.print(f"  Avg days to form: {stats['avg_days_to_form']:.0f}")
    if stats['avg_swing_lows']:
        console.print(f"  Avg swing lows: {stats['avg_swing_lows']:.1f}")

    # Quality distribution
    if stats["quality_distribution"]:
        console.print()
        console.print("[bold cyan]Quality Distribution (R²):[/bold cyan]")
        table = Table(show_header=True)
        table.add_column("Quality")
        table.add_column("Count", justify="right")
        table.add_column("Avg Gain %", justify="right")

        for q in stats["quality_distribution"]:
            table.add_row(
                q["quality"].capitalize(),
                str(q["count"]),
                f"{q['avg_gain']:,.0f}%" if q['avg_gain'] else "-",
            )
        console.print(table)

    # Touch stats
    console.print()
    console.print("[bold cyan]Touch Statistics:[/bold cyan]")
    if stats['avg_touches']:
        console.print(f"  Avg touches per stock: {stats['avg_touches']:.1f}")
    if stats['avg_bounce_pct']:
        console.print(f"  Avg bounce from trendline: {stats['avg_bounce_pct']:.2f}%")


@trendline.command("results")
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to database file",
)
@click.option(
    "--min-r-squared",
    type=float,
    default=None,
    help="Filter by minimum R² value",
)
@click.option(
    "--timeframe",
    type=click.Choice(["daily", "weekly"]),
    default=None,
    help="Filter by timeframe",
)
@click.option(
    "--formed-only",
    is_flag=True,
    help="Only show stocks where trendline formed",
)
@click.option(
    "--top",
    type=int,
    default=50,
    help="Number of results to show",
)
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "csv", "json"]),
    default="table",
    help="Output format",
)
def trendline_results(
    db_path: str | None,
    min_r_squared: float | None,
    timeframe: str | None,
    formed_only: bool,
    top: int,
    output_format: str,
) -> None:
    """View trendline analysis results."""
    from rich.table import Table
    import json as json_module

    db = Database(db_path) if db_path else Database()

    results = db.get_trendline_analyses(
        min_r_squared=min_r_squared,
        timeframe=timeframe,
        formed_only=formed_only,
        limit=top,
    )

    if not results:
        console.print("[yellow]No trendline analyses found[/yellow]")
        return

    if output_format == "json":
        click.echo(json_module.dumps(results, indent=2, default=str))
        return

    if output_format == "csv":
        import csv
        import sys
        writer = csv.writer(sys.stdout)
        writer.writerow([
            "ticker", "timeframe", "formed", "r_squared", "slope_pct",
            "touches", "gain_pct", "days_to_peak"
        ])
        for r in results:
            writer.writerow([
                r["ticker"],
                r["timeframe"],
                r["trendline_formed"],
                f"{r['r_squared']:.3f}" if r['r_squared'] else "",
                f"{r['slope_pct_per_day']:.3f}" if r['slope_pct_per_day'] else "",
                r.get("touch_count", ""),
                r.get("gain_pct", ""),
                r.get("days_to_peak", ""),
            ])
        return

    # Table format
    table = Table(title=f"Trendline Analysis (top {len(results)})")
    table.add_column("Ticker", style="cyan")
    table.add_column("TF")
    table.add_column("Formed")
    table.add_column("R²", justify="right")
    table.add_column("Slope %/day", justify="right")
    table.add_column("Touches", justify="right")
    table.add_column("Gain %", justify="right")

    for r in results:
        formed = "[green]✓[/green]" if r["trendline_formed"] else "[red]✗[/red]"
        r_sq = f"{r['r_squared']:.3f}" if r['r_squared'] else "-"
        slope = f"{r['slope_pct_per_day']:.3f}" if r['slope_pct_per_day'] else "-"

        table.add_row(
            r["ticker"],
            r["timeframe"][:1].upper(),  # D or W
            formed,
            r_sq,
            slope,
            str(r.get("touch_count", "-")),
            f"{r.get('gain_pct', 0):,.0f}%",
        )

    console.print(table)


# =============================================================================
# Cache Management Commands
# =============================================================================


@cli.group()
def cache() -> None:
    """Cache management commands - view stats and clear cached data."""
    pass


@cache.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show cache statistics."""
    from rich.table import Table

    settings = ctx.obj["settings"]
    cache_config = settings.data.cache

    if not cache_config.enabled:
        console.print("[yellow]Cache is disabled in configuration[/yellow]")
        return

    cache_manager = CacheManager(cache_config)
    cache_stats = cache_manager.get_stats()

    console.print()
    console.print("[bold]Cache Statistics[/bold]")
    console.print("=" * 40)

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("Status", "[green]Enabled[/green]" if cache_stats["enabled"] else "[red]Disabled[/red]")
    table.add_row("Cache Directory", cache_stats.get("cache_dir", cache_config.cache_dir))
    table.add_row("Entries", str(cache_stats["entry_count"]))
    table.add_row("Total Size", f"{cache_stats['total_size_mb']:.2f} MB")
    table.add_row("Max Size", f"{cache_config.max_size_gb:.1f} GB")
    table.add_row("TTL (recent data)", f"{cache_config.ttl_hours} hours")

    if cache_stats.get("oldest_entry"):
        table.add_row("Oldest Entry", str(cache_stats["oldest_entry"]))
    if cache_stats.get("newest_entry"):
        table.add_row("Newest Entry", str(cache_stats["newest_entry"]))

    console.print(table)


@cache.command()
@click.option(
    "--ticker",
    type=str,
    default=None,
    help="Clear cache for specific ticker only",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def clear(ctx: click.Context, ticker: str | None, force: bool) -> None:
    """Clear cached data."""
    settings = ctx.obj["settings"]
    cache_config = settings.data.cache

    if not cache_config.enabled:
        console.print("[yellow]Cache is disabled in configuration[/yellow]")
        return

    cache_manager = CacheManager(cache_config)

    # Get current stats
    current_stats = cache_manager.get_stats()
    if current_stats["entry_count"] == 0:
        console.print("[yellow]Cache is already empty[/yellow]")
        return

    # Confirm if not forced
    if not force:
        if ticker:
            msg = f"Clear cache entries for {ticker.upper()}?"
        else:
            msg = f"Clear all {current_stats['entry_count']} cache entries ({current_stats['total_size_mb']:.2f} MB)?"

        if not click.confirm(msg):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Clear the cache
    cleared = cache_manager.clear(ticker=ticker.upper() if ticker else None)

    console.print(f"[green]Cleared {cleared} cache entries[/green]")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()

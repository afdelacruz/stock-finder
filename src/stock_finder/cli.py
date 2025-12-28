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
from stock_finder.output.formatters import format_as_csv, format_as_json, format_as_table, save_results
from stock_finder.scanners.gainer_scanner import GainerScanner
from stock_finder.utils.logging import setup_logging

console = Console()


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

    # Create data provider (FMP by default, yfinance as fallback)
    provider_choice = provider or settings.default_provider
    if provider_choice == "fmp":
        try:
            data_provider = FMPProvider(settings.fmp)
            console.print("[cyan]Using FMP data provider[/cyan]")
        except ValueError as e:
            console.print(f"[yellow]FMP unavailable ({e}), falling back to yfinance[/yellow]")
            data_provider = YFinanceProvider(settings.data)
    else:
        data_provider = YFinanceProvider(settings.data)
        console.print("[cyan]Using yfinance data provider[/cyan]")

    scanner = GainerScanner(data_provider, scan_config)

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
@click.pass_context
def check(ctx: click.Context, ticker: str, years: int, provider: str | None) -> None:
    """Check a single ticker for gains."""
    settings = ctx.obj["settings"]

    scan_config = settings.scan.model_copy()
    scan_config.lookback_years = years
    scan_config.min_gain_pct = 0  # Show any gain

    # Create data provider
    provider_choice = provider or settings.default_provider
    if provider_choice == "fmp":
        try:
            data_provider = FMPProvider(settings.fmp)
        except ValueError:
            data_provider = YFinanceProvider(settings.data)
    else:
        data_provider = YFinanceProvider(settings.data)

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


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Populate the themes table with data from our research analysis.

Run: python scripts/populate_themes.py
"""

import sys
sys.path.insert(0, "src")

from stock_finder.data.database import Database


# Theme data derived from analysis/findings/theme_timeline.md and RESEARCH_SUMMARY.md
THEMES = [
    # Crypto / Bitcoin Mining - Wave 1 (Mar 2020 - Nov 2021)
    {"ticker": "MARA", "theme": "Crypto", "wave": 1, "notes": "Bitcoin miner, 18,922% gain"},
    {"ticker": "RIOT", "theme": "Crypto", "wave": 1, "notes": "Bitcoin miner"},
    {"ticker": "BTBT", "theme": "Crypto", "wave": 1, "notes": "Bitcoin miner"},
    {"ticker": "MSTR", "theme": "Crypto", "wave": 1, "notes": "Bitcoin treasury"},
    {"ticker": "HUT", "theme": "Crypto", "wave": 1, "notes": "Bitcoin miner"},
    {"ticker": "CLSK", "theme": "Crypto", "wave": 1, "notes": "Bitcoin miner"},
    {"ticker": "ANY", "theme": "Crypto", "wave": 1, "notes": "Crypto"},
    {"ticker": "SOS", "theme": "Crypto", "wave": 1, "notes": "Crypto miner"},

    # Crypto / Bitcoin Mining - Wave 2 (Dec 2022 - ongoing)
    {"ticker": "CIFR", "theme": "Crypto", "wave": 2, "notes": "Bitcoin miner, Wave 2"},
    {"ticker": "IREN", "theme": "Crypto", "wave": 2, "notes": "Bitcoin miner, Wave 2"},
    {"ticker": "COIN", "theme": "Crypto", "wave": 2, "notes": "Crypto exchange, Wave 2"},
    {"ticker": "ARBK", "theme": "Crypto", "wave": 2, "notes": "Bitcoin miner, Wave 2"},
    {"ticker": "EBON", "theme": "Crypto", "wave": 2, "notes": "Mining hardware, Wave 2"},

    # Meme Stocks (Mar 2020 - Jun 2021)
    {"ticker": "GME", "theme": "Meme", "wave": 1, "notes": "GameStop, 12,311% gain"},
    {"ticker": "AMC", "theme": "Meme", "wave": 1, "notes": "AMC Entertainment"},
    {"ticker": "BB", "theme": "Meme", "wave": 1, "notes": "BlackBerry"},
    {"ticker": "BBBY", "theme": "Meme", "wave": 1, "notes": "Bed Bath Beyond"},
    {"ticker": "KOSS", "theme": "Meme", "wave": 1, "notes": "Koss Corp"},
    {"ticker": "SNDL", "theme": "Meme", "wave": 1, "notes": "Sundial Growers"},
    {"ticker": "WKHS", "theme": "Meme", "wave": 1, "notes": "Workhorse Group"},
    {"ticker": "EXPR", "theme": "Meme", "wave": 1, "notes": "Express Inc"},

    # Clean Energy / EV - Wave 1 (Dec 2018 - Feb 2021)
    {"ticker": "PLUG", "theme": "CleanEnergy", "wave": 1, "notes": "Fuel cells"},
    {"ticker": "ENPH", "theme": "CleanEnergy", "wave": 1, "notes": "Solar inverters"},
    {"ticker": "FCEL", "theme": "CleanEnergy", "wave": 1, "notes": "Fuel cells, 17,375% gain"},
    {"ticker": "BLDP", "theme": "CleanEnergy", "wave": 1, "notes": "Fuel cells"},
    {"ticker": "BE", "theme": "CleanEnergy", "wave": 1, "notes": "Bloom Energy"},
    {"ticker": "BLNK", "theme": "CleanEnergy", "wave": 1, "notes": "EV charging"},
    {"ticker": "RUN", "theme": "CleanEnergy", "wave": 1, "notes": "Sunrun solar"},
    {"ticker": "CHPT", "theme": "CleanEnergy", "wave": 1, "notes": "EV charging"},
    {"ticker": "LCID", "theme": "CleanEnergy", "wave": 1, "notes": "Lucid Motors"},
    {"ticker": "STEM", "theme": "CleanEnergy", "wave": 1, "notes": "Energy storage"},

    # Clean Energy - Wave 2 (Apr 2024)
    {"ticker": "SPWR", "theme": "CleanEnergy", "wave": 2, "notes": "SunPower, Wave 2"},
    {"ticker": "EVGO", "theme": "CleanEnergy", "wave": 2, "notes": "EV charging, Wave 2"},
    {"ticker": "HYLN", "theme": "CleanEnergy", "wave": 2, "notes": "Hyliion, Wave 2"},

    # COVID Plays (Jun 2019 - Aug 2021)
    {"ticker": "MRNA", "theme": "COVID", "wave": 1, "notes": "mRNA vaccines"},
    {"ticker": "BNTX", "theme": "COVID", "wave": 1, "notes": "BioNTech vaccines"},
    {"ticker": "NVAX", "theme": "COVID", "wave": 1, "notes": "Novavax, 8,570% gain"},
    {"ticker": "INO", "theme": "COVID", "wave": 1, "notes": "Inovio Pharma"},
    {"ticker": "CODX", "theme": "COVID", "wave": 1, "notes": "COVID testing"},
    {"ticker": "APT", "theme": "COVID", "wave": 1, "notes": "PPE/masks"},
    {"ticker": "OCGN", "theme": "COVID", "wave": 1, "notes": "Covaxin"},
    {"ticker": "NNOX", "theme": "COVID", "wave": 1, "notes": "Medical imaging"},

    # Uranium / Nuclear - Wave 1 (Dec 2018 - Oct 2025)
    {"ticker": "LEU", "theme": "Nuclear", "wave": 1, "notes": "Centrus, 25,699% gain (6.8 years)"},
    {"ticker": "UEC", "theme": "Nuclear", "wave": 1, "notes": "Uranium Energy Corp"},
    {"ticker": "UUUU", "theme": "Nuclear", "wave": 1, "notes": "Energy Fuels"},
    {"ticker": "CCJ", "theme": "Nuclear", "wave": 1, "notes": "Cameco"},
    {"ticker": "DNN", "theme": "Nuclear", "wave": 1, "notes": "Denison Mines"},
    {"ticker": "NXE", "theme": "Nuclear", "wave": 1, "notes": "NexGen Energy"},

    # Nuclear - Wave 2 (Jan 2024 - Oct 2025)
    {"ticker": "SMR", "theme": "Nuclear", "wave": 2, "notes": "NuScale, small modular reactors"},
    {"ticker": "NNE", "theme": "Nuclear", "wave": 2, "notes": "Nano Nuclear, Wave 2"},
    {"ticker": "OKLO", "theme": "Nuclear", "wave": 2, "notes": "Oklo, advanced reactors"},

    # Space / Aerospace - Wave 1 (Nov 2019 - Dec 2022)
    {"ticker": "SPCE", "theme": "Space", "wave": 1, "notes": "Virgin Galactic"},
    {"ticker": "GSAT", "theme": "Space", "wave": 1, "notes": "Globalstar satellite"},
    {"ticker": "KTOS", "theme": "Space", "wave": 1, "notes": "Kratos defense/drones"},
    {"ticker": "ACHR", "theme": "Space", "wave": 1, "notes": "Archer Aviation eVTOL"},
    {"ticker": "IONQ", "theme": "Space", "wave": 1, "notes": "Quantum computing"},
    {"ticker": "JOBY", "theme": "Space", "wave": 1, "notes": "Joby Aviation eVTOL"},
    {"ticker": "RDW", "theme": "Space", "wave": 1, "notes": "Redwire space infra"},

    # Space - Wave 2 (Jan 2024 - Dec 2025)
    {"ticker": "LUNR", "theme": "Space", "wave": 2, "notes": "Intuitive Machines, lunar lander"},
    {"ticker": "ASTS", "theme": "Space", "wave": 2, "notes": "AST SpaceMobile, 4,661% gain"},
    {"ticker": "RKLB", "theme": "Space", "wave": 2, "notes": "Rocket Lab, launch provider"},
    {"ticker": "PL", "theme": "Space", "wave": 2, "notes": "Planet Labs imaging"},
    {"ticker": "BKSY", "theme": "Space", "wave": 2, "notes": "BlackSky imaging"},
]


def main():
    db = Database()

    print(f"Loading {len(THEMES)} theme mappings...")

    # Clear existing themes first (for clean reload)
    cleared = db.clear_themes()
    if cleared:
        print(f"Cleared {cleared} existing theme mappings")

    # Add all themes
    count = db.add_themes_bulk(THEMES)
    print(f"Added {count} theme mappings")

    # Show summary
    print("\nTheme Summary:")
    print("-" * 50)
    summary = db.get_theme_summary()
    for row in summary:
        print(f"  {row['theme']} Wave {row['wave']}: {row['stock_count']} stocks")
        print(f"    Tickers: {row['tickers']}")

    print(f"\nTotal: {len(THEMES)} ticker-theme mappings across {len(summary)} theme-waves")


if __name__ == "__main__":
    main()

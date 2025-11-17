#!/usr/bin/env python
"""
Script to download the CUAD (Contract Understanding Atticus Dataset).

Downloads the dataset from the official source and prepares it for processing.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from atticus.core.config import get_config
from atticus.core.logger import get_logger

logger = get_logger(__name__)


def download_cuad_dataset():
    """
    Download CUAD dataset.

    The CUAD dataset should be downloaded from:
    https://www.atticusprojectai.org/cuad

    Or from the GitHub repository:
    https://github.com/TheAtticusProject/cuad
    """
    logger.info("CUAD Dataset Download Instructions")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Please download the CUAD dataset manually from:")
    logger.info("  https://www.atticusprojectai.org/cuad")
    logger.info("  or")
    logger.info("  https://github.com/TheAtticusProject/cuad")
    logger.info("")
    logger.info("After downloading:")
    logger.info("1. Extract the dataset")
    logger.info("2. Place the contracts in: ./data/raw/cuad/")
    logger.info("3. Place the annotations in: ./data/raw/cuad/annotations/")
    logger.info("")
    logger.info("Expected structure:")
    logger.info("  data/raw/cuad/")
    logger.info("  ├── full_contract_txt/")
    logger.info("  │   ├── contract_001.txt")
    logger.info("  │   ├── contract_002.txt")
    logger.info("  │   └── ...")
    logger.info("  └── CUAD_v1.json")
    logger.info("")

    config = get_config()
    data_dir = Path(config.raw_data_dir) / "cuad"
    data_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Data directory created: {data_dir}")
    logger.info("Please place the CUAD dataset in this directory.")


def verify_cuad_dataset():
    """Verify that CUAD dataset is properly installed."""
    config = get_config()
    cuad_dir = Path(config.raw_data_dir) / "cuad"

    if not cuad_dir.exists():
        logger.error(f"CUAD directory not found: {cuad_dir}")
        return False

    # Check for annotation file
    annotation_file = cuad_dir / "CUAD_v1.json"
    if annotation_file.exists():
        logger.info(f"Found CUAD annotations: {annotation_file}")
        with open(annotation_file, "r") as f:
            data = json.load(f)
            logger.info(f"Loaded {len(data.get('data', []))} documents from annotations")
    else:
        logger.warning(f"CUAD annotation file not found: {annotation_file}")

    # Check for contracts directory
    contracts_dir = cuad_dir / "full_contract_txt"
    if contracts_dir.exists():
        contract_files = list(contracts_dir.glob("*.txt"))
        logger.info(f"Found {len(contract_files)} contract files")
        return True
    else:
        logger.warning(f"Contracts directory not found: {contracts_dir}")
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="CUAD Dataset Manager")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify dataset installation",
    )

    args = parser.parse_args()

    if args.verify:
        if verify_cuad_dataset():
            logger.info("CUAD dataset verification successful!")
            sys.exit(0)
        else:
            logger.error("CUAD dataset verification failed!")
            sys.exit(1)
    else:
        download_cuad_dataset()


if __name__ == "__main__":
    main()

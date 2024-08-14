# Copyright 2024 Broda Group Software Inc.
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
#
# Created: 2024-08-14 by 15205060+DavisBroda@users.noreply.github.com
import argparse
import json
import logging

from cli.cliexec_metadata import CliExecMetadata

LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOGGING_LEVEL = logging.INFO
logging.basicConfig(format=LOGGING_FORMAT, level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)


def addmeta(parser: argparse.ArgumentParser):
    args = parser.parse_args()
    cliexec = CliExecMetadata()

    value_cols = json.loads(args.value_columns)
    key_cols = json.loads(args.key_columns)

    res = cliexec.add_meta(
        args.database_dir,
        args.dataset_name,
        args.description,
        key_cols,
        value_cols,
        args.dataset_type
    )

    print(f"Created Metadata Entry for {res}")


def showmeta(parser: argparse.ArgumentParser):
    args = parser.parse_args()
    cliexec = CliExecMetadata()
    out = cliexec.show_meta(
        args.database_dir
    )

    logger.info(f"retrieved metadata: {out}")


def add_meta_parser(
        subparsers
):
    meta_parser = subparsers.add_parser(
        "addmeta", help="Add a metadata entry,"
                        " allowing a dataset to be accessed")
    meta_parser.add_argument(
        "--database_dir",
        help="the directory where databases are stored/created",
        required=True
    )
    meta_parser.add_argument(
        "--dataset_name",
        help="The name by which the dataset will be referred and accessed",
        required=True
    )
    meta_parser.add_argument(
        "--description",
        help="A description of what the dataset contains",
        required=True
    )
    meta_parser.add_argument(
        "--value_columns",
        help="A JSON object mapping value column name to data type. "
             "Data type must be a valid Duckdb General Purpose data type.",
        required=True
    )
    meta_parser.add_argument(
        "--key_columns",
        help="A JSON object mapping key column name to data type. "
             "Data type must be a valid Duckdb General Purpose data type.",
        required=True
    )
    meta_parser.add_argument(
        "--dataset_type",
        help="The type of dataset. Currently supported types are [h3, point]",
        required=True
    )


def show_meta_parser(
        subparsers
):
    meta_parser = subparsers.add_parser(
        "showmeta", help="show available meta entries")
    meta_parser.add_argument(
        "--database_dir",
        help="the directory where databases are stored/created",
        required=True
    )


def execute():
    """
    Main function that sets up the argparse CLI interface.
    """

    # Initialize argparse and set general CLI description
    parser = argparse.ArgumentParser(
        description="Data Mesh Agent Command Line Interface (CLI)")

    # Parser for top-level commands
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    # Create subparsers to handle multiple commands
    subparsers = parser.add_subparsers(dest="command",
                                       help="Available commands")

    add_meta_parser(subparsers)
    show_meta_parser(subparsers)

    args = parser.parse_args()
    logger.info(args)
    # print(args)

    # Set up logging
    logging_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(format=logging_format,
                        level=logging.INFO if args.verbose else logging.WARNING)

    # Execute corresponding function based on provided command
    if args.command == "addmeta":
        addmeta(parser)
    elif args.command == "showmeta":
        showmeta(parser)
    else:
        usage(parser, "Command missing - please provide command")


def usage(parser: any, msg: str):
    print(f"Error: {msg}\n")
    parser.print_help()


if __name__ == "__main__":
    # Execute mainline
    execute()

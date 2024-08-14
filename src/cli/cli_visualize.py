import argparse
import logging

from cli.cliexec_visualize import CliExecVisualize

LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOGGING_LEVEL = logging.INFO
logging.basicConfig(format=LOGGING_FORMAT, level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)


def visualize_dataset(parser: argparse.ArgumentParser):
    args = parser.parse_args()

    cliexec = CliExecVisualize()

    cliexec.visualize_dataset(
        args.database_dir,
        args.resolution,
        args.dataset,
        args.value_column,
        args.max_color,
        args.output_file,
        args.min_lat,
        args.max_lat,
        args.min_long,
        args.max_long,
        args.threshold,
        args.year,
        args.month,
        args.day,
        args.ds_type,
        args.visualizer_type
    )


def add_viualize_dataset_parser(
        subparsers
):
    visualize_parser = subparsers.add_parser(
        "visualize-dataset", help="Visualized maps and overlays")
    visualize_parser.add_argument(
        "--database-dir", required=True,
        type=str,
        help="The directory in which databases are stored"
    )
    visualize_parser.add_argument(
        "--dataset", required=True,
        help="The name of the dataset to visualize"
             "must be a dataset registered in the metadata")
    visualize_parser.add_argument(
        "--resolution", required=True,
        type=int,
        help="The h3 resolution level to display data for"
    )
    visualize_parser.add_argument(
        "--value-column", required=True,
        type=str,
        help="The column of data which is to be visualized"
    )
    visualize_parser.add_argument(
        "--max-color", required=True,
        nargs=3,
        type=int,
        help="The h3 resolution level to display data for"
    )
    visualize_parser.add_argument(
        "--output-file", required=True,
        type=str,
        help="The file where the visualized map will be stored"
    )
    visualize_parser.add_argument(
        "--min-lat", required=False,
        type=float,
        help="The minimum latitude to display"
    )
    visualize_parser.add_argument(
        "--max-lat", required=False,
        type=float,
        help="The maximum latitude to display"
    )
    visualize_parser.add_argument(
        "--min-long", required=False,
        type=float,
        help="The minimum longitude to display"
    )
    visualize_parser.add_argument(
        "--max-long", required=False,
        type=float,
        help="The maximum longitude to display"
    )
    visualize_parser.add_argument(
        "--year", required=False,
        type=float,
        help="The year to display data for"
    )
    visualize_parser.add_argument(
        "--month", required=False,
        type=float,
        help="The month to display data for"
    )
    visualize_parser.add_argument(
        "--day", required=False,
        type=float,
        help="The day to display data for"
    )
    visualize_parser.add_argument(
        "--threshold", required=False,
        type=float,
        help="A ratio of data points relative to max and min values. Only"
             "cells where the data point is greater than threshold"
             "will be displayed. Scaled relative to min and max value"
    )
    visualize_parser.add_argument(
        "--ds-type", required=False,
        type=str,
        default="h3",
        help="the type of ds to process. acceptable values: [h3, point]"
    )
    visualize_parser.add_argument(
        "--visualizer-type", required=False,
        type=str,
        default="HexGridVisualizer",
        help="the type of ds to process. acceptable values: ["
             "HexGridVisualizer, PointLocationVisualizer]"
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

    add_viualize_dataset_parser(subparsers)

    args = parser.parse_args()
    logger.info(args)

    # Set up logging
    logging_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(format=logging_format,
                        level=logging.INFO if args.verbose else logging.WARNING)

    # Execute corresponding function based on provided command
    if args.command == "visualize-dataset":
        visualize_dataset(parser)
    else:
        usage(parser, "Command missing - please provide command")


def usage(parser: any, msg: str):
    print(f"Error: {msg}\n")
    parser.print_help()


if __name__ == "__main__":
    # Execute mainline
    execute()

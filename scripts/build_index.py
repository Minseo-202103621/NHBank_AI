"""Command‑line interface to build the regulation index.

This script wraps the `retriever.index_builder.build_index` function so that
it can be invoked easily from the command line.  Use it to create a
`regulation_index.jsonl` file from a directory of PDF documents.
"""

import argparse

from retriever.index_builder import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build regulation index from PDFs")
    parser.add_argument(
        "--pdf-dir",
        required=True,
        help="Directory containing PDF files to index",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the output JSONL file",
    )
    args = parser.parse_args()
    build_index(args.pdf_dir, args.output)


if __name__ == "__main__":
    main()
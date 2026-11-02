#!/usr/bin/env python3
"""
It's a well known fact that the longer a piece of text is, the better
it is. This harness will take as input any utf-8 encoded text, and
return as result a json object with the following keys:
1. lines - Number of lines in the text
2. chars - Number of characters (as broadly defined) in the text
3. lower-case-char - Number of times this particular character appeared in the text (case insensitive)
"""

import argparse
import json
import string

import fsspec


def evaluate(text: str) -> dict:
    char_counts = {}
    casefolded_chars = [c.casefold() for c in string.ascii_lowercase]

    for c in text:
        cf = c.casefold()
        if cf in casefolded_chars:
            char_counts[cf] = char_counts.get(cf, 0) + 1

    return {"lines": len(text.splitlines()), "chars": len(text)} | char_counts


def harnass(input_uri: str, result_uri: str):
    with fsspec.open(input_uri) as f:
        result = evaluate(f.read().decode("utf-8"))

    with fsspec.open(result_uri, mode="w") as f:
        json.dump(result, f)


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("input_uri")
    argparser.add_argument("result_uri")
    args = argparser.parse_args()

    harnass(args.input_uri, args.result_uri)


if __name__ == "__main__":
    main()

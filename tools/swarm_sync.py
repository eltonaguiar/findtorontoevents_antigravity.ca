#!/usr/bin/env python3
import json
import sys


def get_timestamp(filepath: str) -> str:
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        return data.get('last_modified') or data.get('regime_updated_at') or '0'
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return '0'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('0')
        sys.exit(0)
    print(get_timestamp(sys.argv[1]))
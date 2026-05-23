#!/usr/bin/env python3
"""
Walk-forward / rolling evaluation stub.
Production path: export settled bets with dates, train policy on [t0,t1], test on (t1,t2].
This script documents the hook; implement SQL date filters on lm_sports_bets + forensics segments.
"""
from __future__ import print_function

import sys


def main():
    print(
        "Walk-forward stub: use lm_sports_bets.settled_at windows + "
        "sports_forensics.php?action=segments&include_ci=1 for segment WR with Wilson CI."
    )
    print("Bonferroni: divide alpha by number of segments tested when slicing many buckets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

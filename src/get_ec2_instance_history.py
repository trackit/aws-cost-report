#!/usr/bin/env python3

import collections
import csv
import functools
import itertools
import json

import utils

USAGECOST_DIR='in/usagecost'
OUT_PATH = 'out/instance-history.csv'
USAGE = 'BoxUsage'

def updated(base, addend):
    base = base.copy()
    base.update(addend)
    return base

with utils.csv_folder(USAGECOST_DIR) as records:
    box_usage_records = (
        record
        for record in records
        if USAGE in record['lineItem/UsageType']
    )
    simplified_lineitems = (
        (record['product/instanceType'], round(float(record['lineItem/UsageAmount'])) if record['lineItem/UsageAmount'] else 0, record['lineItem/UsageStartDate'][:10])
        for record in box_usage_records
    )

    histogram = {
        date: updated(
            collections.defaultdict(int),
            {
                instancetype: sum(
                    lineitem[1] for lineitem in instancetype_lineitems
                )
                for instancetype, instancetype_lineitems in itertools.groupby(
                    sorted(
                        date_lineitems,
                        key=lambda x: x[0],
                    ),
                    key=lambda x: x[0],
                )
            }
        )
        for date, date_lineitems in itertools.groupby(
            sorted(
                simplified_lineitems,
                key=lambda x: x[2],
            ),
            key=lambda x: x[2],
        )
    }

instance_types = sorted(
    functools.reduce(
        lambda x, y: x.union(y),
        (
            date.keys()
            for date in histogram.values()
        ),
        frozenset(),
    )
)

with open(OUT_PATH, 'w') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=['date', *instance_types])
    writer.writeheader()
    for date in sorted(histogram.keys()):
        writer.writerow(updated(
            collections.defaultdict(int),
            { 'date': date, **histogram[date] }
        ))

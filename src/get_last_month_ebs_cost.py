#!/usr/bin/env python3

import csv
from datetime import datetime
from collections import defaultdict
import dateutil.relativedelta

import utils

USAGECOST_DIR='in/usagecost'
OUT_PATH_EBS = 'out/last-month/ebs.csv'
OUT_PATH_SNAPSHOTS = 'out/last-month/snapshots.csv'

BEGIN_LAST_MONTH = (datetime.now() + dateutil.relativedelta.relativedelta(months=-1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
END_LAST_MONTH = (BEGIN_LAST_MONTH + dateutil.relativedelta.relativedelta(months=1, days=-1)).replace(hour=23, minute=59, second=59, microsecond=999999)

with utils.csv_folder(USAGECOST_DIR) as records:
    ebs_usage_records = defaultdict(float)
    snapshot_usage_records = defaultdict(float)
    for record in records:
        if 'EBS' in record['lineItem/UsageType'] and 'EBSOptimized' not in record['lineItem/UsageType']:
            usage_start_date = datetime.strptime(record['lineItem/UsageStartDate'], '%Y-%m-%dT%H:%M:%SZ')
            if usage_start_date >= BEGIN_LAST_MONTH and usage_start_date <= END_LAST_MONTH:
                if 'Snapshot' not in record['lineItem/UsageType']:
                    ebs_usage_records[(record['lineItem/ResourceId'], record['product/region'])] += float(record['lineItem/UnblendedCost'])
                elif 'Snapshot' in record['lineItem/UsageType']:
                    snapshot_usage_records[record['lineItem/ResourceId']] += float(record['lineItem/UnblendedCost'])

with open(OUT_PATH_EBS, 'w') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(['ResourceId', 'Region', 'Cost'])
    for ebs in sorted(ebs_usage_records.keys(), key=lambda tup: tup[0]):
        writer.writerow([
            ebs[0],
            ebs[1],
            repr(ebs_usage_records[ebs]),
        ])

with open(OUT_PATH_SNAPSHOTS, 'w') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(['ResourceId', 'Cost'])
    for rid in sorted(snapshot_usage_records.keys()):
        writer.writerow([
            rid,
            repr(snapshot_usage_records[rid]),
        ])

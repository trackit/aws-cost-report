#!/usr/bin/env python3

import csv
from datetime import datetime
from collections import defaultdict
import dateutil.relativedelta
import json
import re

import utils

USAGECOST_DIR='in/usagecost'
METADATA_DIR='out/instance-metadata'
OUT_PATH_EBS = 'out/last-month/ebs.csv'
OUT_PATH_SNAPSHOTS = 'out/last-month/snapshots.csv'

BEGIN_LAST_MONTH = (datetime.now() + dateutil.relativedelta.relativedelta(months=-1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
END_LAST_MONTH = (BEGIN_LAST_MONTH + dateutil.relativedelta.relativedelta(months=1, days=-1)).replace(hour=23, minute=59, second=59, microsecond=999999)

with utils.csv_folder(METADATA_DIR) as records:
    ebs_match = re.compile(r"((vol-[0-9a-fA-F]*),?)*")
    ebs_links = defaultdict(lambda: ("",""))
    for record in records:
        for ebs in ebs_match.match(record['ebs']).group(0).split(','):
            ebs_links[ebs] = (record['instance_id'], record['name'])

with utils.csv_folder(USAGECOST_DIR) as records:
    resource_id_missing = False
    ebs_usage_records = defaultdict(float)
    snapshot_usage_records = defaultdict(float)
    for record in records:
        if 'lineItem/ResourceId' not in record:
            if resource_id_missing == False:
                print("Error: the billing report does not export the ResourceId")
                resource_id_missing = True
            continue
        if 'EBS' in record['lineItem/UsageType'] and 'EBSOptimized' not in record['lineItem/UsageType']:
            usage_start_date = datetime.strptime(record['lineItem/UsageStartDate'], '%Y-%m-%dT%H:%M:%SZ')
            if usage_start_date >= BEGIN_LAST_MONTH and usage_start_date <= END_LAST_MONTH:
                if 'Snapshot' not in record['lineItem/UsageType']:
                    ebs_usage_records[(record['lineItem/UsageAccountId'], record['lineItem/ResourceId'], record['product/region'])] += float(record['lineItem/UnblendedCost'])
                elif 'Snapshot' in record['lineItem/UsageType']:
                    snapshot_usage_records[(record['lineItem/UsageAccountId'], record['lineItem/ResourceId'])] += float(record['lineItem/UnblendedCost'])

with open(OUT_PATH_EBS, 'w') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(['Account', 'ResourceId', 'Region', 'Cost', 'InstanceId', 'InstanceName'])
    for ebs in sorted(ebs_usage_records.keys(), key=lambda tup: ebs_usage_records[tup], reverse=True):
        writer.writerow([
            ebs[0],
            ebs[1],
            ebs[2],
            repr(ebs_usage_records[ebs]),
            ebs_links[ebs[1]][0],
            ebs_links[ebs[1]][1],
        ])

with open(OUT_PATH_SNAPSHOTS, 'w') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(['Account', 'ResourceId', 'Cost'])
    for rid in sorted(snapshot_usage_records.keys(), key=lambda rid: snapshot_usage_records[rid], reverse=True):
        writer.writerow([
            rid[0],
            rid[1],
            repr(snapshot_usage_records[rid]),
        ])

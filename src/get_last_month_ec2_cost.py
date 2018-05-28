#!/usr/bin/env python3

import csv
from datetime import datetime
from collections import defaultdict
import dateutil.relativedelta

import utils

USAGECOST_DIR='in/usagecost'
METADATA_DIR='out/instance-metadata'
OUT_PATH_INSTANCES = 'out/last-month/ec2_instances.csv'
OUT_PATH_BANDWIDTH = 'out/last-month/ec2_bandwidth.csv'

BEGIN_LAST_MONTH = (datetime.now() + dateutil.relativedelta.relativedelta(months=-1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
END_LAST_MONTH = (BEGIN_LAST_MONTH + dateutil.relativedelta.relativedelta(months=1, days=-1)).replace(hour=23, minute=59, second=59, microsecond=999999)

with utils.csv_folder(METADATA_DIR) as records:
    instance_name = defaultdict(str)
    for record in records:
        instance_name[record['instance_id']] = record['name']
    
with utils.csv_folder(USAGECOST_DIR) as records:
    resource_id_missing = False
    instance_usage_records = defaultdict(float)
    bandwidth_usage_records = defaultdict(float)
    for record in records:
        if 'lineItem/ResourceId' not in record:
            if resource_id_missing == False:
                print("Error: the billing report does not export the ResourceId")
                resource_id_missing = True
            continue
        if record['lineItem/ProductCode'] == 'AmazonEC2':
            usage_start_date = datetime.strptime(record['lineItem/UsageStartDate'], '%Y-%m-%dT%H:%M:%SZ')
            if usage_start_date >= BEGIN_LAST_MONTH and usage_start_date <= END_LAST_MONTH:
                if 'BoxUsage' in record['lineItem/UsageType']:
                    instance_usage_records[(record['lineItem/UsageAccountId'], record['lineItem/ResourceId'], record['lineItem/AvailabilityZone'], record['pricing/term'], record['product/instanceType'])] += float(record['lineItem/UnblendedCost'])
                elif 'DataTransfer' in record['lineItem/UsageType']:
                    bandwidth_usage_records[record['lineItem/ResourceId']] += float(record['lineItem/UnblendedCost'])

with open(OUT_PATH_INSTANCES, 'w') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(['Account', 'ResourceId', 'Name', 'AvailabilityZone', 'Term', 'Type', 'Cost'])
    for instance in sorted(instance_usage_records.keys(), key=lambda tup: instance_usage_records[tup], reverse=True):
        writer.writerow([
            instance[0],
            instance[1],
            instance_name[instance[1]],
            instance[2],
            instance[3],
            instance[4],
            repr(instance_usage_records[instance]),
        ])

with open(OUT_PATH_BANDWIDTH, 'w') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(['ResourceId', 'Bandwidth'])
    for instance in sorted(bandwidth_usage_records.keys(), key=lambda instance: bandwidth_usage_records[instance], reverse=True):
        writer.writerow([
            instance,
            repr(bandwidth_usage_records[instance]),
        ])

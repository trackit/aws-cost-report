#!/usr/bin/env python3

import csv
from datetime import datetime
from collections import defaultdict
import dateutil.relativedelta

import utils

USAGECOST_DIR='in/usagecost'
OUT_PATH_S3 = 'out/s3/current_usage.csv'

BEGIN_LAST_MONTH = (datetime.now() + dateutil.relativedelta.relativedelta(months=-1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
BEGIN_CURRENT_MONTH = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def get_simplified_cost_name(record):
    if 'TimedStorage' in record.get('lineItem/UsageType', ''):
        return 'storage_cost'
    elif record.get('product/servicecode', '') == 'AWSDataTransfer':
        return 'bandwidth_cost'
    elif 'Requests' in record.get('lineItem/UsageType', ''):
        return 'requests_cost'
    return None

with utils.csv_folder(USAGECOST_DIR) as records:
    resource_id_missing = False
    s3_usage = defaultdict(lambda:dict(usage_gb_month=0.0, storage_cost=0.0, bandwidth_cost=0.0, requests_cost=0.0, last_month_cost=0.0))
    for record in records:
        if 'lineItem/ResourceId' not in record:
            if resource_id_missing == False:
                print("Error: the billing report does not export the ResourceId")
                resource_id_missing = True
            continue
        if record['lineItem/ProductCode'] == 'AmazonS3':
            usage_start_date = datetime.strptime(record['lineItem/UsageStartDate'], '%Y-%m-%dT%H:%M:%SZ')
            if usage_start_date >= BEGIN_LAST_MONTH:
                simplified_cost_name = get_simplified_cost_name(record)
                if simplified_cost_name is not None:
                    if usage_start_date >= BEGIN_CURRENT_MONTH:
                        s3_usage[record.get('lineItem/ResourceId', '')][simplified_cost_name] += float(record['lineItem/UnblendedCost'])
                        if simplified_cost_name == 'storage_cost':
                            s3_usage[record.get('lineItem/ResourceId', '')]['usage_gb_month'] += float(record['lineItem/UsageAmount'])
                    else:
                        s3_usage[record.get('lineItem/ResourceId', '')]['last_month_cost'] += float(record['lineItem/UnblendedCost'])

with open(OUT_PATH_S3, 'w') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(['Bucket', 'Usage-GB-Month', 'StorageCost', 'BandwidthCost', 'RequestsCost', 'CurrentTotal', 'LastMonthTotal'])
    for bucket in sorted(list(s3_usage.keys()), key=lambda resid: s3_usage[resid]['last_month_cost'], reverse=True):
        writer.writerow([
            bucket,
            s3_usage[bucket]['usage_gb_month'],
            s3_usage[bucket]['storage_cost'],
            s3_usage[bucket]['bandwidth_cost'],
            s3_usage[bucket]['requests_cost'],
            s3_usage[bucket]['storage_cost'] + s3_usage[bucket]['bandwidth_cost'] + s3_usage[bucket]['requests_cost'],
            s3_usage[bucket]['last_month_cost'],
        ])

#!/usr/bin/env python3

import boto3
import itertools
import collections
import csv
import sys
import datetime
import json
import pprint
import collections
import re
from dateutil.tz import tzutc

pp = pprint.PrettyPrinter(indent=4)

DIR_INSTANCE_METADATA = 'out/instance-metadata'

REGION = boto3._get_default_session().region_name
ACCOUNT = boto3.client('sts').get_caller_identity()['Account']


def safe_list_get(l, idx, default):
    try:
        return l[idx]
    except IndexError:
        return default


def get_ec2_metadata(ec2, region):
    print("Getting instances metadata for {} in {}...".format(ACCOUNT, REGION))
    instances_pag = ec2.get_paginator('describe_instances')
    metadata = [
        {
            'instance_id': i.get('InstanceId', ''),
            'name': safe_list_get([v['Value'] for v in i.get('Tags', []) if v['Key'] == 'Name'], 0, ''),
            'ebs': ','.join([e.get('Ebs', {}).get('VolumeId', '') for e in i.get('BlockDeviceMappings', [])]),
        }
        for p in instances_pag.paginate()
        for r in p['Reservations']
        for i in r['Instances']
    ]
    print('Done!')
    return metadata


def write_instances_metadata(f, reservation_usage):
    writer = csv.DictWriter(f, fieldnames=[
        'instance_id',
        'name',
        'ebs',
    ])
    writer.writeheader()
    for m in metadata:
        writer.writerow(m)


if __name__ == '__main__':
    ec2 = boto3.client('ec2')
    metadata = get_ec2_metadata(
        ec2, REGION)
    with open('{}/{}.{}.csv'.format(DIR_INSTANCE_METADATA, ACCOUNT, REGION), 'w') as f:
        write_instances_metadata(f, metadata)

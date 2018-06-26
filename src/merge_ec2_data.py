#!/usr/bin/env python3

import utils
import csv
import os
import itertools
import collections

DIR_INSTANCE_RESERVATION_USAGE = 'out/instance-reservation-usage'
OUT_INSTANCE_RESERVATION_USAGE = 'out/instance-reservation-usage.csv'
DIR_RESERVATION_USAGE = 'out/reservation-usage'
OUT_RESERVATION_USAGE = 'out/reservation-usage.csv'

instances_count = collections.defaultdict(int)
instances_meta = collections.defaultdict(lambda:
                                         {
                                             'cost_ondemand': float,
                                             'cost_reserved_worst': float,
                                             'cost_reserved_best': float
                                         })

reservations_count = collections.defaultdict(int)
reservations_used = collections.defaultdict(int)
reservations_meta = collections.defaultdict(lambda:
                                            {
                                                'cost_hourly': float,
                                                'cost_upfront': float,
                                            })


def get_key(record):
    return (
        record['instance_type'], record['availability_zone'], record['tenancy'],
        record['product']
    )


print('Merging ec2 data...')

for file_name in os.listdir(DIR_INSTANCE_RESERVATION_USAGE):
    with open('{}/{}'.format(DIR_INSTANCE_RESERVATION_USAGE, file_name),
              'r') as f:
        instances_reader = csv.DictReader(f)
        for record in instances_reader:
            instances_count[get_key(record)] += int(
                record['count'])
            instances_meta[get_key(record)] = {
                'cost_ondemand': record['cost_ondemand'],
                'cost_reserved_worst': record['cost_reserved_worst'],
                'cost_reserved_best': record['cost_reserved_best'],
            }
    with open('{}/{}'.format(DIR_RESERVATION_USAGE, file_name), 'r') as f:
        reservations_reader = csv.DictReader(f)
        for record in reservations_reader:
            reservations_count[get_key(record)] += int(
                record['count'])
            reservations_meta[get_key(record)] = {
                'cost_hourly': record['cost_hourly'],
                'cost_upfront': record['cost_upfront']
            }


with open(OUT_INSTANCE_RESERVATION_USAGE, 'w') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'instance_type',
        'availability_zone',
        'tenancy',
        'product',
        'count',
        'count_reserved',
        'cost_ondemand',
        'cost_reserved_worst',
        'cost_reserved_best',
    ])
    writer.writeheader()
    reservations_count_save = reservations_count.copy()
    for k in instances_count.keys():
        kk = k if k in reservations_count else (k[0], k[1][:-1], k[2], k[3])
        count_reserved = min(reservations_count[kk], instances_count[k])
        reservations_count[kk] -= count_reserved
        reservations_used[kk] += count_reserved

        writer.writerow({
            'instance_type': k[0],
            'availability_zone': k[1],
            'tenancy': k[2],
            'product': k[3],
            'count': instances_count[k],
            'count_reserved': count_reserved,
            'cost_ondemand': instances_meta[k]['cost_ondemand'],
            'cost_reserved_worst': instances_meta[k]['cost_reserved_worst'],
            'cost_reserved_best': instances_meta[k]['cost_reserved_best'],
        })
    reservations_count = reservations_count_save


with open(OUT_RESERVATION_USAGE, 'w') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'instance_type',
        'availability_zone',
        'tenancy',
        'product',
        'count',
        'count_used',
        'cost_hourly',
        'cost_upfront',
    ])
    writer.writeheader()
    for k in reservations_count.keys():
        writer.writerow({
            'instance_type': k[0],
            'availability_zone': k[1],
            'tenancy': k[2],
            'product': k[3],
            'count': reservations_count[k],
            'count_used': reservations_used[k],
            'cost_hourly': reservations_meta[k]['cost_hourly'],
            'cost_upfront': reservations_meta[k]['cost_upfront'],
        })

print('All ec2 data merged!')

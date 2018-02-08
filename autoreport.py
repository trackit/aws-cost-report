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

import mockdata
from mytypes import *

pp = pprint.PrettyPrinter(indent=4)

with open('ondemandcosts.json') as f:
    compute_instance_costs = json.load(f)

compute_sheet_region = {
    'us-east-2'      : 'US East (Ohio)',
    'us-east-1'      : 'US East (N. Virginia)',
    'us-west-1'      : 'US West (N. California)',
    'us-west-2'      : 'US West (Oregon)',
    'ap-northeast-1' : 'Asia Pacific (Tokyo)',
    'ap-northeast-2' : 'Asia Pacific (Seoul)',
    'ap-south-1'     : 'Asia Pacific (Mumbai)',
    'ap-southeast-1' : 'Asia Pacific (Singapore)',
    'ap-southeast-2' : 'Asia Pacific (Sydney)',
    'ca-central-1'   : 'Canada (Central)',
    'cn-north-1'     : 'China (Beijing)',
    'cn-northwest-1' : 'China (Ningxia)',
    'eu-central-1'   : 'EU (Frankfurt)',
    'eu-west-1'      : 'EU (Ireland)',
    'eu-west-2'      : 'EU (London)',
    'eu-west-3'      : 'EU (Paris)',
    'sa-east-1'      : 'South America (Sao Paulo)',
}

compute_sheet_tenancy = {
    'dedicated' : 'Dedicated',
    'host'      : 'Host',
    'default'   : 'Shared',
}

compute_sheet_platform = {
    'Linux/UNIX' : 'Linux',
    'Windows'    : 'Windows',
    'RHEL'       : 'RHEL',
    'SUSE'       : 'SUSE',
}

DEFAULT_REGION=boto3._get_default_session().region_name

_az_to_region_re = re.compile(r'^(.+?)[a-z]?$')
def az_to_region(az):
    return _az_to_region_re.match(az).group(1)
    

def identity(x):
    return x

def reserved_instance_offering_cost_per_hour(offering):
    return offering['FixedPrice'] / (offering['Duration']/3600) + (offering['RecurringCharges'][0]['Amount'] if len(offering['RecurringCharges']) > 0 else 0.0)

def bucketize(it, key, op=lambda a, b: a.push(b), zero=list):
    acc = collections.defaultdict(zero)
    for el in it:
        k = key(el)
        acc[k] = op(acc[k], el)
    return acc

def get_reserved_instances(ec2, region):
    reserved_instances_data = ec2.describe_reserved_instances()
    return [
        InstanceReservation(
            type = InstanceType(
                size              = ri['InstanceType'],
                availability_zone = ri['AvailabilityZone'] if ri['Scope'] == 'Availability Zone' else DEFAULT_REGION,
                tenancy           = ri['InstanceTenancy'],
                product           = ri['ProductDescription'],
            ),
            cost_hourly       = sum(rc['Amount'] for rc in ri['RecurringCharges']),
            cost_upfront      = ri['FixedPrice'],
            count = ri['InstanceCount'],
        )
        for ri in reserved_instances_data['ReservedInstances']
    ]

def get_ondemand_instance_types(ec2):
    instance_paginator = ec2.get_paginator('describe_instances')
    pages = instance_paginator.paginate(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': [
                    'pending',
                    'running',
                ],
            },
            {
                'Name': 'tenancy',
                'Values': [
                    'dedicated',
                    'default',
                ],
            }
        ]
    )
    reservations = itertools.chain.from_iterable(p['Reservations'] for p in pages)
    instances = itertools.chain.from_iterable(r['Instances'] for r in reservations)
    instances = (
        InstanceType(i['InstanceType'], i['Placement']['AvailabilityZone'], i['Placement']['Tenancy'], i.get('Platform', 'Linux/UNIX'))
        for i in instances
        if i.get('InstanceLifecycle', 'ondemand') == 'ondemand'
    )
    instance_counts = bucketize(
        instances,
        key=identity,
        op=lambda x, _: x + 1,
        zero=int,
    )
    return [
        (k, v)
        for k, v in instance_counts.items()
    ]

def get_ec2_type_offerings(ec2, instance_type):
    offerings = itertools.chain.from_iterable(
        page['ReservedInstancesOfferings']
        for page in ec2.get_paginator('describe_reserved_instances_offerings').paginate(
            IncludeMarketplace=False,
            InstanceTenancy=instance_type.tenancy,
            ProductDescription=instance_type.product,
            Filters=[
                {
                    'Name': 'instance-type',
                    'Values': [instance_type.size],
                },
            ],
        )
    )
    offerings = sorted(offerings, key=reserved_instance_offering_cost_per_hour)
    offering_best = offerings[0]
    offering_worst = offerings[-1]
    ondemand = next(
        c
        for c in compute_instance_costs
        if (
            c['attributes']['instanceType'] == instance_type.size
            and c['attributes']['location'] == compute_sheet_region[az_to_region(instance_type.availability_zone)]
            and c['attributes']['tenancy'] == compute_sheet_tenancy[instance_type.tenancy]
            and c['attributes']['operatingSystem'] == compute_sheet_platform[instance_type.product]
        )
    )['cost']
    res = InstanceOffering(
        type                = instance_type,
        cost_reserved_worst = reserved_instance_offering_cost_per_hour(offering_worst),
        cost_reserved_best  = reserved_instance_offering_cost_per_hour(offering_best),
        cost_ondemand       = ondemand,
    )
    pp.pprint(res)
    return res

def get_instance_offerings(ec2, instance_types):
    return [get_ec2_type_offerings(ec2, ityp) for ityp in instance_types]

def instance_type_matches(pattern, example):
    return pattern.type == example or pattern.type == example._replace(availability_zone=az_to_region(example.availability_zone))

def get_instance_matchings(instance_offerings, reserved_instances, ondemand_instances):
    remaining_reserved_instances = [
        [ri, ri.count]
        for ri in reserved_instances
    ]
    print("BEGIN MATCHING")
    pp.pprint(reserved_instances)
    pp.pprint(remaining_reserved_instances)
    matches = []
    for oi in sorted(ondemand_instances, reverse=True, key=lambda oi: oi[0].availability_zone[::-1]):
        matching_reserved = (
            rri
            for rri in sorted(remaining_reserved_instances, reverse=True, key=lambda i: i[0].type.availability_zone[::-1])
            if rri[1] > 0 and instance_type_matches(rri[0], oi[0])
        )
        reserved = 0
        while reserved < oi[1]:
            try:
                ri = next(matching_reserved)
            except StopIteration:
                break
            use = min(ri[1], oi[1] - reserved)
            ri[1] -= use
            reserved += use
        matches.append(
            InstanceMatching(
                offering       = next(io for io in instance_offerings if io.type == oi[0]),
                count          = oi[1],
                count_reserved = reserved,
            )
        )
    reservations_usage = [
        (ri, ri.count - remaining)
        for [ri, remaining] in remaining_reserved_instances
    ]
    pp.pprint(matches)
    pp.pprint(reservations_usage)
    return matches, reservations_usage

        

def get_ec2_reservation_data(ec2, region):
    print("Getting reserved instances...")
    reserved_instances = mockdata.reserved_instances or get_reserved_instances(ec2, region)
    pp.pprint(reserved_instances)
    print("Getting on-demand instances...")
    ondemand_instances = mockdata.ondemand_instances or get_ondemand_instance_types(ec2)
    pp.pprint(ondemand_instances)
    print("Getting offerings for all instances...")
    instance_offerings = mockdata.instance_offerings or get_instance_offerings(
        ec2,
        frozenset(oi[0] for oi in ondemand_instances) | frozenset(ri.type for ri in reserved_instances),
    )
    print("Matching on-demand instances with reserved instances...")
    matched_instances, reservation_usage = get_instance_matchings(instance_offerings, reserved_instances, ondemand_instances)
    print("Done!")
    return matched_instances, reservation_usage

def write_matched_instances(f, matched_instances, header=True):
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
    if header:
        writer.writeheader()
    for mi in matched_instances:
        writer.writerow({
            'instance_type'       : mi.offering.type.size,
            'availability_zone'   : mi.offering.type.availability_zone,
            'tenancy'             : mi.offering.type.tenancy,
            'product'             : mi.offering.type.product,
            'count'               : mi.count,
            'count_reserved'      : mi.count_reserved,
            'cost_ondemand'       : mi.offering.cost_ondemand,
            'cost_reserved_worst' : mi.offering.cost_reserved_worst,
            'cost_reserved_best'  : mi.offering.cost_reserved_best,
        })

def write_reservation_usage(f, reservation_usage, header=True):
    writer = csv.DictWriter(f, fieldnames=[
        'instance_type',
        'availability_zone',
        'tenancy',
        'product',
        'cost_hourly',
        'cost_upfront',
        'count',
        'count_used',
    ])
    if header:
        writer.writeheader()
    for ru, used in reservation_usage:
        writer.writerow({
            'instance_type'     : ru.type.size,
            'availability_zone' : ru.type.availability_zone,
            'tenancy'           : ru.type.tenancy,
            'product'           : ru.type.product,
            'cost_hourly'       : ru.cost_hourly,
            'cost_upfront'      : ru.cost_upfront,
            'count'             : ru.count,
            'count_used'        : used,
        })

if __name__ == '__main__':
    ec2 = boto3.client('ec2')
    region = ec2._client_config.region_name
    matched_instances, reservation_usage = get_ec2_reservation_data(ec2, region)
    with open('instances-reservation-usage.{}.csv'.format(region), 'w') as f:
        write_matched_instances(f, matched_instances)
    with open('reservation-usage.{}.csv'.format(region), 'w') as f:
        write_reservation_usage(f, reservation_usage)

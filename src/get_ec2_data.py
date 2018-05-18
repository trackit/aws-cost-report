#!/usr/bin/env python3

import botocore
import boto3
import itertools
import collections
import csv
import sys
import datetime
import json
import collections
import re
from dateutil.tz import tzutc
from threading import Thread

import mockdata
from mytypes import *

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
    'Linux/UNIX'                                        : 'Linux',
    'Linux/UNIX (Amazon VPC)'                           : 'Linux',
    'SUSE Linux'                                        : 'SUSE',
    'SUSE Linux (Amazon VPC)'                           : 'SUSE',
    'Red Hat Enterprise Linux'                          : 'RHEL',
    'Red Hat Enterprise Linux (Amazon VPC)'             : 'RHEL',
    'Windows'                                           : 'Windows',
    'windows'                                           : 'Windows',
    'Windows (Amazon VPC)'                              : 'Windows',
    'windows (Amazon VPC)'                              : 'Windows',
    'Windows with SQL Server Standard'                  : 'Windows',
    'windows with SQL Server Standard'                  : 'Windows',
    'Windows with SQL Server Standard (Amazon VPC)'     : 'Windows',
    'windows with SQL Server Standard (Amazon VPC)'     : 'Windows',
    'Windows with SQL Server Web'                       : 'Windows',
    'windows with SQL Server Web'                       : 'Windows',
    'Windows with SQL Server Web (Amazon VPC)'          : 'Windows',
    'windows with SQL Server Web (Amazon VPC)'          : 'Windows',
    'Windows with SQL Server Enterprise'                : 'Windows',
    'windows with SQL Server Enterprise'                : 'Windows',
    'Windows with SQL Server Enterprise (Amazon VPC)'   : 'Windows',
    'windows with SQL Server Enterprise (Amazon VPC)'   : 'Windows',
}

DIR_BILLS                      = 'in/usagecost'
DIR_INSTANCE_RESERVATION_USAGE = 'out/instance-reservation-usage'
DIR_RESERVATION_USAGE          = 'out/reservation-usage'
FIL_ONDEMAND_COSTS             = 'in/ondemandcosts.json'

REGION=boto3._get_default_session().region_name
ACCOUNT=boto3.client('sts').get_caller_identity()['Account']

with open(FIL_ONDEMAND_COSTS) as f:
    compute_instance_costs = json.load(f)

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
    reserved_instances_data = ec2.describe_reserved_instances(
        Filters=[
            {
                'Name': 'state',
                'Values': [
                    'active',
                ]
            },
        ],
    )
    return [
        InstanceReservation(
            type = InstanceType(
                size              = ri['InstanceType'],
                availability_zone = ri['AvailabilityZone'] if ri['Scope'] == 'Availability Zone' else region,
                tenancy           = ri['InstanceTenancy'],
                product           = ri['ProductDescription'],
                vpc               = ri['ProductDescription'].endswith("(Amazon VPC)"),
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
        InstanceType(i['InstanceType'], i['Placement']['AvailabilityZone'], i['Placement']['Tenancy'], i.get('Platform', 'Linux/UNIX'), i.get('VpcId', '') != '')
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

def get_ec2_type_offerings(ec2, instance_type, container):
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
    try:
        offerings = sorted(offerings, key=reserved_instance_offering_cost_per_hour)
    except botocore.exceptions.ClientError:
        # Handling api limits
        return get_ec2_type_offerings(ec2, instance_type, container)
    try:
        offering_best = offerings[0]
        offering_worst = offerings[-1]
    except IndexError:
        return None
    ondemand = next(
        c
        for c in compute_instance_costs
        if (
            c['attributes']['instanceType'] == instance_type.size
            and c['attributes']['location'] == compute_sheet_region.get(az_to_region(instance_type.availability_zone), az_to_region(instance_type.availability_zone))
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
    container[instance_type] = res
    return res

def get_instance_offerings(ec2, instance_types):
    threads = []
    container = {}
    for ityp in instance_types:
        threads.append(Thread(target=get_ec2_type_offerings, args=(ec2, ityp, container)))

    # 4 threads max launched at a time (due to aws api limits)
    c = 0
    for i in range(1, len(threads)+1):
        threads[i-1].start()
        c += 1
        if i % 4 == 0 or i == len(threads):
            while c > 0:
                c -= 1
                threads[i-1-c].join()
                print("[{} - {}] Getting offerings for all instances {}/{}!".format(ACCOUNT, REGION, i-c, len(threads)))
            c = 0
    return [o for o in container.values() if o]

def instance_type_matches(pattern, example):
    def get_generic_type(instancetype):
        if instancetype.lower().startswith('windows') or instancetype.lower().startswith('suse'):
            return instancetype
        return 'Linux/UNIX'
    tmpPattern = pattern.type._replace(product=get_generic_type(pattern.type.product))
    tmpExample = example._replace(product=get_generic_type(pattern.type.product))
    if example.vpc == True:
        return (tmpPattern == example or tmpPattern == example._replace(vpc=False) or
        tmpPattern == tmpExample._replace(vpc=False, availability_zone=az_to_region(example.availability_zone)) or
        tmpPattern == tmpExample._replace(availability_zone=az_to_region(example.availability_zone)))
    else:
        return (tmpPattern == example or tmpPattern == example._replace(availability_zone=az_to_region(example.availability_zone)) or
        tmpPattern == tmpExample._replace(vpc=True) or
        tmpPattern == tmpExample._replace(vpc=True, availability_zone=az_to_region(example.availability_zone)))

def get_instance_matchings(instance_offerings, reserved_instances, ondemand_instances):
    remaining_reserved_instances = [
        [ri, ri.count]
        for ri in reserved_instances
    ]
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
        try:
            matches.append(
                InstanceMatching(
                    offering       = next(io for io in instance_offerings if (io.type == oi[0] or io.type == oi[0]._replace(product=oi[0].product+' (Amazon VPC)'))),
                    count          = oi[1],
                    count_reserved = reserved,
                )
            )
        except StopIteration:
            pass
    reservations_usage = [
        (ri, ri.count - remaining)
        for [ri, remaining] in remaining_reserved_instances
    ]
    return matches, reservations_usage


def get_ec2_reservation_data(ec2, region):
    print("[{} - {}] Getting reserved instances...".format(ACCOUNT, region))
    reserved_instances = mockdata.reserved_instances or get_reserved_instances(ec2, region)
    print("[{} - {}] Getting on-demand instances...".format(ACCOUNT, region))
    ondemand_instances = mockdata.ondemand_instances or get_ondemand_instance_types(ec2)
    print("[{} - {}] Getting offerings for all instances...".format(ACCOUNT, region))
    instance_offerings = mockdata.instance_offerings or get_instance_offerings(
        ec2,
        frozenset(oi[0] for oi in ondemand_instances) | frozenset(ri.type for ri in reserved_instances),
    )
    print("[{} - {}] Matching on-demand instances with reserved instances...".format(ACCOUNT, region))
    matched_instances, reservation_usage = get_instance_matchings(instance_offerings, reserved_instances, ondemand_instances)
    print("[{} - {}] Done!".format(ACCOUNT, region))
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
    matched_instances, reservation_usage = get_ec2_reservation_data(ec2, REGION)
    with open('{}/{}.{}.csv'.format(DIR_INSTANCE_RESERVATION_USAGE, ACCOUNT, REGION), 'w') as f:
        write_matched_instances(f, matched_instances)
    with open('{}/{}.{}.csv'.format(DIR_RESERVATION_USAGE, ACCOUNT, REGION), 'w') as f:
        write_reservation_usage(f, reservation_usage)

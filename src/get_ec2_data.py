#!/usr/bin/env python3

import collections
import csv
import itertools
import json
import re
import argparse
import multiprocessing.pool
from pprint import pprint
import boto3
import botocore

from mytypes import *

compute_sheet_region = {
    'us-east-2': 'US East (Ohio)',
    'us-east-1': 'US East (N. Virginia)',
    'us-west-1': 'US West (N. California)',
    'us-west-2': 'US West (Oregon)',
    'ap-northeast-1': 'Asia Pacific (Tokyo)',
    'ap-northeast-2': 'Asia Pacific (Seoul)',
    'ap-south-1': 'Asia Pacific (Mumbai)',
    'ap-southeast-1': 'Asia Pacific (Singapore)',
    'ap-southeast-2': 'Asia Pacific (Sydney)',
    'ca-central-1': 'Canada (Central)',
    'cn-north-1': 'China (Beijing)',
    'cn-northwest-1': 'China (Ningxia)',
    'eu-central-1': 'EU (Frankfurt)',
    'eu-west-1': 'EU (Ireland)',
    'eu-west-2': 'EU (London)',
    'eu-west-3': 'EU (Paris)',
    'sa-east-1': 'South America (Sao Paulo)',
}

compute_sheet_tenancy = {
    'dedicated': 'Dedicated',
    'host': 'Host',
    'default': 'Shared',
}

compute_sheet_platform = {
    'Linux/UNIX': 'Linux',
    'Linux/UNIX (Amazon VPC)': 'Linux',
    'SUSE Linux': 'SUSE',
    'SUSE Linux (Amazon VPC)': 'SUSE',
    'Red Hat Enterprise Linux': 'RHEL',
    'Red Hat Enterprise Linux (Amazon VPC)': 'RHEL',
    'Windows': 'Windows',
    'windows': 'Windows',
    'Windows (Amazon VPC)': 'Windows',
    'windows (Amazon VPC)': 'Windows',
    'Windows with SQL Server Standard': 'Windows',
    'windows with SQL Server Standard': 'Windows',
    'Windows with SQL Server Standard (Amazon VPC)': 'Windows',
    'windows with SQL Server Standard (Amazon VPC)': 'Windows',
    'Windows with SQL Server Web': 'Windows',
    'windows with SQL Server Web': 'Windows',
    'Windows with SQL Server Web (Amazon VPC)': 'Windows',
    'windows with SQL Server Web (Amazon VPC)': 'Windows',
    'Windows with SQL Server Enterprise': 'Windows',
    'windows with SQL Server Enterprise': 'Windows',
    'Windows with SQL Server Enterprise (Amazon VPC)': 'Windows',
    'windows with SQL Server Enterprise (Amazon VPC)': 'Windows',
}

DIR_BILLS = 'in/usagecost'
DIR_INSTANCE_RESERVATION_USAGE = 'out/instance-reservation-usage'
DIR_RESERVATION_USAGE = 'out/reservation-usage'
FIL_ONDEMAND_COSTS = 'in/ondemandcosts.json'

with open(FIL_ONDEMAND_COSTS) as f:
    compute_instance_costs = json.load(f)

_az_to_region_re = re.compile(r'^(.+?)[a-z]?$')


def az_to_region(az):
    return _az_to_region_re.match(az).group(1)


def identity(x):
    return x


boto_sessions = {}


def boto_session_getter(profile, region):
    global boto_sessions
    if (profile, region) in boto_sessions:
        return boto_sessions[(profile, region)]
    session = boto3.Session(profile_name=profile, region_name=region)
    ec2 = session.client('ec2')
    boto_sessions[(profile, region)] = ec2
    return ec2


def reserved_instance_offering_cost_per_hour(offering):
    return offering['FixedPrice'] / (offering['Duration'] / 3600) + (
        offering['RecurringCharges'][0]['Amount'] if len(
            offering['RecurringCharges']) > 0 else 0.0)


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
        InstanceReservationCount(
            instance_reservation=InstanceReservation(
                type=InstanceType(
                    size=ri['InstanceType'],
                    availability_zone=ri['AvailabilityZone'] if ri[
                                                                    'Scope'] == 'Availability Zone' else region,
                    tenancy=ri['InstanceTenancy'],
                    product=ri['ProductDescription'],
                    vpc=ri['ProductDescription'].endswith("(Amazon VPC)"),
                ),
                cost_hourly=sum(rc['Amount'] for rc in ri['RecurringCharges']),
                cost_upfront=ri['FixedPrice'],
            ),
            count=ri['InstanceCount'],
            count_used=0,
        )
        for ri in reserved_instances_data['ReservedInstances']
    ]


def get_ondemand_instance_types(ec2, profile):
    def get_instance_type(instance_type):
        if instance_type == "windows":
            return "Windows"
        return instance_type

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
    reservations = itertools.chain.from_iterable(
        p['Reservations'] for p in pages)
    instances = itertools.chain.from_iterable(
        r['Instances'] for r in reservations)
    return [
        InstanceTypeWithProfile(
            profile=profile,
            instance_type=InstanceType(
                size=i['InstanceType'],
                availability_zone=i['Placement']['AvailabilityZone'],
                tenancy=i['Placement']['Tenancy'],
                product=get_instance_type(i.get('Platform', 'Linux/UNIX')),
                vpc=i.get('VpcId', '') != '',
            )
        )
        for i in instances
        if i.get('InstanceLifecycle', 'ondemand') == 'ondemand'
    ]


def get_ec2_type_offerings(ec2, instance_type):
    offerings = itertools.chain.from_iterable(
        page['ReservedInstancesOfferings']
        for page in
        ec2.get_paginator('describe_reserved_instances_offerings').paginate(
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
        offerings = sorted(offerings,
                           key=reserved_instance_offering_cost_per_hour)
    except botocore.exceptions.ClientError:
        # Handling api limits
        return get_ec2_type_offerings(ec2, instance_type)
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
                and c['attributes']['location'] == compute_sheet_region.get(
            az_to_region(instance_type.availability_zone),
            az_to_region(instance_type.availability_zone))
                and c['attributes']['tenancy'] == compute_sheet_tenancy[
                    instance_type.tenancy]
                and c['attributes']['operatingSystem'] ==
                compute_sheet_platform[instance_type.product]
        )
    )['cost']
    res = InstanceOffering(
        type=instance_type,
        cost_reserved_worst=reserved_instance_offering_cost_per_hour(
            offering_worst),
        cost_reserved_best=reserved_instance_offering_cost_per_hour(
            offering_best),
        cost_ondemand=ondemand,
    )
    return res


def instance_type_matches(pattern, example):
    def get_generic_type(instancetype):
        if instancetype.lower().startswith(
                'windows') or instancetype.lower().startswith('suse'):
            return instancetype
        return 'Linux/UNIX'

    tmpPattern = pattern.type._replace(
        product=get_generic_type(pattern.type.product))
    tmpExample = example._replace(
        product=get_generic_type(pattern.type.product))
    if example.vpc == True:
        return (tmpPattern == example or tmpPattern == example._replace(
            vpc=False) or
                tmpPattern == tmpExample._replace(vpc=False,
                                                  availability_zone=az_to_region(
                                                      example.availability_zone)) or
                tmpPattern == tmpExample._replace(
                    availability_zone=az_to_region(example.availability_zone)))
    else:
        return (tmpPattern == example or tmpPattern == example._replace(
            availability_zone=az_to_region(example.availability_zone)) or
                tmpPattern == tmpExample._replace(vpc=True) or
                tmpPattern == tmpExample._replace(vpc=True,
                                                  availability_zone=az_to_region(
                                                      example.availability_zone)))


def get_instance_matchings(offerings, reservations):
    instance_offerings_counted = [
        InstanceOfferingCount(
            instance_offering=instance_offering,
            count=count,
            count_reserved=0,
        )
        for instance_offering, count in offerings.items()
    ]
    remaining_reserved_instances = [
        [ri, count]
        for ri, count in reservations.items()
    ]
    matched_instances = []
    for oi in sorted(instance_offerings_counted, reverse=True,
                     key=lambda x: x.instance_offering.type.availability_zone[
                                   ::-1]):
        matching_reserved = (
            rri
            for rri in sorted(remaining_reserved_instances, reverse=True,
                              key=lambda i: i[0].type.availability_zone[::-1])
            if rri[1] > 0 and instance_type_matches(rri[0], oi.instance_offering.type)
        )
        reserved = 0
        while reserved < oi.count:
            try:
                ri = next(matching_reserved)
            except StopIteration:
                break
            use = min(ri[1], oi.count - reserved)
            ri[1] -= use
            reserved += use
        matched_instances.append(oi._replace(count_reserved=reserved))
    reservation_usage = [
        InstanceReservationCount(
            instance_reservation=ri,
            count=reservations[ri],
            count_used=reservations[ri] - remaining,
        )
        for [ri, remaining] in remaining_reserved_instances
    ]
    return matched_instances, reservation_usage


def get_ec2_reservations(profiles, region):
    reservations = collections.defaultdict(int)
    for profile in profiles:
        print('[{} - {}] Getting reserved instances...'.format(profile, region))
        ec2 = boto_session_getter(profile, region)
        reserved_instances = get_reserved_instances(ec2, region)
        for ri in reserved_instances:
            reservations[ri.instance_reservation] += ri.count
    return reservations


def get_ec2_instances(profiles, region):
    instances = collections.defaultdict(int)
    for profile in profiles:
        print('[{} - {}] Getting on-demand instances...'.format(profile, region))
        ec2 = boto_session_getter(profile, region)
        instance_types = get_ondemand_instance_types(ec2, profile)
        for it in instance_types:
            instances[it] += 1
    return instances


def get_ec2_offerings(instances, region):
    with multiprocessing.pool.ThreadPool(processes=4) as pool:
        offerings = collections.defaultdict(int)
        tasks = []
        print('[global - {}] Getting offerings for all instances...'.format(region))
        for instance, count in instances.items():
            ec2 = boto_session_getter(instance.profile, region)
            tasks.append({
                'profile': instance.profile,
                'instance_type': instance.instance_type,
                'instance_count': count,
                'task': pool.apply_async(get_ec2_type_offerings,
                                         [ec2, instance.instance_type]),
            })
            # offering = get_ec2_type_offerings(ec2, instance)
        for i, task in zip(itertools.count(1), tasks):
            print('[{} - {}] Getting offerings for instance {}/{}...'.format(
                instance.profile, region, i, len(instances)))
            offering = task['task'].get()
            if offering:
                offerings[offering] += task['instance_count']
    return offerings


def get_ec2_data(profiles, region):
    reservations = get_ec2_reservations(profiles, region)
    instances = get_ec2_instances(profiles, region)
    offerings = get_ec2_offerings(instances, region)
    print('[global - {}] Matching on-demand instances with reserved instances...'.format(region))
    matched_instances, reservation_usage = get_instance_matchings(offerings,
                                                                  reservations)
    print('[global - {}] Done!'.format(region))
    return matched_instances, reservation_usage


def write_matched_instances(f, matched_instances, header=True):
    writer = csv.DictWriter(f, fieldnames=[
        'instance_type',
        'availability_zone',
        'tenancy',
        'product',
        'cost_ondemand',
        'cost_reserved_worst',
        'cost_reserved_best',
        'count',
        'count_reserved',
    ])
    if header:
        writer.writeheader()
    for mi in matched_instances:
        writer.writerow({
            'instance_type': mi.instance_offering.type.size,
            'availability_zone': mi.instance_offering.type.availability_zone,
            'tenancy': mi.instance_offering.type.tenancy,
            'product': mi.instance_offering.type.product,
            'cost_ondemand': mi.instance_offering.cost_ondemand,
            'cost_reserved_worst': mi.instance_offering.cost_reserved_worst,
            'cost_reserved_best': mi.instance_offering.cost_reserved_best,
            'count': mi.count,
            'count_reserved': mi.count_reserved,
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
    for ru in reservation_usage:
        writer.writerow({
            'instance_type': ru.instance_reservation.type.size,
            'availability_zone': ru.instance_reservation.type.availability_zone,
            'tenancy': ru.instance_reservation.type.tenancy,
            'product': ru.instance_reservation.type.product,
            'cost_hourly': ru.instance_reservation.cost_hourly,
            'cost_upfront': ru.instance_reservation.cost_upfront,
            'count': ru.count,
            'count_used': ru.count_used,
        })


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', help='aws region', required=True)
    parser.add_argument('--profile', help='aws profile', required=True, nargs='+')
    args = parser.parse_args()
    matched_instances, reservation_usage = get_ec2_data(args.profile,
                                                        args.region)
    with open('{}/{}.csv'.format(DIR_INSTANCE_RESERVATION_USAGE, args.region),
              'w') as f:
        write_matched_instances(f, matched_instances)
    with open('{}/{}.csv'.format(DIR_RESERVATION_USAGE, args.region), 'w') as f:
        write_reservation_usage(f, reservation_usage)

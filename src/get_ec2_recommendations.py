#!/usr/bin/env python3

import collections
import datetime
import re
import csv

import boto3

# Normalization factors can be found at
# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-modifying.html#ri-modification-instancemove
NORM_FACTOR = collections.OrderedDict([
    ('nano'     , 1)       ,
    ('micro'    , 2)       ,
    ('small'    , 1 * 4)   ,
    ('medium'   , 2 * 4)   ,
    ('large'    , 4 * 4)   ,
    ('xlarge'   , 8 * 4)   ,
    ('2xlarge'  , 16 * 4)  ,
    ('4xlarge'  , 32 * 4)  ,
    ('8xlarge'  , 64 * 4)  ,
    ('9xlarge'  , 72 * 4)  ,
    ('10xlarge' , 80 * 4)  ,
    ('12xlarge' , 96 * 4)  ,
    ('16xlarge' , 128 * 4) ,
    ('18xlarge' , 144 * 4) ,
    ('24xlarge' , 192 * 4) ,
    ('32xlarge' , 256 * 4) ,
])

TARGET_CPU_USAGE = 0.80
CPU_USAGE_INTERVAL = datetime.timedelta(hours=24)
CPU_USAGE_INTERVAL_SECOND = CPU_USAGE_INTERVAL.days * 24 * 3600 + CPU_USAGE_INTERVAL.seconds
DIR_RECOMMENDATION = 'out/instance-size-recommendation'

REGION=boto3._get_default_session().region_name
ACCOUNT=boto3.client('sts').get_caller_identity()['Account']

InstanceSize = collections.namedtuple('InstanceSize', ['family', 'size'])
InstanceRecommendation = collections.namedtuple('InstanceRecommendation', [
    'account',
    'id',
    'name',
    'size',
    'lifecycle',
    'cpu_usage',
    'recommendation',
    'reason',
])

def next_or(it, default):
    try:
        return next(it)
    except StopIteration:
        return default

def next_or_none(it):
    return next_or(it, None)

_str_to_instance_size_re = re.compile(r'([a-z]+[0-9])\.(nano|micro|small|medium|(?:[0-9]*x?large))')
def str_to_instance_size(s):
    m = _str_to_instance_size_re.match(s)
    if m:
        return InstanceSize(
            family=m.group(1),
            size=m.group(2),
        )

def instance_size_to_str(instance_size):
    return '{}.{}'.format(*instance_size)

def recommended_size(size, cpu_usage):
    current_norm_factor = NORM_FACTOR[size]
    cpu_delta = cpu_usage / TARGET_CPU_USAGE
    target_norm_factor = cpu_delta * current_norm_factor
    matching_norm_factor = next(size for size, norm_factor in NORM_FACTOR.items() if norm_factor >= target_norm_factor)
    return matching_norm_factor

def get_reason(cpu_usage, current_size, recommendation):
    if cpu_usage is None:
        return 'insufficient_data'
    elif cpu_usage > 0.80:
        return 'High CPU usage average: {0:.3f}%'.format(cpu_usage*100)
    elif current_size == recommendation:
        return 'Optimal CPU usage average'
    return 'Low CPU usage average: {0:.3f}%'.format(cpu_usage*100)

def get_cpu_usage(cloudwatch, now, instance_id):
    usage_statistics = cloudwatch.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[
            { 'Name': 'InstanceId', 'Value': instance_id },
        ],
        StartTime=now - CPU_USAGE_INTERVAL,
        EndTime=now,
        Period=CPU_USAGE_INTERVAL_SECOND,
        Statistics=['Average']
    )
    try:
        return usage_statistics['Datapoints'][0]['Average'] / 100
    except IndexError:
        return None

def get_recommendation(instance):
        instance_type_str = instance['InstanceType']
        instance_type = str_to_instance_size(instance_type_str)
        instance_id = instance['InstanceId']
        instance_name = next_or((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), '')
        instance_lifecycle = instance.get('InstanceLifecycle', 'ondemand')
        cpu_usage = get_cpu_usage(cloudwatch, now, instance_id)
        recommendation = recommended_size(instance_type.size, cpu_usage) if cpu_usage is not None else 'insufficient_data'
        reason = get_reason(cpu_usage, instance_type.size, recommendation)
        return InstanceRecommendation(
            id=instance_id,
            name=instance_name,
            size=instance_type_str,
            lifecycle=instance_lifecycle,
            cpu_usage=cpu_usage or "",
            recommendation=recommendation,
            reason=reason,
            account=ACCOUNT,
        )

def main(ec2, cloudwatch, now):
    instances = (
        instance
        for page in ec2.get_paginator('describe_instances').paginate()
        for reservation in page['Reservations']
        for instance in reservation['Instances']
    )
    recommendations = (
        get_recommendation(instance)
        for instance in instances
    )
    recommendations = sorted(recommendations, key=lambda r: (r.name, r.size))
    with open('{}/{}.{}.csv'.format(DIR_RECOMMENDATION, ACCOUNT, REGION), 'w') as f:
        writer = csv.writer(f)
        writer.writerow(InstanceRecommendation._fields)
        for recommendation in recommendations:
            writer.writerow(recommendation)

if __name__ == '__main__':
    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')
    now = datetime.datetime.now()
    main(ec2, cloudwatch, now)

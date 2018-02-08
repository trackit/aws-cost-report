#!/usr/bin/env python3

import csv
import sys
import collections
import datetime
import itertools
import os

def rows_folder(dirpath):
    for filename in os.listdir(dirpath):
        filepath = os.path.join(dirpath, filename)
        with open(filepath) as f:
            for row in rows(f):
                yield row

def parseIsoDatetime(isodatetime):
    return datetime.datetime.strptime(isodatetime.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S%z')

def rows(csvfile):
    reader = csv.DictReader(csvfile)
    for row in reader:
        yield row

def window(l, n=2):
    for i in range(len(l) - n + 1):
        yield l[i:i+n]

def variations(costs):
    return [
        "" if old <= .0 else (new / old) - 1
        for [old, new] in window([0, *costs])
    ]

def yearmonth_to_string(yearmonth):
    year, month = divmod(yearmonth, 12)
    return '{:04d}-{:02d}'.format(year, month + 1)

first_month = -1
last_month = -1
breakdown = collections.defaultdict(float)

for row in rows_folder('usagecost'):
    usage_start_date = parseIsoDatetime(row['lineItem/UsageStartDate'])
    month = usage_start_date.year * 12 + usage_start_date.month - 1
    first_month = month if first_month == -1 else min(month, first_month)
    last_month = month if last_month == -1 else max(month, last_month)
    usagetype = row['lineItem/UsageType']
    breakdown[(month, usagetype)] += float(row['lineItem/UnblendedCost'])

with open('months.csv', 'w') as monthsfile:
    writer = csv.writer(monthsfile)
    writer.writerow(['month', 'usage', 'cost'])
    for key, value in breakdown.items():
        writer.writerow([*key, value])

#with open('months.csv') as monthsfile:
#    for row in rows(monthsfile):
#        breakdown[(int(row['month']), row['usage'])] = float(row['cost'])
#        first_month = int(row['month']) if first_month == -1 else min(int(row['month']), first_month)
#        last_month = int(row['month']) if last_month == -1 else max(int(row['month']), last_month)

print(first_month)
print(last_month)

breakdown_by_date = collections.defaultdict(lambda: list([.0] * (last_month - first_month + 1)))
for (month, product), cost in breakdown.items():
    breakdown_by_date[product][month - first_month] += cost

with open('absolute.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['usage'] + [yearmonth_to_string(ym) for ym in range(first_month, last_month + 1)])
    for product, month_cost in breakdown_by_date.items():
        writer.writerow([product, *month_cost])

breakdown_variation = {}
for (product, monthly_costs) in breakdown_by_date.items():
    breakdown_variation[product] = variations(monthly_costs)

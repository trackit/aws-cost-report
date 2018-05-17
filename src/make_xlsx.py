#!/usr/bin/env python3

import collections
import csv
import itertools
import json
import datetime
import os
import pprint
import xlsxwriter
from datetime import datetime
import dateutil.relativedelta
import sys

from sheets import *
import utils

SHEET_RESERVATIONS_SUMMARY = 1

PRETTY_FIELD_NAMES = {
    'instance_type': 'Instance type',
    'availability_zone': 'Availability zone',
    'tenancy': 'Tenancy',
    'product': 'Product',
    'count': 'Count',
    'count_reserved': 'Count (reserved)',
    'cost_ondemand': 'Cost (on demand)',
    'cost_reserved_worst': 'Cost (worst reserved)',
    'cost_reserved_best': 'Cost (best reserved)',
}

PRETTY_FIELD_GROUPS = {
    'reservation': 'Reservation',
    'hourly_cost_per_instance': 'Hourly cost per instance',
}

NUMFORMAT_CURRENCY = '#,##0.000 [$USD]'
NUMFORMAT_PERCENT = '0.00%'
NUMFORMAT_PERCENT_VAR = '\+0.00%;\-0.00%'

IN_INSTANCE_RESERVATION_USAGE_DIR    = 'out/instance-reservation-usage'
IN_RESERVATION_USAGE_DIR             = 'out/reservation-usage'
IN_ABSOLUTE_COST_PER_MONTH           = 'out/absolute.csv'
IN_INSTANCE_SIZE_RECOMMENDATIONS_DIR = 'out/instance-size-recommendation'
IN_INSTANCE_HISTORY                  = 'out/instance-history.csv'
IN_INSTANCE_USAGE_LAST_MONTH         = 'out/last-month/ec2_instances.csv'
IN_EC2_BANDWIDTH_USAGE_LAST_MONTH    = 'out/last-month/ec2_bandwidth.csv'
IN_EBS_USAGE_LAST_MONTH              = 'out/last-month/ebs.csv'
IN_SNAPSHOT_USAGE_LAST_MONTH         = 'out/last-month/snapshots.csv'

COLOR_RED_BG = "#ffcccc"
COLOR_RED_FG = "#cc0000"
COLOR_GREEN_BG = "#ccffcc"
COLOR_GREEN_FG = "#006600"


def _with_trailing(it, trail):
    return itertools.chain(it, itertools.repeat(trail))


def gen_reserved_summary(workbook, header_format, val_format):
    with utils.csv_folder(IN_INSTANCE_RESERVATION_USAGE_DIR) as records:
        worksheet = workbook.add_worksheet("Reserved instance summary")

        worksheet.set_column("A:N", 15)
        worksheet.merge_range("A1:D1", "Reservation", header_format)
        worksheet.merge_range("E1:F1", "Count", header_format)
        worksheet.merge_range("G1:I1", "Cost per instance", header_format)
        worksheet.merge_range("J1:L1", "Total monthly cost", header_format)
        worksheet.merge_range("M1:N1", "Savings over on demand", header_format)

        green_format = workbook.add_format()
        green_format.set_color(COLOR_GREEN_FG)
        green_format.set_bg_color(COLOR_GREEN_BG)

        cur_format = workbook.add_format()
        cur_format.set_align("center")
        cur_format.set_align("vcenter")
        cur_format.set_border()
        cur_format.set_num_format(NUMFORMAT_CURRENCY)

        per_format = workbook.add_format()
        per_format.set_align("center")
        per_format.set_align("vcenter")
        per_format.set_border()
        per_format.set_num_format(NUMFORMAT_PERCENT)

        refs = {
            "instance_type": [0, "Instance type", str, val_format],
            "availability_zone": [1, "Availability zone", str, val_format],
            "tenancy": [2, "Tenancy", str, val_format],
            "product": [3, "Product", str, val_format],
            "count": [4, "Running", int, val_format],
            "count_reserved": [5, "Reserved", int, val_format],
            "cost_ondemand": [6, "On demand", float, cur_format],
            "cost_reserved_worst": [7, "Worst reserved", float, cur_format],
            "cost_reserved_best": [8, "Best reserved", float, cur_format],
            "cost_monthly_ondemand": [9, "On demand", float, cur_format],
            "cost_monthly_reserved_worst": [10, "Worst reserved", float, cur_format],
            "cost_monthly_reserved_best": [11, "Best reserved", float, cur_format],
            "savings_reserved_worst": [12, "Worst reserved", float, per_format],
            "savings_reserved_best": [13, "Best reserved", float, per_format],
        }
        for v in refs.values():
            worksheet.write(1, v[0], v[1], header_format)
        for i, line in zip(itertools.count(2), records):
            for h, v in line.items():
                worksheet.write(i, refs[h][0], refs[h][2](v), refs[h][3])
            for h in ("cost_monthly_ondemand", "cost_monthly_reserved_worst", "cost_monthly_reserved_best"):
                res = float(line["count"]) * \
                    float(line["cost_" + h[13:]]) * 720
                worksheet.write_formula(
                    i, refs[h][0],
                    "=E{}*{}{}*720".format(i+1, chr(ord('A') +
                                                    refs[h][0] - 3), i+1), refs[h][3],
                    res,
                )
            for h in ("savings_reserved_worst", "savings_reserved_best"):
                res = 1 - float(line[h.replace("savings", "cost")]
                                ) / float(line["cost_ondemand"])
                worksheet.write_formula(
                    i, refs[h][0],
                    "=1-{}{}/G{}".format(chr(ord('A') +
                                             refs[h][0] - 5), i+1, i+1), refs[h][3],
                    res,
                )
            worksheet.conditional_format("F{}".format(i+1), {
                "type": "cell",
                "criteria": "equal to",
                "value": "E{}".format(i+1),
                "format": green_format,
            })


def gen_reservation_usage_summary(workbook, header_format, val_format):
    with utils.csv_folder(IN_RESERVATION_USAGE_DIR) as records:
        worksheet = workbook.add_worksheet("Reservation usage summary")

        worksheet.set_column("A:J", 18)
        worksheet.merge_range("A1:D1", "Reservation", header_format)
        worksheet.merge_range("E1:F1", "Count", header_format)
        worksheet.merge_range("G1:I1", "Cost per instance", header_format)
        worksheet.merge_range("J1:J2", "Monthly losses", header_format)

        cur_format = workbook.add_format()
        cur_format.set_align("center")
        cur_format.set_align("vcenter")
        cur_format.set_border()
        cur_format.set_num_format(NUMFORMAT_CURRENCY)

        refs = {
            "instance_type": [0, "Instance type", str, val_format],
            "availability_zone": [1, "Availability zone", str, val_format],
            "tenancy": [2, "Tenancy", str, val_format],
            "product": [3, "Product", str, val_format],
            "count": [4, "Reserved", int, val_format],
            "count_used": [5, "Used", int, val_format],
            "cost_upfront": [6, "Upfront", float, cur_format],
            "cost_hourly": [7, "Hourly", float, cur_format],
            "effective_cost": [8, "Effective", float, cur_format],
            "monthly_losses": [9, "Monthly losses", float, cur_format],
        }
        for v in refs.values():
            worksheet.write(1, v[0], v[1], header_format)
        for i, line in zip(itertools.count(2), records):
            for h, v in line.items():
                worksheet.write(i, refs[h][0], refs[h][2](v), refs[h][3])
            effective_cost = float(
                line["cost_upfront"]) / 720 + float(line["cost_hourly"])
            worksheet.write_formula(
                i, refs["effective_cost"][0],
                "=G{}/720+H{}".format(*[i+1]*2), refs["effective_cost"][3],
                effective_cost,
            )
            worksheet.write(
                i, refs["monthly_losses"][0],
                "=(E{}-F{})*I{}*720".format(*[i+1]
                                            * 3), refs["monthly_losses"][3],
                (float(line["count"]) - float(line["count_used"])
                 ) * effective_cost * 720,
            )


def gen_weekly_variations(workbook, header_format, val_format):
    def to_alpha(x): return chr(ord('A') + x)

    with open(IN_ABSOLUTE_COST_PER_MONTH) as f:
        reader = csv.DictReader(f)
        source = sorted(
            reader,
            key=(lambda row: sum(float(v)
                                 for k, v in row.items() if k != 'usage')),
            reverse=True,
        )
        worksheet = workbook.add_worksheet("Cost variations")

        worksheet.set_column("A:A", 30)
        worksheet.set_column("B:M", 14)
        worksheet.merge_range("A1:A3", "Usage type", header_format)
        worksheet.merge_range("B1:L1", "Monthly cost", header_format)
        worksheet.merge_range("M1:M3", "Total", header_format)

        green_format = workbook.add_format()
        green_format.set_color(COLOR_GREEN_FG)
        green_format.set_bg_color(COLOR_GREEN_BG)

        red_format = workbook.add_format()
        red_format.set_color(COLOR_RED_FG)
        red_format.set_bg_color(COLOR_RED_BG)

        cur_format = workbook.add_format()
        cur_format.set_align("center")
        cur_format.set_align("vcenter")
        cur_format.set_border()
        cur_format.set_num_format(NUMFORMAT_CURRENCY)

        per_format = workbook.add_format()
        per_format.set_align("center")
        per_format.set_align("vcenter")
        per_format.set_border()
        per_format.set_num_format(NUMFORMAT_PERCENT)

        date_fieldnames = reader.fieldnames[1:-1]
        if len(date_fieldnames) > 6:
            date_fieldnames = date_fieldnames[-5:]
        refs = {
            header: [i, True, float]
            for i, header in zip(itertools.count(3, 2), date_fieldnames[1:])
        }
        refs[date_fieldnames[0]] = [1, False, float]
        refs["usage"] = [0, False, str]
        for h, v in refs.items():
            if v[1]:
                worksheet.merge_range(1, v[0]-1, 1, v[0], h, header_format)
                worksheet.write(2, v[0]-1, "Variation", header_format)
                worksheet.write(2, v[0], "Cost", header_format)
            else:
                worksheet.write(1, v[0], h, header_format)
                worksheet.write(2, v[0], "Cost", header_format)
        for i, line in zip(itertools.count(3), source):
            for name, meta in refs.items():
                val = line[name]
                worksheet.write(i, meta[0], meta[2](val), cur_format)
                if meta[1]:
                    before = float(line[date_fieldnames[int(meta[0]/2-1)]])
                    worksheet.write_formula(
                        i, meta[0]-1,
                        "=IF({}{}=0,\"\",{}{}/{}{}-1)".format(
                            to_alpha(meta[0] - 2),
                            i+1,
                            to_alpha(meta[0]),
                            i+1,
                            to_alpha(meta[0] - 2),
                            i+1,
                        ), per_format,
                        " " if before == 0.0 else meta[2](val) / before - 1
                    )
                    worksheet.conditional_format("{}{}".format(to_alpha(meta[0]-1), i+1), {
                        "type": "cell",
                        "criteria": "greater than",
                        "value": "0",
                        "format": red_format,
                    })
                    worksheet.conditional_format("{}{}".format(to_alpha(meta[0]-1), i+1), {
                        "type": "cell",
                        "criteria": "less than or equal to",
                        "value": "0",
                        "format": green_format,
                    })
            worksheet.write("M{}".format(
                i+1), sum([float(line[o]) for o in reader.fieldnames[1:]]), cur_format)


def gen_weekly_variations_chart(workbook, header_format, val_format):
    with open(IN_ABSOLUTE_COST_PER_MONTH) as f:
        reader = csv.DictReader(f)
        source = sorted(
            reader,
            key=(lambda row: sum(float(v) for k, v in row.items() if k != 'usage')),
            reverse=True,
        )[:5]

        header = ['usage'] + sorted([s for s in source[0] if s != 'usage'])
        data = [
            [float(s[h]) if h != 'usage' else s[h] for h in header]
            for s in source
        ]
        chart = workbook.add_chart({
            "type": "line"
        })
        chartsheet = workbook.add_worksheet("Cost variations chart")
        chartsheet.add_table(1, 1, len(data)+1, len(header)-1, {'data': data, 'columns': [{'header': h} for h in header]})
        for i in range(2, len(data)+1):
            chart.add_series({
                "values": ["Cost variations chart", i, 2, i, len(header)-1],
                "categories": ["Cost variations chart", 1, 2, 1, len(header)-1],
                "name": ["Cost variations chart", i, 1],
            })
        chartsheet.insert_chart('A1', chart, {'x_scale': 3, 'y_scale': 2})


def gen_instance_count_history(workbook, header_format, val_format):
    with open(IN_INSTANCE_HISTORY) as f:
        reader = csv.DictReader(f)
        worksheet = workbook.add_worksheet("Instance count history")

        worksheet.set_column(0, len(reader.fieldnames)-1, 18)
        worksheet.merge_range("A1:A2", "Date", header_format)
        worksheet.merge_range(0, 1, 0, len(
            reader.fieldnames)-1, "Instance Count", header_format)

        def transform(x):
            try:
                if x == "":
                    return 0
                else:
                    return int(x)
            except ValueError:
                return x

        refs = {
            header: [
                i,
                transform,
            ] for i, header in zip(itertools.count(), reader.fieldnames)
        }
        for h, v in refs.items():
            worksheet.write(1, v[0], h, header_format)
        for i, line in zip(itertools.count(2), reader):
            for h, v in line.items():
                worksheet.write(i, refs[h][0], refs[h][1](v), val_format)


def gen_instance_count_history_chart(workbook, header_format, val_format):
    with open(IN_INSTANCE_HISTORY) as f:
        reader = csv.DictReader(f)

        chart = workbook.add_chart({
            "type": "line"
        })
        row_len = len(list(reader))
        for i, fieldname in zip(itertools.count(1), reader.fieldnames[1:]):
            chart.add_series({
                "values": ["Instance count history", 2, i, row_len-1, i],
                "categories": ["Instance count history", 2, 0, row_len-1, 0],
                "name": fieldname,
            })
        chartsheet = workbook.add_chartsheet("Instance count history chart")
        chartsheet.set_chart(chart)


def gen_instance_size_recommendations(workbook, header_format, val_format):
    def transform(h, v):
        if h == "cpu_usage":
            try:
                return "%.3f%%" % (float(v)*100)
            except ValueError:
                pass
        return v

    with utils.csv_folder(IN_INSTANCE_SIZE_RECOMMENDATIONS_DIR) as source:
        worksheet = workbook.add_worksheet("Instance size recommendations")

        worksheet.set_column("A:E", 25)
        worksheet.set_column("F:F", 20)
        worksheet.set_column("G:G", 18)
        worksheet.set_column("H:H", 35)
        worksheet.merge_range("A1:F1", "Instance", header_format)
        worksheet.merge_range("G1:G2", "Recommended", header_format)
        worksheet.merge_range("H1:H2", "Reason", header_format)

        refs = {
            "account": [0, "Account"],
            "id": [1, "ID"],
            "name": [2, "Name"],
            "size": [3, "Type"],
            "lifecycle": [4, "Lifecycle"],
            "cpu_usage": [5, "CPU Utilization (Avg.)"],
            "recommendation": [6, "Recommendation"],
            "reason": [7, "Reason"]
        }
        for i in refs.values():
            worksheet.write(1, i[0], i[1], header_format)
            for i, line in zip(itertools.count(2), source):
                for h, v in line.items():
                    worksheet.write(i, refs[h][0], transform(h, v), val_format)

def instance_summary(workbook, header_format, val_format):
    bandwidth_usage = {}
    def transform(x):
        try:
            if x == "": return 0.0
            else: return float(x)
        except ValueError:
            return x
    with open(IN_EC2_BANDWIDTH_USAGE_LAST_MONTH) as f:
        reader = csv.reader(f)
        for i, line in itertools.islice(zip(itertools.count(2), reader), 1, None):
            bandwidth_usage[line[0]] = transform(line[1])
    with open(IN_INSTANCE_USAGE_LAST_MONTH) as f:
        reader = csv.DictReader(f)
        worksheet = workbook.add_worksheet("EC2 instances last month")

        last_month = datetime.now() + dateutil.relativedelta.relativedelta(months=-1)
        worksheet.merge_range("A1:G1", "Instances for {}-{:02d}".format(last_month.year, last_month.month), header_format)
        worksheet.merge_range("H1:H2", "Total", header_format)

        cur_format = workbook.add_format()
        cur_format.set_align("center")
        cur_format.set_align("vcenter")
        cur_format.set_border()
        cur_format.set_num_format(NUMFORMAT_CURRENCY)

        worksheet.set_column(2, len(reader.fieldnames)+1, 18)
        worksheet.set_column("A:B", 33)

        refs = {
            "ResourceId": [0, "Resource Id", str, val_format],
            "Name": [1, "Name", str, val_format],
            "AvailabilityZone": [2, "Availability zone", str, val_format],
            "Term": [3, "Term", str, val_format],
            "Type": [4, "Type", str, val_format],
            "Cost": [5, "Instance cost", transform, cur_format],
            "Bandwidth": [6, "Bandwidth cost", transform, cur_format],
        }
        ec2_cost_data = []
        for i, line in zip(itertools.count(2), reader):
            line['Bandwidth'] = refs['Bandwidth'][2](bandwidth_usage.get(line['ResourceId'], ''))
            line['Total'] = refs['Bandwidth'][2](line['Cost']) + line['Bandwidth']
            ec2_cost_data.append(line)
        ec2_cost_data.sort(key=lambda e: e['Total'], reverse=True)
        for v in refs.values():
            worksheet.write(1, v[0], v[1], header_format)
        for i, line in zip(itertools.count(2), ec2_cost_data):
            for h, v in line.items():
                if h == 'Total':
                    continue
                worksheet.write(i, refs[h][0], refs[h][2](v), refs[h][3])
            worksheet.write(i, len(refs), line['Total'], cur_format)

def ebs_summary(workbook, header_format, val_format):
    def transform(x):
        try:
            if x == "": return 0.0
            else: return float(x)
        except ValueError:
            return x
    with open(IN_EBS_USAGE_LAST_MONTH) as f:
        reader = csv.DictReader(f)
        worksheet = workbook.add_worksheet("EBS last month")

        last_month = datetime.now() + dateutil.relativedelta.relativedelta(months=-1)
        worksheet.merge_range("A1:E1", "EBS for {}-{:02d}".format(last_month.year, last_month.month), header_format)
        worksheet.merge_range("A2:A3", "Resource ID", header_format)
        worksheet.merge_range("B2:B3", "Region", header_format)
        worksheet.merge_range("C2:C3", "Cost", header_format)
        worksheet.merge_range("D2:E2", "Instance Linked", header_format)

        cur_format = workbook.add_format()
        cur_format.set_align("center")
        cur_format.set_align("vcenter")
        cur_format.set_border()
        cur_format.set_num_format(NUMFORMAT_CURRENCY)

        worksheet.set_column(0, len(reader.fieldnames)-1, 25)

        refs = {
            "ResourceId": [0, "Resource Id", str, val_format],
            "Region": [1, "Region", str, val_format],
            "Cost": [2, "Cost", transform, cur_format],
            "InstanceId": [3, "ID", str, val_format],
            "InstanceName": [4, "Name", str, val_format],
        }
        for v in refs.values():
            worksheet.write(2, v[0], v[1], header_format)
        for i, line in zip(itertools.count(3), reader):
            for h, v in line.items():
                worksheet.write(i, refs[h][0], refs[h][2](v), refs[h][3])

def snapshots_summary(workbook, header_format, val_format):
    def transform(x):
        try:
            if x == "": return 0.0
            else: return float(x)
        except ValueError:
            return x
    with open(IN_SNAPSHOT_USAGE_LAST_MONTH) as f:
        reader = csv.DictReader(f)
        worksheet = workbook.add_worksheet("Snapshots last month")

        last_month = datetime.now() + dateutil.relativedelta.relativedelta(months=-1)
        worksheet.merge_range("A1:B1", "Snapshots for {}-{:02d}".format(last_month.year, last_month.month), header_format)

        cur_format = workbook.add_format()
        cur_format.set_align("center")
        cur_format.set_align("vcenter")
        cur_format.set_border()
        cur_format.set_num_format(NUMFORMAT_CURRENCY)

        worksheet.set_column(0, 0, 80)
        worksheet.set_column(1, 1, 25)

        refs = {
            "ResourceId": [0, "Resource Id", str, val_format],
            "Cost": [1, "Cost", transform, cur_format],
        }
        for v in refs.values():
            worksheet.write(1, v[0], v[1], header_format)
        for i, line in zip(itertools.count(2), reader):
            for h, v in line.items():
                worksheet.write(i, refs[h][0], refs[h][2](v), refs[h][3])

def gen_introduction(workbook, header_format, val_format):
    worksheet = workbook.add_worksheet("Introduction")

    worksheet.insert_image("A1", "src/ressources/introduction.png")


def main(name):
    workbook = xlsxwriter.Workbook('./out/{}.xlsx'.format(name))

    header_format = workbook.add_format()
    header_format.set_bold()
    header_format.set_align("center")
    header_format.set_align("vcenter")
    header_format.set_border()

    val_format = workbook.add_format()
    val_format.set_align("center")
    val_format.set_align("vcenter")
    val_format.set_border()

    gen_introduction(workbook, header_format, val_format)
    gen_weekly_variations(workbook, header_format, val_format)
    gen_weekly_variations_chart(workbook, header_format, val_format)
    gen_reserved_summary(workbook, header_format, val_format)
    gen_reservation_usage_summary(workbook, header_format, val_format)
    gen_instance_size_recommendations(workbook, header_format, val_format)
    gen_instance_count_history_chart(workbook, header_format, val_format)
    gen_instance_count_history(workbook, header_format, val_format)
    instance_summary(workbook, header_format, val_format)
    ebs_summary(workbook, header_format, val_format)
    snapshots_summary(workbook, header_format, val_format)

    workbook.close()


if __name__ == '__main__':
    print("Generating xlsx file.")
    name = sys.argv[1] if len(sys.argv) > 1 else "sheet"
    main(name)
    print("{}.xlsx generated!".format(name))

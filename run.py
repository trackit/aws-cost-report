#!/usr/bin/env python3

import boto3
import argparse
import sys
import os
import hashlib
import json
import threading
import zipfile
import gzip
import time
import shutil

class Parser(argparse.ArgumentParser):
    def print_help(self, file=sys.stdout):
        super(Parser, self).print_help(file)
        print(
            """
BILLING PREFIX:
  This tool uses AWS's new Cost And Usage Report format for billing data. The
  following structure is expected in S3:

    PREFIX
    `- arbitraryReportName
       |- 20171001-20171101
       |  |- arbitraryReportName-Manifest.json
       |  |- bbe82960-6a1a-47fd-ae59-1e666e2f674a
       |  |  |- arbitraryReportName-Manifest.json
       |  |  |- arbitraryReportName-1.csv.gz
       |  |  `- ...
       |  `- ...
       `- ...

  You can get more information about this at
  https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/billing-reports-costusage.html""",
            file=file,
        )

    def error(self, message):
        print(message)
        self.print_help()
        sys.exit(2)


def parse_args():
    parser = Parser()
    parser.add_argument(
        "--no-clear-before",
        help="Do not clear all data before doing anything. Useful when a previous invocation failed or when you add data incrementally before generating the sheet.",
        dest="clear_before",
        action="store_false",
        default=True,
    )
    parser.add_argument(
        "--no-generate-sheet",
        help="Do not generate a Google Sheet after all data was retrieved.",
        dest="generate_sheet",
        action="store_false",
        default=True,
    )
    parser.add_argument(
        "--billing",
        help="Get billing data from s3:/BUCKET/PREFIX using PROFILE.",
        action="append",
        nargs=3,
        metavar=("PROFILE", "BUCKET", "PREFIX"),
        default=[],
    )
    parser.add_argument(
        "--ec2",
        help="Get EC2 data for region REGION using PROFILE.",
        action="append",
        nargs=2,
        metavar=("PROFILE", "REGION"),
        default=[],
    )
    return parser.parse_args(), parser


def try_mkdir(path):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass


try_mkdir("in")
try_mkdir("in/usagecost")
try_mkdir("out")
try_mkdir("out/reservation-usage")
try_mkdir("out/instance-reservation-usage")
try_mkdir("out/instance-size-recommendation")

current_profile = "default"
current_region = "us-east-1"

def awsenv(profile, region):
    return "util/awsenv --profile {} --region {}".format(profile, region)


def build_billing_diff():
    os.system("src/get_bill_diff.py")


def build_instance_history():
    os.system("src/get_bill_diff.py")


def build_sheet():
    os.system("src/make_sheet.py")


def do_get_billing_data(profile, bucket, prefix):

    nonce = hashlib.sha1("{}{}".format(bucket, prefix).encode()).hexdigest()[:12]
    it = 1
    concurrent_available = 4
    concurrent_available_mutex = threading.Lock()
    thread = []

    def change_concurrent_available(value):
        nonlocal concurrent_available
        nonlocal concurrent_available_mutex

        concurrent_available_mutex.acquire()
        concurrent_available += value
        concurrent_available_mutex.release()

    def save_to_file(stream, file_name, report_key):
        try:
            with open(file_name, "wb+") as f:
                shutil.copyfileobj(stream, f)
        except Exception as e:
            print(e)
        finally:
            change_concurrent_available(1)

    def analyze_report(s3_client, bucket, report_keys):
        nonlocal it
        nonlocal thread
        nonlocal concurrent_available

        for report_key in report_keys:
            obj = s3_client.get_object(Bucket=bucket, Key=report_key)
            file_name = "in/usagecost/{}.{}.csv.{}".format(nonce, it, report_key.split(".")[-1])
            if concurrent_available <= 0:
                print("    Waiting to download {}...".format(report_key))
            while concurrent_available <= 0:
                time.sleep(0.1)
            t = threading.Thread(name=report_key, target=save_to_file, args=(obj["Body"], file_name, report_key))
            print("    Downloading {}...".format(report_key))
            t.start()
            change_concurrent_available(-1)
            thread.append(t)
            it += 1

    def analyze_obj(s3_client, objs):
        total = len(objs)
        current = 1
        for obj in objs:
            print("  Getting bill files from {} ({}/{})...".format(obj["Key"], current, total))
            content = s3_client.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read().decode("utf-8")
            content_json = json.loads(content)
            analyze_report(s3_client, content_json["bucket"], content_json["reportKeys"])
            current += 1
        for t in thread:
            t.join()

    def unzip_obj():
        for file_name in os.listdir("in/usagecost"):
            try:
                print("Extracting {}...".format(file_name))
                if file_name.startswith(nonce) and file_name.endswith(".zip"):
                    with zipfile.ZipFile(os.path.join("in/usagecost", file_name), "r") as z:
                        z.extractall("in/usagecost")
                elif file_name.startswith(nonce) and file_name.endswith(".gz"):
                    with gzip.GzipFile(os.path.join("in/usagecost", file_name), "r") as z:
                        with open(os.path.join("in/usagecost", file_name[:-3]), "wb+") as f:
                            shutil.copyfileobj(z, f)
            except Exception as e:
                print("Failed to extract {}: {}".format(file_name, e))

    try:
        session = boto3.Session(profile_name=profile)
        s3_client = session.client("s3")
        objs = s3_client.list_objects(Bucket=bucket)["Contents"]
        objs = [obj for obj in objs if obj["Key"].endswith(".json") and obj["Key"].startswith(prefix+"/")]
    except Exception as e:
        exit(e)
    analyze_obj(s3_client, objs)
    unzip_obj()
    pass


def do_get_instance_data(profile, region):
    os.system("{} src/get_ec2_data.py".format(awsenv(profile, region)))
    os.system("{} src/get_ec2_recommendations.py".format(awsenv(profile, region)))


def recursivly_remove_file(path):
    if os.path.isdir(path):
        for f in os.listdir(path):
            recursivly_remove_file(os.path.join(path, f))
    else:
        os.remove(path)


def clear_data():
    for f in os.listdir("out"):
        recursivly_remove_file(os.path.join("out", f))
    for f in os.listdir("in"):
        f = os.path.join("in", f)
        if not os.path.isdir(f) or (os.path.isdir(f) and f != "in/persistent"):
            recursivly_remove_file(f)


def main():
    global current_profile
    global current_region

    args, parser = parse_args()
    if len(args.billing) == 0 and len(args.ec2) == 0:
        return parser.print_help()
    if args.clear_before:
        clear_data()
    if not os.path.isfile("in/ondemandcosts.json"):
        os.system("src/get_ec2_costs.sh")
    for bill in args.billing:
        print("Download billings for {}...".format(bill[0]))
        current_profile = bill[0]
        do_get_billing_data(*bill)
    for ec in args.ec2:
        current_profile = ec[0]
        current_region = ec[1]
        do_get_instance_data(*ec)
    if args.generate_sheet:
        build_billing_diff()
        build_instance_history()
        build_sheet()


if __name__ == "__main__":
    main()

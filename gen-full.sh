#!/bin/bash

set -xe

bill_bucket="$1"
bill_prefix="$2"

bill_tmp=$(mktemp -d)

aws s3 sync --exclude '*' --include '*.json' "s3://$bill_bucket/$bill_prefix" "$bill_tmp/"

rm usagecost/*
mkdir -p usagecost

jq -r '.reportKeys | .[]' "$bill_tmp"/*/*/*.json | parallel -j 4 \
	aws s3 cp "s3://$bill_bucket/{}" "usagecost/{#}.csv.gz"

pushd usagecost/
for gzipped in *.gz
do
	gzip -d "$gzipped"
done
for zipped in *.zip
do
	unzip "$zipped"
done
popd

./usagecostdiff.py
./autoreport.py
./gen-sheet.py

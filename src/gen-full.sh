#!/bin/bash

DIR_BILLS=out/usagecost
DIR_INSTANCE_RESERVATION_USAGE=out/instance-reservation-usage
DIR_RESERVATION_USAGE=out/reservation-usage

set -xe

bill_bucket="$1"
bill_prefix="$2"

bill_tmp=$(mktemp -d)

aws s3 sync --exclude '*' --include '*.json' "s3://$bill_bucket/$bill_prefix" "$bill_tmp/"

rm {$DIR_BILLS,$DIR_INSTANCE_RESERVATION_USAGE,$DIR_RESERVATION_USAGE}/*
mkdir -p $DIR_BILLS $DIR_INSTANCE_RESERVATION_USAGE $DIR_RESERVATION_USAGE

jq -r '.reportKeys | .[]' "$bill_tmp"/*/*/*.json | \
	sed -r 's/csv\.(gz|zip)$/\0\x00\0/' | \
	parallel \
		--jobs 4 \
		--colsep '\0' \
		aws s3 cp "s3://$bill_bucket/{1}" "$DIR_BILLS/{#}.{2}"

rm -r "$bill_tmp"

pushd $DIR_BILLS/
for gzipped in *.gz
do
	[[ "$gzipped" == '*.gz' ]] || gzip -d "$gzipped"
done
for zipped in *.zip
do
	[[ "$zipped" == '*.zip' ]] || unzip "$zipped"
done
popd

./usagecostdiff.py
./autoreport.py
./gen-sheet.py

#!/bin/bash

set -e

DEFAULT_EDITOR=nano
PROFILE_ENV=env # AWS profile which uses environment variables instead of credentials file.
MAX_RETRY=5

DIR_BILLS='in/usagecost'

for pgm in shasum sha1sum md5sum md5
do
	pgm_path=$(which $pgm) 2>/dev/null
	if [[ -x "$pgm_path" ]]
	then
		HASH_INSECURE="$pgm_path"
		break
	fi
done
if [[ -z "$HASH_INSECURE" ]]
then
	echo "Could not find hash function." 1>&2
	exit 1
fi

current_profile=default
current_region=us-east-1

mkdir -p in/{usagecost}
mkdir -p out/{instance-,}reservation-usage
mkdir -p out/instance-size-recommendation

function clear_data() {
	find in -type f ! -path 'in/persistent/*' -delete
	find out -type f -delete
}

function prepare_env_file() {
	echo '# This file will be sourced by bash.'
	echo '# Set your environment variables.'
	for env_var in AWS_{ACCESS_KEY_ID,SECRET_ACCESS_KEY,SESSION_TOKEN}
	do
		if [[ -z "${!env_var}" ]]
		then
			echo "# export ${env_var}="
		else
			echo "export ${env_var}=${!env_var}"
		fi
	done
}

function set_profile() {
	read -p "AWS profile (or '${PROFILE_ENV}'): " current_profile
	if [[ "$current_profile" == "$PROFILE_ENV" ]]
	then
		tmp_env="$(mktemp)"
		prepare_env_file > "$tmp_env"
		${EDITOR:-${DEFAULT_EDITOR}} "$tmp_env"
		source "$tmp_env"
		rm "$tmp_env"
	else
		unset AWS_{ACCESS_KEY_ID,SECRET_ACCESS_KEY,SESSION_TOKEN}
	fi
	util/awsdumpenv
}

function set_region() {
	read -p "AWS region: " current_region
}

function get_billing_data() {
	local bill_bucket
	local bill_prefix
	read -p "Bucket name: " bill_bucket
	read -p "Key prefix:  " bill_prefix
	do_get_billing_data "$bill_bucket" "$bill_prefix"
}

function do_get_billing_data() {
	local bill_bucket="$1"
	local bill_prefix="$2"
	local bill_tmp=$(mktemp -d)
	local nonce=$($HASH_INSECURE <<<"$bill_bucket$bill_prefix" | head -c 12)
	aws_cli s3 sync --exclude '*' --include '*.json' "s3://$bill_bucket/$bill_prefix" "$bill_tmp/"
	jq -r '.reportKeys | .[]' "$bill_tmp"/*/*/*.json | \
		perl -pe 's/(csv\.(?:gz|zip))$/\1\x00\1/' | \
		parallel \
			--jobs 4 \
			--colsep '\0' \
			aws "${aws_cli_args[@]}" s3 cp "s3://$bill_bucket/{1}" "$DIR_BILLS/$nonce.{#}.{2}"
	pushd "$DIR_BILLS"
	for z in *.gz
	do
		[[ "$z" == '*.gz' ]] || gzip -d "$z"
	done
	for z in *.zip
	do
		[[ "$z" == '*.zip' ]] || unzip -d "$z"
	done
	popd
}

function get_cost_data() {
	retry src/get_ec2_costs.sh
}

function get_instance_data() {
	retry aws_env src/get_ec2_data.py
	retry aws_env src/get_ec2_recommendations.py
}

function retry() {
	local retry=$MAX_RETRY
	while ! "$@" && [[ $retry > 1 ]]
	do
		retry=$((retry - 1))
	done
	if [[ $retry = 1 ]]
	then
		return 1
	else
		return 0
	fi
}

function build_billing_diff() {
	src/get_bill_diff.py
}

function build_instance_history() {
	src/get_ec2_instance_history.py
}

function build_sheet() {
	retry src/make_sheet.py
}

function before_action_choice() {
	echo "Current profile: ${current_profile}"
	echo "Current region:  ${current_region}"
	echo
	echo "Select next action."
}

function aws_cli() {
	if [[ "${current_profile}" != "${PROFILE_ENV}" ]]
	then
		aws_cli_args=(--region "${current_region}" --profile "${current_profile}")
	else
		aws_cli_args=()
	fi
	aws "${aws_cli_args[@]}" "$@"
}

function aws_env() {
	if [[ "${current_profile}" != "${PROFILE_ENV}" ]]
	then
		util/awsenv --profile "${current_profile}" --region "${current_region}" "$@"
	else
		"$@"
	fi
}

function auto_report() {
	clear_data
	set_profile
	set_region
	get_billing_data
	get_cost_data
	get_instance_data
	build_billing_diff
	build_instance_history
	build_sheet
}

function wizard() {
	before_action_choice
	select action in \
		auto_report \
		clear_data \
		set_profile \
		set_region \
		get_cost_data \
		get_billing_data \
		get_instance_data \
		build_billing_diff \
		build_instance_history \
		build_sheet
	do
		if [[ -z "$action" ]]
		then
			exit
		fi
		"$action"
		before_action_choice
	done
}

# non-interactive actions
nint_bill_profile=()
nint_bill_bucket=()
nint_bill_prefix=()
nint_ec2_profile=()
nint_ec2_region=()
nint_clear_before=yes
function parse_options() {
	while [[ "${#@}" -gt 0 ]]
	do
		case "$1" in
		--billing)
			parse_options_billing "$@" && shift 4 || return 1
			;;
		--ec2)
			parse_options_ec2 "$@"     && shift 3 || return 1
			;;
		--no-clear-before)
			nint_clear_before=no
			shift 1
			;;
		--no-generate-sheet)
			nint_generate_sheet=no
			shift 1
			;;
		--help)
			print_usage
			exit 0
			;;
		*)
			1>&2 echo "unknown parameter $0"
			return 1
			;;
		esac
	done
	return 0
}

function parse_options_ec2() {
	if [[ "${#@}" -ge 3 ]]
	then
		nint_ec2_profile=("${nint_ec2_profile[@]}" "$2")
		nint_ec2_region=("${nint_ec2_region[@]}" "$3")
		return 0
	else
		return 1
	fi
}

function parse_options_billing() {
	if [[ "${#@}" -ge 4 ]]
	then
		nint_bill_profile=("${nint_bill_profile[@]}" "$2")
		nint_bill_bucket=("${nint_bill_bucket[@]}" "$3")
		nint_bill_prefix=("${nint_bill_prefix[@]}" "$4")
		return 0
	else
		return 1
	fi
}

function run_non_interactive() {
	if [[ "$nint_clear_before" == "yes" ]]
	then
		clear_data
	fi
	if [[ ! -r "in/ondemandcosts.json" ]]
	then
		get_cost_data
	fi
	for i in $(seq 0 $((${#nint_bill_profile[@]} - 1)))
	do
		local bill_prefix="${nint_bill_prefix[i]}"
		local bill_bucket="${nint_bill_bucket[i]}"
		local bill_profile="${nint_bill_profile[i]}"
		current_profile="$bill_profile"
		do_get_billing_data "$bill_bucket" "$bill_prefix"
	done
	for i in $(seq 0 $((${#nint_ec2_profile[@]} - 1)))
	do
		local ec2_profile="${nint_ec2_profile[i]}"
		local ec2_region="${nint_ec2_region[i]}"
		current_profile="$ec2_profile"
		current_region="$ec2_region"
		get_instance_data
	done
	if [[ "$nint_generate_sheet" == "yes" ]]
	then
		build_billing_diff
		build_instance_history
		build_sheet
	fi
}

function print_usage() {
	cat 1>&2 <<EOF
USAGE:
wizard:  ${0} [--wizard]
command: ${0} [--no-clear-before] [--no-generate-sheet] [--billing PROFILE
              BUCKET PREFIX]... [-ec2 PROFILE REGION]...

  --wizard           Run interactively

  --no-clear-before    Do not clear all data before doing anything. Useful when
                       a previous invocation failed or when you add data
                       incrementally before generating the sheet.
  --no-generate-sheet  Do not generate a Google Sheet after all data was
                       retrieved.
  --billing            Get billing data from s3:/BUCKET/PREFIX using PROFILE.
  --ec2                Get EC2 data for region REGION using PROFILE.

BILLING PREFIX:
  This tool uses AWS's new Cost And Usage Report format for billing data. The
  following structure is expected in S3:

    PREFIX
    \`- arbitraryReportName
       |- 20171001-20171101
       |  |- arbitraryReportName-Manifest.json
       |  |- bbe82960-6a1a-47fd-ae59-1e666e2f674a
       |  |  |- arbitraryReportName-Manifest.json
       |  |  |- arbitraryReportName-1.csv.gz
       |  |  \`- ...
       |  \`- ...
       \`- ...
  
  You can get more information about this at 
  https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/billing-reports-costusage.html
EOF
}

function main() {
	if [[ "${#@}" == 0 || "$1" == "--wizard" ]]
	then
		wizard
	else
		parse_options "$@" || ( print_usage; exit 1 )
		run_non_interactive
	fi
}

main "$@"

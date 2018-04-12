![](https://s3-us-west-2.amazonaws.com/trackit-public-artifacts/aws-cost-report/introduction.png)
# Cost report generator

## Requirements

- Install [jq](https://stedolan.github.io/jq/download/)
- Install the python3 dependencies: `sudo pip3 install -r requirements.txt`

## Google Sheets API access

Follow the instructions at
https://developers.google.com/sheets/api/quickstart/python to setup credentials
and API access.

## How to run the tool on your machine

```
# Print help and usage informations
$> ./run.py --help

# Run with one billing bucket and one EC2 profile
$> ./run.py --billing profile_name billing-bucket-name prefix --ec2 profile_name --xlsx-name filename

# Run with multiple billing buckets and EC2 profiles
$> ./run.py --billing profile_name billing-bucket-name prefix --billing profile_name2 billing-bucket-name2 prefix2 --ec2 profile_name --ec2 profile_name2 --xlsx-name filename
```

The tool is built to use AWS credentials stored in `~/.aws/credentials`.
If you set the profile to `env`, the tool will use environment variables you must supply instead.

## How to run the tool with docker

The docker container do not export any data to google sheets.
However it generates CSVs in the `out` directory, and a local spreadsheet generation will be added soon.

### Use our prebuilt image

```
# Pull the msolution/aws-cost-report image
$> docker pull msolution/aws-cost-report
```

### Build your own image

```
# Build your own msolution/aws-cost-report image
$> docker build -t msolution/aws-cost-report .
```

### Use the docker container

```
# Run with one billing bucket and one EC2 profile, using env credentials
$> docker run -v /local/path/out:/root/aws-cost-report/out -e AWS_ACCESS_KEY_ID=accesskeyid -e AWS_SECRET_ACCESS_KEY=secretaccesskey -e AWS_DEFAULT_REGION=default-region -e AWS_SESSION_TOKEN=sessiontoken(optional) msolution/aws-cost-report --no-generate-sheet --billing env billing-bucket-name prefix --ec2 env --xlsx-name filename

# Run with multiple billing buckets and EC2 profiles, using your local aws credentials
$> docker run -v /path/to/credentials:/root/.aws:ro -v /local/path/out:/root/aws-cost-report/out msolution/aws-cost-report --no-generate-sheet --billing profile_name billing-bucket-name prefix --billing profile_name2 billing-bucket-name2 prefix2 --ec2 profile_name --ec2 profile_name2 --xlsx-name filename
```

## Screenshots

Download the report example [here](https://s3-us-west-2.amazonaws.com/trackit-public-artifacts/aws-cost-report/report-example.xlsx).

### Cost and variations tab

![](https://s3-us-west-2.amazonaws.com/trackit-public-artifacts/aws-cost-report/cost-variations.png)


### Reserved instance summary

![](https://s3-us-west-2.amazonaws.com/trackit-public-artifacts/aws-cost-report/reserved-instance-summary.png)


### Instance size recommendations

![](https://s3-us-west-2.amazonaws.com/trackit-public-artifacts/aws-cost-report/instance-size-recommendations.png)


### EC2 instances last month

![](https://s3-us-west-2.amazonaws.com/trackit-public-artifacts/aws-cost-report/ec2-instances-last-month.png)

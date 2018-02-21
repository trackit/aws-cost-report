# Cost report generator

## Requirements

- Install [jq](https://stedolan.github.io/jq/download/)
- Install [parallel](https://github.com/flesler/parallel)
- Install the python3 dependencies: `sudo pip3 install -r requirements.txt`

## Google Sheets API access

Follow the instructions at
https://developers.google.com/sheets/api/quickstart/python to setup credentials
and API access.

## How to use the wizard

In order to support getting data from multiple sources (accounts or regions),
this tool provides a rudimentary interactive wizard : `run.sh`. When you run
it, you should see the following:

```
Current profile: default
Current region:  us-east-1

Select next action.
1) auto_report         4) set_region          7) get_instance_data
2) clear_data          5) get_cost_data       8) build_billing_diff
3) set_profile         6) get_billing_data    9) build_sheet
>
```

In order to run a command, type in its number and press _Return_. For the
simplest case where you want to generate a report for a single region in a
single account, you can use `auto_report` which will run all the necessary
actions and prompt you for information.

The tool is built to use AWS credentials stored in `~/.aws/credentials`. To
choose the profile the tool should use, select `set_profile`. If you set the
profile to `env`, the tool will use environment variables you must supply
instead.

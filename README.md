# Cost report generator

## How to use

`autoreport.py` takes no arguments and generates CSV files later used for
Google Sheets generation. This command can take several minutes to run. It is
easiest to run it using `awsenv`, as follows:

```
$ AWS_DEFAULT_REGION=<region> awsenv --profile <profile name> autoreport.py
```

`gen-sheet.py` reads the CSV files and builds a Google Sheets spreadsheet.
Follow the instructions at
https://developers.google.com/sheets/api/quickstart/python to setup credentials
and API access.

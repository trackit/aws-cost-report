#!/usr/bin/env python3

import collections
import csv
import itertools
import json
import os
import pprint

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import httplib2

from sheets import *
import utils

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = ' '.join([
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
])
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart'

SHEET_RESERVATIONS_SUMMARY = 1

PRETTY_FIELD_NAMES = {
    'instance_type'       : 'Instance type',
    'availability_zone'   : 'Availability zone',
    'tenancy'             : 'Tenancy',
    'product'             : 'Product',
    'count'               : 'Count',
    'count_reserved'      : 'Count (reserved)',
    'cost_ondemand'       : 'Cost (on demand)',
    'cost_reserved_worst' : 'Cost (worst reserved)',
    'cost_reserved_best'  : 'Cost (best reserved)',
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

COLOR_RED_BG   = { 'red': 0xFF/float(0xFF), 'green': 0xCC/float(0xFF), 'blue': 0xCC/float(0xFF) }
COLOR_RED_FG   = { 'red': 0xCC/float(0xFF), 'green': 0x00/float(0xFF), 'blue': 0x00/float(0xFF) }
COLOR_GREEN_BG = { 'red': 0xCC/float(0xFF), 'green': 0xFF/float(0xFF), 'blue': 0xCC/float(0xFF) }
COLOR_GREEN_FG = { 'red': 0x00/float(0xFF), 'green': 0x66/float(0xFF), 'blue': 0x00/float(0xFF) }

def _with_trailing(it, trail):
    return itertools.chain(it, itertools.repeat(trail))

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def reserved_summary():
    def cost_monthly(sheet, row, column, field):
        base_hourly = sheet.field_index('cost_ondemand')
        base_monthly = sheet.field_index('cost_monthly_ondemand')
        return Formula('={}*{}*720'.format(
            sheet.field_address('count', row, 2),
            sheet.address(base_hourly + (column - base_monthly), row),
        ))
    def savings_monthly(sheet, row, column, field):
        base_ondemand = sheet.field_index('cost_ondemand')
        base_reserved = sheet.field_index('cost_reserved_worst')
        base_savings = sheet.field_index('savings_reserved_worst')
        return Formula('=1-{}/{}'.format(
            sheet.address(base_reserved + (column - base_savings), row),
            sheet.field_address('cost_ondemand', row, 2),
        ))
    fields = (
        FieldGroup('Reservation', (
            Field('instance_type'               , 'instance_type'               , str             , 'Instance type'     , None)               ,
            Field('availability_zone'           , 'availability_zone'           , str             , 'Availability zone' , None)               ,
            Field('tenancy'                     , 'tenancy'                     , str             , 'Tenancy'           , None)               ,
            Field('product'                     , 'product'                     , str             , 'Product'           , None)               ,
        )),
        Field(    'count'                       , 'count'                       , int             , 'Count'             , '0')                ,
        Field(    'count_reserved'              , 'count_reserved'              , int             , 'Count (reserved)'  , '0')                ,
        FieldGroup('Hourly cost per instance', (
            Field('cost_ondemand'               , 'cost_ondemand'               , float           , 'On demand'         , NUMFORMAT_CURRENCY) ,
            Field('cost_reserved_worst'         , 'cost_reserved_worst'         , float           , 'Worst reserved'    , NUMFORMAT_CURRENCY) ,
            Field('cost_reserved_best'          , 'cost_reserved_best'          , float           , 'Best reserved'     , NUMFORMAT_CURRENCY) ,
        )),
        FieldGroup('Monthly cost total', (
            Field('cost_monthly_ondemand'       , 'cost_monthly_ondemand'       , cost_monthly    , 'On demand'         , NUMFORMAT_CURRENCY) ,
            Field('cost_monthly_reserved_worst' , 'cost_monthly_reserved_worst' , cost_monthly    , 'Worst reserved'    , NUMFORMAT_CURRENCY) ,
            Field('cost_monthly_reserved_best'  , 'cost_monthly_reserved_best'  , cost_monthly    , 'Best reserved'     , NUMFORMAT_CURRENCY) ,
        )),
        FieldGroup('Savings over on demand', (
            Field('savings_reserved_worst'      , 'savings_reserved_worst'      , savings_monthly , 'Worst reserved'    , NUMFORMAT_PERCENT)  ,
            Field('savings_reserved_best'       , 'savings_reserved_best'       , savings_monthly , 'Best reserved'     , NUMFORMAT_PERCENT)  ,
        ))
    )
    conditional_format = (
        ConditionalFormat('CUSTOM_FORMULA', '=(INDIRECT(ADDRESS(ROW(), COLUMN() - 1)) = INDIRECT(ADDRESS(ROW(), COLUMN())))', {
            'backgroundColor': COLOR_GREEN_BG,
            'textFormat': {
                'foregroundColor': COLOR_GREEN_FG,
            },
        }),
    )
    with utils.csv_folder(IN_INSTANCE_RESERVATION_USAGE_DIR) as records:
        sheet = Sheet(
            source=records,
            fields=fields,
            sheet_id=1,
            fields_conditional_formats=tuple(
                ColumnConditionalFormat(column, conditional_format)
                for column in field_flatten(FieldRoot(fields)) if column.name == 'count_reserved'
            )
        )
        sheet.properties['title'] = 'Reserved instance summary'
        return sheet.to_dict()

def _returns(value):
    def f(*args, **kwargs):
        return value
    return f

def reservation_usage_summary():
    def effective_cost(sheet, row, column, field):
        return Formula('={}/720+{}'.format(
            sheet.field_address('cost_upfront', row, 2),
            sheet.field_address('cost_hourly', row, 2),
        ))
    def monthly_losses(sheet, row, column, field):
        return Formula('({reserved}-{used})*{effective}*720'.format(
            reserved =sheet.field_address('count_reserved', row, 2),
            used     =sheet.field_address('count_used', row, 2),
            effective=sheet.field_address('effective_cost', row, 2),
        ))
    fields = (
        FieldGroup('Reservation', (
            Field('instance_type'               , 'instance_type'               , str             , 'Instance type'     , None)               ,
            Field('availability_zone'           , 'availability_zone'           , str             , 'Availability zone' , None)               ,
            Field('tenancy'                     , 'tenancy'                     , str             , 'Tenancy'           , None)               ,
            Field('product'                     , 'product'                     , str             , 'Product'           , None)               ,
        )),
        FieldGroup('Count', (
            Field('count_reserved'              , 'count'                       , int             , 'Reserved'          , None)               ,
            Field('count_used'                  , 'count_used'                  , int             , 'Used'              , None)               ,
        )),
        FieldGroup('Cost per instance', (
            Field('cost_upfront'                , 'cost_upfront'                , float           , 'Upfront'           , NUMFORMAT_CURRENCY) ,
            Field('cost_hourly'                 , 'cost_hourly'                 , float           , 'Hourly'            , NUMFORMAT_CURRENCY) ,
            Field('effective_cost'              , 'effective_cost'              , effective_cost  , 'Effective', NUMFORMAT_CURRENCY),
        )),
        Field(    'monthly_losses'              , 'monthly_losses'              , monthly_losses  , 'Monthly losses', NUMFORMAT_CURRENCY),
    )
    with utils.csv_folder(IN_RESERVATION_USAGE_DIR) as records:
        sheet = Sheet(
            source=records,
            fields=fields,
            sheet_id=3,
        )
        sheet.properties['title'] = 'Reservation usage summary'
        return sheet.to_dict()

def weekly_variations():
    def variation(sheet, row, column, field):
        prev_address = sheet.address(column - 1, row)
        next_address = sheet.address(column + 1, row)
        return Formula('=IF({0}=0,"",{1}/{0}-1)'.format(
            prev_address,
            next_address,
        ))
    def total(sheet, row, column, field):
        cost_fields = [
            f
            for f in sheet.fields_flat() if '_cost' in f.name
        ]
        return Formula('=SUM({})'.format(
            ','.join(
                sheet.field_address(f, row)
                for f in cost_fields
            )
        ))
    with open(IN_ABSOLUTE_COST_PER_MONTH) as f:
        reader = csv.DictReader(f)
        fields = (
            Field(    'usage' , 'usage' , str   , 'Usage type' , None),
            FieldGroup('Monthly cost', tuple(
                FieldGroup(isoweek,
                    (
                        (
                            Field(isoweek+'_var',  isoweek, variation, 'Variation', NUMFORMAT_PERCENT_VAR),
                        ) if not is_first_week else ()
                    ) + (
                        Field(isoweek+'_cost', isoweek, float  , 'Cost'      , NUMFORMAT_CURRENCY),
                    )
                )
                for isoweek, is_first_week in zip(reader.fieldnames[1:], _with_trailing((True,), False))
            )),
            Field('total', 'total', total, 'Total', NUMFORMAT_CURRENCY),
        )
        variation_conditional_format = (
            ConditionalFormat('NUMBER_GREATER', '0', {
                'backgroundColor': COLOR_RED_BG,
                'textFormat': {
                    'foregroundColor': COLOR_RED_FG,
                },
            }),
            ConditionalFormat('NUMBER_LESS_THAN_EQ', '0', {
                'backgroundColor': COLOR_GREEN_BG,
                'textFormat': {
                    'foregroundColor': COLOR_GREEN_FG,
                },
            })
        )
        variation_columns = (
            f
            for f in field_flatten(FieldRoot(fields)) if '_var' in f.name
        )
        source = sorted(
            reader,
            key=(lambda row: sum(float(v) for k, v in row.items() if k != 'usage')),
            reverse=True,
        )
        sheet = Sheet(
            source=source,
            fields=fields,
            fields_conditional_formats=tuple(
                ColumnConditionalFormat(column, variation_conditional_format)
                for column in variation_columns
            ),
            sheet_id=2,
        )
        sheet.properties['title'] = 'Cost variations'
        sheet_data = sheet.to_dict()
    return sheet_data

INSTANCE_SIZES = [
    'nano',
    'micro',
    'small',
    'medium',
    'large',
    'xlarge',
    '2xlarge',
    '4xlarge',
    '8xlarge',
    '9xlarge',
    '10xlarge',
    '12xlarge',
    '16xlarge',
    '18xlarge',
    '24xlarge',
    '32xlarge',
]

def instance_history():
    with open(IN_INSTANCE_HISTORY) as f:
        reader = csv.DictReader(f)
        fields = (
            Field('date', 'date', str, 'Date', None),
            FieldGroup('Instance count', tuple(
                Field(instance_type, instance_type, int, instance_type, None)
                for instance_type in reader.fieldnames[1:]
            )),
        )
        sheet = Sheet(
            source=reader,
            fields=fields,
            sheet_id=5
        )
        sheet.properties['title'] = 'Instance count history'
        return sheet.to_dict()

def instance_size_recommendations():
    fields = (
        FieldGroup('Instance', (
            Field('account', 'account', str, 'Account', None),
            Field('id', 'id', str, 'ID', None),
            Field('name', 'name', str, 'Name', None),
            Field('size', 'size', str, 'Type', None),
            Field('lifecycle', 'lifecycle', str, 'Lifecycle', None),
        )),
        Field('recommendation', 'recommendation', str, 'Recommended', None),
    )
    with utils.csv_folder(IN_INSTANCE_SIZE_RECOMMENDATIONS_DIR) as source:
        sheet = Sheet(
            source=source,
            fields=fields,
            sheet_id=4,
        )
        sheet.properties['title'] = 'Instance size recommendations'
        return sheet.to_dict()

def main():
    """Shows basic usage of the Sheets API.

    Creates a Sheets API service object and prints the names and majors of
    students in a sample spreadsheet:
    https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    reserved_summary_data = reserved_summary()
    weekly_variations_data = weekly_variations()
    reservation_usage_summary_data = reservation_usage_summary()
    instance_size_recommendations_data = instance_size_recommendations()
    instance_history_data = instance_history()

    body = {
        'properties': {
            'title': 'my generated spreadsheet',
        },
        'sheets': [
            weekly_variations_data,
            reserved_summary_data,
            reservation_usage_summary_data,
            instance_size_recommendations_data,
            instance_history_data,
        ],
    }

    #print(json.dumps(body, indent=4))

    spreadsheet = service.spreadsheets().create(body=body)

    print(spreadsheet)
    print(dir(spreadsheet))
    print(spreadsheet.execute())

if __name__ == '__main__':
    main()

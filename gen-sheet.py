#!/usr/bin/env python2.7

from __future__ import print_function
import httplib2
import os
import csv
import itertools
import pprint

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import collections
import json

from sheets import *

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
    with open('instances-reservation-usage.us-east-1.csv') as f:
        reader = csv.DictReader(f)
        sheet = Sheet(
            source=reader,
            fields=fields,
            sheet_id=1,
        )
        sheet.properties['title'] = 'Reserved instance summary'
        sheet_data = sheet.to_dict()
    return sheet_data

def reservation_usage_summary():
    fields = (
        FieldGroup('Reservation', (
            Field('instance_type'               , 'instance_type'               , str             , 'Instance type'     , None)               ,
            Field('availability_zone'           , 'availability_zone'           , str             , 'Availability zone' , None)               ,
            Field('tenancy'                     , 'tenancy'                     , str             , 'Tenancy'           , None)               ,
            Field('product'                     , 'product'                     , str             , 'Product'           , None)               ,
        )),
        Field(    'count_reserved'              , 'count'                       , int             , 'Count (reserved)'  , None)               ,
        Field(    'count_used'                  , 'count_used'                  , int             , 'Count (used)'      , None)               ,
    )
    with open('reservation-usage.us-west-2.csv') as f:
        reader = csv.DictReader(f)
        sheet = Sheet(
            source=reader,
            fields=fields,
            sheet_id=3,
        )
        sheet.properties['title'] = 'Reservation usage summary'
        sheet_data = sheet.to_dict()
    return sheet_data

def weekly_variations():
    def variation(sheet, row, column, field):
        prev_address = sheet.address(column - 1, row)
        next_address = sheet.address(column + 1, row)
        return Formula('=IF({0}=0,"",{1}/{0}-1)'.format(
            prev_address,
            next_address,
        ))
    with open('absolute.csv') as f:
        reader = csv.DictReader(f)
        fields = (
            Field(    'usage' , 'usage' , str   , 'Usage type' , None),
            FieldGroup('Monthly cost', tuple(
                FieldGroup(isoweek,
                    (
                        (
                            Field(isoweek+'_var',  isoweek, variation, 'Variation', NUMFORMAT_PERCENT),
                        ) if not is_first_week else ()
                    ) + (
                        Field(isoweek+'_cost', isoweek, float  , 'Cost'      , NUMFORMAT_CURRENCY),
                    )
                )
                for isoweek, is_first_week in zip(reader.fieldnames[1:], _with_trailing((True,), False))
            ))
        )
        sheet = Sheet(
            source=reader,
            fields=fields,
            sheet_id=2,
        )
        sheet.properties['title'] = 'Cost variations'
        sheet_data = sheet.to_dict()
    return sheet_data

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

    body = {
        'properties': {
            'title': 'my generated spreadsheet',
        },
        'sheets': [
            weekly_variations_data,
            reserved_summary_data,
            reservation_usage_summary_data,
        ],
    }

    #print(json.dumps(body, indent=4))

    spreadsheet = service.spreadsheets().create(body=body)

    print(spreadsheet)
    print(dir(spreadsheet))
    print(spreadsheet.execute())

if __name__ == '__main__':
    main()

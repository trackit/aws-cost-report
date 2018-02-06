#!/usr/bin/env python2.7

from __future__ import print_function
import httplib2
import os
import csv
import itertools

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
        base_hourly = sheet.field_index('cost_ondemand', 0)[0]
        base_monthly = sheet.field_index('cost_monthly_ondemand', 0)[0]
        return Formula('={}*{}*720'.format(
            sheet.field_address('count', row, 2),
            sheet.address(base_hourly + (column - base_monthly), row),
        ))
    def savings_monthly(sheet, row, column, field):
        base_ondemand = sheet.field_index('cost_ondemand', 0)[0]
        base_reserved = sheet.field_index('cost_reserved_worst', 0)[0]
        base_savings = sheet.field_index('savings_reserved_worst', 0)[0]
        return Formula('=1-{}/{}'.format(
            sheet.address(base_reserved + (column - base_savings), row),
            sheet.field_address('cost_ondemand', row, 2),
        ))
    fields = map(Field._make, [
        ('instance_type'               , 'instance_type'               , str             , 'reservation'              , 'Instance type')     ,
        ('availability_zone'           , 'availability_zone'           , str             , 'reservation'              , 'Availability zone') ,
        ('tenancy'                     , 'tenancy'                     , str             , 'reservation'              , 'Tenancy')           ,
        ('product'                     , 'product'                     , str             , 'reservation'              , 'Product')           ,
        ('count'                       , 'count'                       , int             , None                       , 'Count')             ,
        ('count_reserved'              , 'count_reserved'              , int             , None                       , 'Count (reserved)')  ,
        ('cost_ondemand'               , 'cost_ondemand'               , float           , 'hourly_cost_per_instance' , 'On demand')         ,
        ('cost_reserved_worst'         , 'cost_reserved_worst'         , float           , 'hourly_cost_per_instance' , 'Worst reserved')    ,
        ('cost_reserved_best'          , 'cost_reserved_best'          , float           , 'hourly_cost_per_instance' , 'Best reserved')     ,
        ('cost_monthly_ondemand'       , 'cost_monthly_ondemand'       , cost_monthly    , 'monthly_cost_total'       , 'On demand')         ,
        ('cost_monthly_reserved_worst' , 'cost_monthly_reserved_worst' , cost_monthly    , 'monthly_cost_total'       , 'Worst reserved')    ,
        ('cost_monthly_reserved_best'  , 'cost_monthly_reserved_best'  , cost_monthly    , 'monthly_cost_total'       , 'Best reserved')     ,
        ('savings_reserved_worst'      , 'savings_reserved_worst'      , savings_monthly , 'savings'                  , 'Worst reserved')    ,
        ('savings_reserved_best'       , 'savings_reserved_best'       , savings_monthly , 'savings'                  , 'Best reserved')     ,
    ])
    field_groups = map(FieldGroup._make, [
        ('reservation', 'Reservation'),
        ('hourly_cost_per_instance', 'Hourly cost per instance'),
        ('monthly_cost_total', 'Monthly cost total'),
        ('savings', 'Savings over on demand'),
    ])
    with open('instances-reservation-usage.us-east-1.csv') as f:
        reader = csv.DictReader(f)
        sheet = Sheet(
            source=reader,
            fields=fields,
            field_groups=field_groups,
            sheet_id=1,
        )
        sheet.properties['title'] = 'Reserved instance summary'
        sheet_data = sheet.to_dict()
    return sheet_data

def weekly_variations():
    with open('absolute.csv') as f:
        reader = csv.DictReader(f)
        fields = map(Field._make, [
            ('usage' , 'usage' , str   , None    , 'Usage type'),
        ] + [
            (isoweek , isoweek , float , 'weeks' , isoweek)
            for isoweek in reader.fieldnames[1:]
        ])
        field_groups = [
            FieldGroup('weeks', 'Weeks'),
        ]
        sheet = Sheet(
            source=reader,
            fields=fields,
            field_groups=field_groups,
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

    body = {
        'properties': {
            'title': 'my generated spreadsheet',
        },
        'sheets': [
            reserved_summary_data,
            weekly_variations_data,
        ],
    }

    print(json.dumps(body, indent=4))

    spreadsheet = service.spreadsheets().create(body=body)

    print(spreadsheet)
    print(dir(spreadsheet))
    print(spreadsheet.execute())

if __name__ == '__main__':
    main()

#!/usr/bin/env python2.7

from __future__ import print_function
import httplib2
import os
import csv

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

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

    
    fields = ['instance_type', 'availability_zone', 'tenancy', 'product', 'count', 'count_reserved', 'cost_ondemand', 'cost_reserved_worst', 'cost_reserved_best']
    number_fields = frozenset(['count', 'count_reserved', 'cost_ondemand', 'cost_reserved_worst', 'cost_reserved_best'])
    assert all(e in fields for e in number_fields)
    with open('instances-reservation-usage.us-east-1.csv') as f:
        reader = csv.DictReader(f)
        row_data = [
            {
                'values': [
                    {
                        'userEnteredValue': {
                            'stringValue': f,
                        },
                    }
                    for f in fields
                ] + [None, None, {
                    'userEnteredValue': { 'stringValue': 'surprise!' },
                }],
            }
        ] + [
            {
                'values': [
                    {
                        'userEnteredValue': {
                            ('numberValue' if f in number_fields else 'stringValue'): float(row[f]) if f in number_fields else row[f],
                        },
                    }
                    for f in fields
                ],
            }
            for row in reader
        ]

    spreadsheet = service.spreadsheets().create(body={
        'properties': {
            'title': 'my generated spreadsheet',
        },
        'sheets': {
            'data': [
                {
                    'startRow': 0,
                    'startColumn': 0,
                    'rowData': row_data,
                }
            ],
        },
    })

    print(spreadsheet)
    print(dir(spreadsheet))
    print(spreadsheet.execute())

if __name__ == '__main__':
    main()

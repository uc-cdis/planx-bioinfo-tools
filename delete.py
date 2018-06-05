#!/usr/bin/env python2

import requests
import sys
import getopt
import os
import argparse
import datetime
import time
import json

# change the following url to the url of your project:
parser = argparse.ArgumentParser(description="delete meta data")
# https://gtex.bionimbus.org/api/v0/submission/
parser.add_argument('-a', '--apiurl', required=True, help="project url for deletion")
# ndh-dmid-LHV
parser.add_argument('-p', '--project', required=True, help="project id for deletion")
parser.add_argument('-n', '--node', required=True, help="node to delete")
parser.add_argument('-k', '--authfile', required=True, help="API key file", default='credentials.json')
parser.add_argument('-l', '--length', type=int, required=True, help="length of the chunk to be deleted")
args = parser.parse_args()
project_url = args.apiurl + args.project.replace('-', '/', 1) + '/'
graphql_url = args.apiurl + "graphql"
chunk = args.length

# get keys
json_data = open(args.authfile).read()
keys = json.loads(json_data)
auth = requests.post('https://niaid.bionimbus.org/user/credentials/cdis/access_token', json=keys)
print(auth.text)

# Get id from submitter_id
query_txt = """query Test { %s (first:0, project_id: "%s") {id}} """ % (args.node, args.project)
query = {'query': query_txt}
print(graphql_url)
output = requests.post(graphql_url, headers={'Authorization': 'bearer ' + auth.json()['access_token']}, json=query).text
data = json.loads(output)
print(data)

list_ids = ""
count = 0
for id in data['data'][args.node]:
    list_ids += id['id'] + ","
    count += 1

    if count >= chunk:
        url = project_url + 'entities/' + list_ids[0:-1]
        tsv_text = requests.delete(url, headers={'Authorization': 'bearer ' + auth.json()['access_token']})
        print(tsv_text)
        count = 0
        list_ids = ""

url = project_url + 'entities/' + list_ids[0:-1]
tsv_text = requests.delete(url, headers={'Authorization': 'bearer ' + auth.json()['access_token']})
print(tsv_text)

# command line: python delete.py -a https://niaid.bionimbus.org/api/v0/submission/ -p ndh-dmid-LHV -n aliquot -k niaid_api.json -l 30

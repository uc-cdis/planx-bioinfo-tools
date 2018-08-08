#!/usr/bin/env python2
import requests
import sys
import getopt
import os
import argparse
import datetime
import time
import json
import pandas as pd

# change the following url to the url of your project:
parser = argparse.ArgumentParser(description="delete meta data")
parser.add_argument('-a', '--apiurl', required=True, help="data commons url")
parser.add_argument('-p', '--project', required=True, help="project id for deletion")
parser.add_argument('-n', '--node', required=True, help="node to delete")
parser.add_argument('-k', '--authfile', help="API key file", default='credentials.json')
parser.add_argument('-l', '--length', type=int, default=20, help="length of the chunk to be deleted")
parser.add_argument('-e', '--nentities', type=int, default=10000, help="number of entities to remove")
parser.add_argument('-f', '--file', default='', help="list of submitter_ids to remove")
args = parser.parse_args()

# Get needed URLs
token_url   = args.apiurl + "/user/credentials/cdis/access_token"
graphql_url = args.apiurl + "/api/v0/submission/graphql/"
project_url = args.apiurl + "/api2/v0/submission/" + args.project.replace('-', '/', 1) + '/'
chunk = args.length

# get keys
json_data = open(args.authfile).read()
keys = json.loads(json_data)

auth = requests.post(token_url, json=keys)

# Get id from submitter_id
query_txt = """query Test { %s (first:%s, project_id: "%s") {submitter_id id}}""" % (args.node, args.nentities, args.project)
query = {'query': query_txt}
output = requests.post(graphql_url, headers={'Authorization': 'bearer ' + auth.json()['access_token']}, json=query).text
data = json.loads(output)

# Get submitter_id list
submitter_ids = []
if args.file != '':
   table = pd.read_table(args.file,  sep="\t")
   submitter_ids = list(table['submitter_id'])
   print(submitter_ids)

# Remove all ids from one node by chunks
list_ids = ""
count = 0
total = 0
for id in data['data'][args.node]:
    if submitter_ids == [] or id['submitter_id'] in submitter_ids:
       list_ids += id['id'] + ","
       count += 1
    if count >= chunk:
        url = project_url + 'entities/' + list_ids[0:-1]
        print(url)
        itime = datetime.datetime.now()
        tsv_text = requests.delete(url, headers={'Authorization': 'bearer ' + auth.json()['access_token']}).text
        etime = datetime.datetime.now()
        print(tsv_text)
        print("Processed time: %s" % (etime-itime))
        count = 0
        total += chunk
        list_ids = ""

        if total % 1000 == 0:
          auth = requests.post(token_url, json=keys)

url = project_url + 'entities/' + list_ids[0:-1]
print(url)
tsv_text = requests.delete(url, headers={'Authorization': 'bearer ' + auth.json()['access_token']})
print(tsv_text)



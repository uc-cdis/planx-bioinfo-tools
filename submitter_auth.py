#!/usr/bin/env python2
import requests
import sys
import getopt
import os
import argparse
import datetime
import time
import json

parser = argparse.ArgumentParser(description="submit meta data")
parser.add_argument('-f', '--file', required=True, help="meta data to submit in tsv format")
parser.add_argument('-p', '--project', required=True, help="project url for submission")
parser.add_argument('-k', '--authfile', required=True, help="auth key file", default='credentials.json')
parser.add_argument('-l', '--length', type=int, required=True, help="length of the chunk to be submitted", default=100)
parser.add_argument('-r', '--row', required=True, help='initial row to submit', default=1)
args = parser.parse_args()

# get keys
json_data = open(args.authfile).read()
keys = json.loads(json_data)
auth = requests.post('https://niaid.bionimbus.org/user/credentials/cdis/access_token', json=keys)

header = ""
data = ""
count = 0
total = -1
nline = 0
# if there are multiple dots, splitext splits at the last one (so splitext('file.jpg.zip') gives ('file.jpg', '.zip')
outfile = "./output/submission_output_" + os.path.splitext(args.file)[0] + ".txt"
i = 2
while os.path.isfile(outfile):
    outfile = "./output/submission_output_" + os.path.splitext(args.file)[0] + "_" + str(i) + ".txt"
    i += 1
output = open(outfile, 'w')

with open(args.file, 'r') as file:
    for line in file:
        if nline == 0:
            header = line
            data = header + "\r"
        nline += 1
        if nline > int(args.row):
            data = data + line + "\r"
            count = count + 1
            total = total + 1
            if count > args.length:
                count = 1
                itime = datetime.datetime.now()
                #response = requests.put(args.project, data=data, auth=auth, headers={'content-type': 'text/tab-separated-values'})
                response = requests.put(args.project, data=data, headers={'content-type': 'text/tab-separated-values', 'Authorization': 'bearer ' + auth.json()['access_token']})
                etime = datetime.datetime.now()
                print("Submitted (" + str(total) + "): " + str(response) + " " + str(etime - itime))
                output.write("Submitted (" + str(total) + "): " + str(response))
                output.write(response.text)
                # print data
                data = header + "\r"

                # make it sleep after 10 chunks
                # if total % 1000 == 0:
                #     print "Sleeping for 3 min..."
                #     time.sleep(180)

response = requests.put(args.project, data=data, headers={'content-type': 'text/tab-separated-values', 'Authorization': 'bearer ' + auth.json()['access_token']})
print("Submitted (" + str(total) + "): " + str(response))
output.write("Submitted (" + str(total) + "): " + str(response))
output.write(response.text)

# python submitter_auth.py -f follow_up.tsv -p https://niaid.bionimbus.org/api/v0/submission/ndh/dmid-LHV/ -k niaid_api.json -l 100 -r 1

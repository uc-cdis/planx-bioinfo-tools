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
parser.add_argument('-a', '--apiurl', required=True, help="Data commons URL. E.g. https://niaid.bionimbus.org")
parser.add_argument('-p', '--project', required=True, help="project url for submission")
parser.add_argument('-k', '--authfile', required=True, help="auth key file")
parser.add_argument('-l', '--length', type=int, required=True, help="length of the chunk to be submitted")
parser.add_argument('-r', '--row', required=True, help='initial row to submit')
parser.add_argument('-o', '--output', default="./output/", help='output path to locate logs for submission')
args = parser.parse_args()

# Get needed URLs
token_url   = args.apiurl + "/user/credentials/cdis/access_token"
graphql_url = args.apiurl + "/api/v0/submission/graphql/"
project_url = args.apiurl + "/api/v0/submission/" + args.project.replace('-', '/', 1) + '/'

# get keys
json_data = open(args.authfile).read()
keys = json.loads(json_data)
auth = requests.post(token_url, json=keys)

header = ""
data = ""
count = 0
total = -1
nline = 0

# create output folder if doesn't exist
if not os.path.exists(args.output):
    os.makedirs(args.output)

# if there are multiple dots, splitext splits at the last one (so splitext('file.jpg.zip') gives ('file.jpg', '.zip')
outfile = args.output + "submission_output_" + os.path.splitext(args.file)[0] + ".txt"
i = 2
while os.path.isfile(outfile):
    outfile = args.output + "submission_output_" + os.path.splitext(args.file)[0] + "_" + str(i) + ".txt"
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
                response = requests.put(project_url, data=data, headers={'content-type': 'text/tab-separated-values', 'Authorization': 'bearer '+ auth.json()['access_token']}) 
                etime = datetime.datetime.now()
                print ("Submitted (" + str(total) + "): " + str(response) + " " + str(etime-itime))
                output.write("Submitted (" + str(total) + "): " + str(response))
                output.write(response.text)
                if "200" not in str(response):
                   print ("Submission failed. Stopping...")
                   break
                # print (data)
                data = header + "\r"

response = requests.put(project_url, data=data, headers={'content-type': 'text/tab-separated-values', 'Authorization': 'bearer '+ auth.json()['access_token']})
print ("Submitted (" + str(total) + "): " + str(response))
output.write("Submitted (" + str(total) + "): " + str(response))
output.write(response.text)

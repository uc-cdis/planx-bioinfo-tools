#!/usr/bin/env python2
import requests
import sys
import getopt
import os
import argparse
import datetime
import time
import json

parser = argparse.ArgumentParser(description="submit data to a gen3 data commons")
parser.add_argument('-f', '--file', required=True, help="meta data to submit in tsv format")
parser.add_argument('-a', '--apiurl', required=True, help="Data commons URL. E.g. https://niaid.bionimbus.org")
parser.add_argument('-p', '--project', required=True, help="project url for submission")
parser.add_argument('-k', '--authfile', required=True, help="auth key file")
parser.add_argument('-o', '--output', default="./output/", help='output path to locate logs for submission')


def submit(file, apiurl, project, authfile, output = "./output/"):
    # Get needed URLs
    token_url   = apiurl + "/user/credentials/cdis/access_token"
    project_url = apiurl + "/api/v0/submission/" + project.replace('-', '/', 1) + '/'

    # get keys
    json_data = open(authfile).read()
    keys = json.loads(json_data)
    auth = requests.post(token_url, json=keys)

    data = ""

    # create output folder if doesn't exist
    if not os.path.exists(output):
        os.makedirs(output)

    # if there are multiple dots, splitext splits at the last one (so splitext('file.jpg.zip') gives ('file.jpg', '.zip')
    outfile = output + "submission_output_" + os.path.splitext(file)[0] + ".txt"
    i = 2
    while os.path.isfile(outfile):
        outfile = output + "submission_output_" + os.path.splitext(file)[0] + "_" + str(i) + ".txt"
        i += 1
    output = open(outfile, 'w')

    with open(file, 'r') as file:
        total = -1
        count = 0
        header = file.readline()
        data = header
        for line in file:
            # submit the data at 100 records to prevent submitting too much data
            if count > 100:
                # submit the data you have and set data back to just the header
                print "Getting response from " + project_url
                itime = datetime.datetime.now()
                response = requests.put(project_url, data=data, headers={"content-type": "text/tab-separated-values", "Authorization": "bearer "+ auth.json()["access_token"]})
                etime = datetime.datetime.now()
                print "Submitted (" + str(total) + "): " + str(response) + " " + str(etime-itime)
                output.write("Submitted (" + str(total) + "): " + str(response))
                output.write(response.text)
                data = header
                count = 0
            data += line + "\n"
            total += 1
            count += 1
        print "Getting final response from " + project_url
        itime = datetime.datetime.now()
        response = requests.put(project_url, data=data, headers={"content-type": "text/tab-separated-values", "Authorization": "bearer "+ auth.json()["access_token"]})
        etime = datetime.datetime.now()
        print "Submitted (" + str(total) + "): " + str(response) + " " + str(etime-itime)
        output.write("Submitted (" + str(total) + "): " + str(response))
        output.write(response.text)

if __name__ == '__main__':
    args = parser.parse_args()
    submit(args.file, args.apiurl, args.project, args.authfile, args.output)


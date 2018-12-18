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
        header = file.readline()
        max_count = 100
        end_of_file_reached = False
        while not end_of_file_reached:
            data = header
            total = -1
            count = 0
            Timeout = False
            print "we are using a submission size of " + str(max_count)
            file.seek(0)
            for line in file:
                if count > max_count:
                    try:
                        # submit the data you have and set data back to just the header
                        print "Getting response from " + project_url
                        itime = datetime.datetime.now()
                        response = requests.put(project_url, data=data, headers={"content-type": "text/tab-separated-values", "Authorization": "bearer "+ auth.json()["access_token"]}, timeout=45)
                        etime = datetime.datetime.now()
                        print "Submitted (" + str(total) + "): " + str(response) + " in time: " + str(etime-itime)
                    except requests.exceptions.Timeout as errt:
                        print "THIS IS A TIMEOUT!!!!!!!! \n We are going to retry with a smaller submission size!"
                        Timeout = True
                        max_count = max_count / 2
                        break
                    output.write("Submitted (" + str(total) + "): " + str(response))
                    output.write(response.text)
                    data = header
                    count = 0
                data += line + "\n"
                total += 1
                count += 1
            if not Timeout and count > 0:
                try:
                    print "Getting final response from " + project_url
                    itime = datetime.datetime.now()
                    response = requests.put(project_url, data=data, headers={"content-type": "text/tab-separated-values", "Authorization": "bearer "+ auth.json()["access_token"]}, timeout=30)
                    etime = datetime.datetime.now()
                except requests.exceptions.Timeout as errt:
                    print "THIS IS A TIMEOUT!!!!!!!! \nWe are going to retry with a smaller submission size!"
                    Timeout = True
                    max_count = max_count / 2
                    continue
                print "Submitted (" + str(total) + "): " + str(response) + " " + str(etime-itime)
                output.write("Submitted (" + str(total) + "): " + str(response))
                output.write(response.text)
                end_of_file_reached = True

if __name__ == '__main__':
    args = parser.parse_args()
    submit(args.file, args.apiurl, args.project, args.authfile, args.output)


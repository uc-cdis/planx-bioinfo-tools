import subprocess
import json
import requests
import xml.etree.ElementTree as ET
import time
from joblib import Parallel, delayed
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter

'''
Considerations:
Maybe make the process run in parallel so it runs faster - it's ~10k+ files to download.

Need to figure out a way to log properly - how do we know the process ran completely and as intended?
How do we know if any of the retrievals failed?
How do we know if we are missing any fastq files?
'''

# make it a command line call, pass n_jobs and backend preference

def main():
    njobs, back = getArgs()
    sra_list = loadAccessions()
    # print type(sra_list)
    # print len(sra_list)
    # tmp = list(set([k[:3] for k in sra_list]))
    # print 'Prefixes: {}'.format(tmp)
    with open('fastqDumpLog.txt', 'w') as f:
        f.write('--- FASTQ DUMP LOG ---\n')
    start = time.time()
    print 'Running <{}> jobs with <{}> backend'.format(njobs, back)
    Parallel(n_jobs=njobs, backend=back)(delayed(getfastq)(sra) for sra in sra_list)
    end = time.time()
    print 'Run Duration: {} seconds'.format(end - start)

def getArgs():
    parser = ArgumentParser(
        formatter_class=RawTextHelpFormatter,
        prog="getfastq.py",
        description="Execute fastq-dump call for given list of SRAs."
    )
    parser.add_argument(
        "-n",
        "--n_jobs",
        dest = "njobs"
    )
    # 'threading' or 'loky'
    parser.add_argument(
        "-b",
        "--backend",
        dest = "backend"
    )
    args = parser.parse_args()
    njobs = int(args.njobs)
    back = args.backend.strip().lower()

    return njobs, back

def loadAccessions():
    '''
    Loads in list of SRA accession numbers from finalSRAList.json
    '''
    sra_list = json.load(open("finalSRAList.json", "r"))
    return sra_list

# sratoolkit/bin/fastq-dump --outdir ./testdir --gzip --skip-technical -I --split-files -X 1 SRR671803
# HERE: be sure the path to fastq-dump is correct
# could possibly pass path to fastq-dump at command call
def getfastq(sra):
    '''
    Input is an SRA accession number (string)
    Assembles and executes command to retrieve the fastq files
    Note on folder structure:
    Could possibly write each pair of files to its own directory
    Like fastq < sra < fastq_1, fastq_2
    '''
    print '\n--- API Call for {} ---\n'.format(sra)
    cmd = [
    "sratoolkit/bin/fastq-dump", # ensure path to fastq-dump command is correct
    "--outdir",
    "./fastqDump", # directory which will hold all the fast files
    "--gzip",
    "--skip-technical",
    "-I",
    "--split-files",
    sra # accession number here
    ]

    '''
    "-X", # only here for testing purposes
    "1", # only here for testing purposes
    '''

    with open('fastqDumpLog.txt', 'a+') as f:
        subprocess.call(cmd, stdout=f)

if __name__ == '__main__':
    main()

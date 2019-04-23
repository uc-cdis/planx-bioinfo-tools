import json, subprocess

def main():
    sras = getSRAs()
    for sra in sras:
        uploadFastq(sra)

def getSRAs():
    out = json.load(open('emptyPairs.json'))
    return out

def uploadFastq(sra):
    cmd = [
    '/home/ubuntu/go/bin/gen3-client',
    'upload',
    '--profile=matt',
    '--upload-path=/mnt/ariba_run/fastqDump/{}_[12].fastq.gz'.format(sra)
    ]

    subprocess.call(cmd)

if __name__ == '__main__':
    main()

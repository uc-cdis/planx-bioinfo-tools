from zipfile import ZipFile
from joblib import Parallel, delayed
import os, json, time

def main():
    sra_list = getSRA()
    iterZip(sra_list)

def mkdir(dir):
    try:
        os.mkdir(dir)
    except:
        pass

def getSRA():
    '''Load in list of SRAs from uniqueSRA.json'''
    sra_list = json.load(open('uniqueSRA.json'))
    return sra_list

def iterZip(sra_list):
    '''Zips pairs of fastq files.'''
    global log

    mkdir('zipOut')
    mkdir('zipOut/objects')

    log = {
    'pass': {'count': 0, 'list': []},
    'fail': {'count': 0, 'list': []},
    'time': 0,
    'sra_count': len(sra_list)
    }

    print len(sra_list)

    then = time.time()
    Parallel(n_jobs=30, prefer='threads')(delayed(zip)(sra) for sra in sra_list)
    now = time.time()

    dur = now - then
    log['time'] = dur

    with open('zipOut/log.json', 'w') as f:
        f.write(json.dumps(log, indent=2))

def zip(sra):
    '''Zip the two fastq's corresponding to this sra into an archive.'''
    zipfile = 'zipOut/objects/{}.zip'.format(sra)
    with ZipFile(zipfile, 'w', allowZip64=True) as z:
        try:
            for i in [1,2]:
                f = 'fastqDump/{}_{}.fastq.gz'.format(sra, i) #SRR6152696_2.fastq.gz
                z.write(f)
            log['pass']['list'].append(sra)
            log['pass']['count'] += 1
        except:
            log['fail']['list'].append(sra)
            log['fail']['count'] += 1
            os.remove(zipfile) # delete the faulty/empty archive



if __name__ == '__main__':
    main()

from zipfile import ZipFile
import os, json

def main():
    sra_list = getSRA()
    zip(sra_list)

def mkdir(dir):
    try:
        os.mkdirs(dir)
    except:
        pass

def getSRA():
    '''Load in list of SRAs from uniqueSRA.json'''
    sra_list = json.load(open('uniqueSRA.json'))
    return sra_list

def zip(sra_list):
    '''Zips pairs of fastq files.'''
    mkdir('zipOut/objects')
    log = open('zipOut/log.txt', 'w')
    for sra in sra_list:
        zipfile = 'zipOut/objects/{}.zip'.format(sra)
        with ZipFile(zipfile, 'w') as z:
            log.write('-- {} --\n'.format(sra))
            for i in [1,2]:
                f = 'fastqDump/{}_{}.fastq.gz'.format(sra, i) #SRR6152696_2.fastq.gz
                try:
                    z.write(f)
                    log.write('Successfully zipped {}\n'.format(f))
                except:
                    log.write('Error zipping {}\n'.format(f))
    log.close()

if __name__ == '__main__':
    main()

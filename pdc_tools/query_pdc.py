import requests
import json
import string
from collections import defaultdict
from bs4 import BeautifulSoup
import re
import os
import sys
import hashlib


pdc_metadata = defaultdict(list)
raw_file_name_to_id = {} # other types of files link to RAW files


def get_all_files(study_id, folder_name):
    print('processing file urls and sizes')
    files = []
    cksum = []

    url0 = 'https://cptc-xfer.uis.georgetown.edu/publicData/Phase_II_Data/CPTAC_Breast_Cancer_S039/'
    page = requests.get(url0).text
    parsed_page = BeautifulSoup(page, 'html.parser')
    dir1 = [
        url0 + node.get('href')
        for node in parsed_page.find_all('a')
        if node.get('href').endswith('/')
        and folder_name in node.get('href')
    ]

    for url1 in dir1:
        page = requests.get(url1).text
        parsed_page = BeautifulSoup(page, 'html.parser')
        cksum.extend([
            url1 + node.get('href')
            for node in parsed_page.find_all('a')
            if node.get('href').endswith('cksum')
        ])
        dir2 = [
            url1 + node.get('href')
            for node in parsed_page.find_all('a')
            if node.get('href').endswith('_PSM/')
            or node.get('href').endswith('_mzML/')
            or node.get('href').endswith('_raw/')
        ]

        for url2 in dir2:
            page = requests.get(url2).text
            parsed_page = BeautifulSoup(page, 'html.parser')
            dir3 = []
            for node in parsed_page.find_all('a'):
                u = url2 + node.get('href')
                if node.get('href').endswith('cksum'):
                    cksum.append(u)
                elif node.get('href').endswith('_mzIdentML/') or node.get('href').endswith('_tsv/'):
                    dir3.append(u)
            
            if len(dir3) > 0:
                for url3 in dir3:
                    page = requests.get(url3).text
                    parsed_page2 = BeautifulSoup(page, 'html.parser')
                    files.extend([
                        url3 + node.get('href')
                        for node in parsed_page2.find_all('a')
                        if node.get('href').endswith('.raw')
                        or node.get('href').endswith('.mzML.gz')
                        or node.get('href').endswith('.mzid.gz')
                        or node.get('href').endswith('.psm')
                    ])
            
            files.extend([
                url2 + node.get('href')
                for node in parsed_page.find_all('a')
                if node.get('href').endswith('.raw')
                or node.get('href').endswith('.mzML.gz')
                or node.get('href').endswith('.mzid.gz')
                or node.get('href').endswith('.psm')
            ])

        # break
    
    files_dict = defaultdict(dict)

    # get the file urls
    for f in files:
        file_name = f.split('/')[len(f.split('/'))-1]
        # return
        date = get_file_date(f)
        t = ''
        if '.mzML.gz' in f:
            t = 'MZML'
        elif '.raw.cap.psm' in f:
            t = 'PSM-TSV'
        elif '.mzid.gz' in f:
            t = 'PSM-MZID'
        elif '.raw' in f:
            t = 'RAW'
        else:
            print('No type for {}'.format(f))
        if not t in files_dict[date].keys():
            files_dict[date][t] = defaultdict(dict)
        files_dict[date][t][file_name]['url'] = f
    
    # get the file sizes
    for f in cksum:
        t = ''
        if '_mzML.cksum' in f:
            t = 'MZML'
        elif '_tsv.cksum' in f:
            t = 'PSM-TSV'
        elif '_mzIdentML.cksum' in f:
            t = 'PSM-MZID'
        elif '_raw.cksum' in f:
            t = 'RAW'
        else:
            print('No type for {}'.format(f))
        page = requests.get(f).text
        parsed_page = BeautifulSoup(page, 'html.parser')
        for line in parsed_page:
            i = 0
            info = line.split()
            while (i < len(info)):
                file_size = int(info[i+2])
                file_name = info[i+3]
                date = get_file_date(file_name)
                try:
                    files_dict[date][t][file_name]['file_size'] = file_size
                except:
                    print('Coult not find date {} for file {} in files dict'.format(date, f))
                    # return
                i += 4
    
    # write results in file
    print(len(files), 'files found')
    with open(study_id+'/files_list', 'w') as f:
        json.dump(files_dict, f, indent=4)
    
    return files_dict


def get_study_info(study_submitter_id):
    print('processing study', study_submitter_id)
    query = """
    {{
        uiStudy (study_submitter_id: "{}") {{
            study_submitter_id
            project_name
            analytical_fraction
            experiment_type
        }}
    }}""".format(study_submitter_id) # removed submitter_id_name program_name disease_type primary_site
    study_data = query_pdc(query)['data']['uiStudy'][0]
    study_data['study_description'] = ''
    study_data['submitter_id'] = study_data.pop('study_submitter_id') # rename
    study_data['type'] = 'study'

    pdc_metadata['study'].append(study_data)
    # will be saved in file after program/project


def get_getPaginatedFiles_query(study_submitter_id, file_type):
    query = """
    {{
        getPaginatedFiles (study_submitter_id: "{}", offset: 0, limit: 10000, file_type: "{}") {{
            files {{
                file_name
                file_type
                md5sum
            }}
        }}
    }}""".format(study_submitter_id, file_type)
    return query


def get_files_for_study(study_submitter_id):
    print('processing files:')

    query = get_getPaginatedFiles_query(study_submitter_id, 'RAW')
    raw_files_data = query_pdc(query)['data']['getPaginatedFiles']['files']

    query = get_getPaginatedFiles_query(study_submitter_id, 'PSM')
    psm_files_data = query_pdc(query)['data']['getPaginatedFiles']['files']
    # not_raw_files_data = psm_files_data
    query = get_getPaginatedFiles_query(study_submitter_id, 'MZML')
    mzml_files_data = query_pdc(query)['data']['getPaginatedFiles']['files']
    not_raw_files_data = psm_files_data + mzml_files_data

    # first we need to process RAW files, to create the links to RAW files in the other files and in the workflow
    print(' raw files:')
    files = process_files(raw_files_data) # first, RAW files
    for file_type in files:
        for item in files[file_type]:
            item['type'] = file_type
        pdc_metadata[file_type].extend(files[file_type])
    
    # write results in files
    with open(study_id+'/raw_protein_mass_spectrometry.json', 'w') as f:
        json.dump(pdc_metadata['raw_protein_mass_spectrometry'], f, indent=4)
    with open(study_id+'/raw_file_name_to_id.json', 'w') as f:
        json.dump(raw_file_name_to_id, f, indent=4)

    # then we need to process the proteomic workflow, to create the links in the non-RAW files
    get_workflow_for_study(study_id)

    print(' non-raw files:')
    files = process_files(not_raw_files_data) # then, other files
    for file_type in files:
        for item in files[file_type]:
            item['type'] = file_type
        pdc_metadata[file_type].extend(files[file_type])
    
    # write results in files
    with open(study_id+'/psm_protein_mass_spectrometry.json', 'w') as f:
        json.dump(pdc_metadata['psm_protein_mass_spectrometry'], f, indent=4)
    with open(study_id+'/mzml_protein_mass_spectrometry.json', 'w') as f:
        json.dump(pdc_metadata['mzml_protein_mass_spectrometry'], f, indent=4)

    # write results in files
    # for k in pdc_metadata.keys():
    #     if k.endswith('protein_mass_spectrometry'):
    #         with open(study_id+'/'+k+'.json', 'w') as f:
    #             json.dump(pdc_metadata[k], f, indent=4)


def get_protein_expression_for_study(study_submitter_id):
    print('processing protein expression files:')

    url0 = 'https://cptc-xfer.uis.georgetown.edu/publicData/Phase_II_Data/CPTAC_Breast_Cancer_S039/'
    page = requests.get(url0).text
    parsed_page = BeautifulSoup(page, 'html.parser')
    protein_reports_dir = [
        url0 + node.get('href')
        for node in parsed_page.find_all('a')
        if node.get('href').endswith('/')
        and folder_name in node.get('href')
        and '_Protein_Report' in node.get('href')
    ]

    files = []
    for url1 in protein_reports_dir:
        page = requests.get(url1).text
        parsed_page = BeautifulSoup(page, 'html.parser')
        table_rows = parsed_page.find('table').find_all('tr')
        links = [
            node
            # url1 + node.get('href')
            for node in parsed_page.find_all('a')
            if folder_name in node.get('href')
        ]
        for l in links:
            files.append({
                'file_name': l.getText(),
                'urls': url1 + l.get('href')
            })
        # for row in table_rows:
        #     cols = row.find_all('td')
        #     cols = [ele.text.strip() for ele in cols]
        #     if len(cols) > 3 and folder_name in cols[1]:
        #         file_name = cols[1]
        #         file_size_str = cols[3]
        #         file_size = float(file_size_str[:len(file_size_str) - 1])
        #         if file_size_str.endswith('K'):
        #             file_size *= 1024
        #         elif file_size_str.endswith('M'):
        #             file_size *= 1024 * 1024
        #         else:
        #             raise('File size {} for file {} does not end with K or M'.format(file_name, file_size_str))
        #         files.append({
        #             'file_name': file_name,
        #             'file_size': int(round(file_size)),
        #             'urls': urls.pop(0)
        #         })

    # link workflow/RAW files
    all_raw_submitter_ids = [
        {'submitter_id': raw['submitter_id']}
        for raw in pdc_metadata['raw_protein_mass_spectrometry']
    ]

    # protein expression is derived from the raw data, so these are the same as the raw:
    data_category = pdc_metadata['raw_protein_mass_spectrometry'][0]['data_category']
    experimental_strategy = pdc_metadata['raw_protein_mass_spectrometry'][0]['experimental_strategy']

    for f in files:
        f['file_name'] = f['file_name'].rstrip() # get rid of the \r at the end of file names
        print('', f['file_name'])
        f['original_file_name'] = f['file_name'] # there is nothing in 'filesPerStudy' or 'getPaginatedFiles' that can help associating name with original name. so keeping original name for both
        
        data = requests.get(f['urls']).content
        f['file_size'] = sys.getsizeof(data)
        f['md5sum'] = hashlib.md5(data).hexdigest() # it is empty in 'filesPerStudy' and 'getPaginatedFiles', so let's generate it here
        
        parts = f['file_name'].split('.')
        extension = parts[len(parts) - 1].upper()
        f['data_type'] = extension
        f['data_format'] = extension
        
        f['data_category'] = data_category
        f['experimental_strategy'] = experimental_strategy

        submitter_id = build_file_submitter_id(f['original_file_name'], f['data_category'])
        f['submitter_id'] = submitter_id

        f['proteomic_workflows'] = {
            'submitter_id': pdc_metadata['proteomic_workflow'][0]['submitter_id']
        }
        f['raw_protein_mass_spectrometries'] = all_raw_submitter_ids

        f['type'] = 'protein_expression'
        # print(json.dumps(f, indent=4))
        # break
    
    pdc_metadata['protein_expression'] = files
    with open(study_id+'/protein_expression.json', 'w') as f:
        json.dump(pdc_metadata['protein_expression'], f, indent=4)


def get_samples_with_files():
    raws = pdc_metadata['raw_protein_mass_spectrometry']
    samples_with_files_ids = []
    for f in raws:
        for s in f['samples']:
            samples_with_files_ids.append(s['submitter_id'])
    return samples_with_files_ids


def get_subjects_with_files():
    sample_ids = get_samples_with_files()
    subjects_with_files_ids = set()
    query = """
    {
        allCases {
            case_submitter_id
            samples {
                sample_submitter_id
            }
        }
    }"""
    subjects = query_pdc(query)['data']['allCases']
    for sub in subjects:
        for sam in sub['samples']:
            if sam['sample_submitter_id'] in sample_ids:
                subjects_with_files_ids.add(sub['case_submitter_id'])
    return subjects_with_files_ids


def get_subjects_for_study(study_submitter_id):
    print('processing subjects')
    subject_ids = get_subjects_with_files()
    # print(len(all_subject_ids))
    # return
    i = 0
    for s in subject_ids:
        process_subject(s, study_submitter_id)
        i+=1
        if (i % 50 == 0 or i == len(subject_ids)):
            print(' ', i, '/', len(subject_ids))
        # break

    # write results in files
    node_list = ['subject', 'sample', 'demographic', 'diagnosis']
    clean_up_dict(node_list)
    for k in node_list:
        for item in pdc_metadata[k]:
            item['type'] = k
        with open(study_id+'/'+k+'.json', 'w') as f:
            json.dump(pdc_metadata[k], f, indent=4)


def process_subject(subject_id, study_submitter_id):
    query = """
    {{
        case (case_submitter_id: "{}") {{
            case_submitter_id
            tissue_source_site_code
            days_to_lost_to_followup
            disease_type
            index_date
            lost_to_followup
            primary_site
            demographics {{
                demographic_submitter_id
                ethnicity
                gender
                race
                cause_of_death
                days_to_birth
                days_to_death
                vital_status
                year_of_birth
                year_of_death
            }}
            diagnoses {{
                diagnosis_submitter_id
                age_at_diagnosis
                classification_of_tumor
                days_to_last_follow_up
                days_to_last_known_disease_status
                days_to_recurrence
                last_known_disease_status
                morphology
                primary_diagnosis
                progression_or_recurrence
                site_of_resection_or_biopsy
                tissue_or_organ_of_origin
                tumor_grade
                tumor_stage
                vital_status
                days_to_birth
                days_to_death
                prior_malignancy
                ajcc_clinical_m
                ajcc_clinical_n
                ajcc_clinical_stage
                ajcc_clinical_t
                ajcc_pathologic_m
                ajcc_pathologic_n
                ajcc_pathologic_stage
                ajcc_pathologic_t
                ann_arbor_b_symptoms
                ann_arbor_clinical_stage
                ann_arbor_extranodal_involvement
                ann_arbor_pathologic_stage
                best_overall_response
                burkitt_lymphoma_clinical_variant
                cause_of_death
                circumferential_resection_margin
                colon_polyps_history
                days_to_best_overall_response
                days_to_diagnosis
                days_to_hiv_diagnosis
                days_to_new_event
                figo_stage
                hiv_positive
                hpv_positive_type
                hpv_status
                iss_stage
                laterality
                ldh_level_at_diagnosis
                ldh_normal_range_upper
                lymph_nodes_positive
                lymphatic_invasion_present
                method_of_diagnosis
                new_event_anatomic_site
                new_event_type
                overall_survival
                perineural_invasion_present
                prior_treatment
                progression_free_survival
                progression_free_survival_event
                residual_disease
                vascular_invasion_present
                year_of_diagnosis
            }}
            samples {{
                gdc_sample_id
                gdc_project_id
                sample_submitter_id
                sample_type
                biospecimen_anatomic_site
                composition
                current_weight
                days_to_collection
                days_to_sample_procurement
                diagnosis_pathologically_confirmed
                freezing_method
                initial_weight
                Intermediate_dimension
                is_ffpe
                longest_dimension
                method_of_sample_procurement
                oct_embedded
                pathology_report_uuid
                preservation_method
                sample_type_id
                shortest_dimension
                time_between_clamping_and_freezing
                time_between_excision_and_freezing
                tissue_type
                tumor_code
                tumor_code_id
                tumor_descriptor
                aliquots {{
                    analyte_type
                }}
            }}
        }}
    }}""".format(subject_id) # removed diagnosis.disease_type and diagnosis.cases_count
    subject = query_pdc(query)['data']['case']
    demographics = subject['demographics'].copy()
    diagnoses = subject['diagnoses'].copy()
    samples = subject['samples'].copy()
    del subject['demographics']
    del subject['diagnoses']
    del subject['samples']
    if subject['index_date'] == "": # this is an enum, so empty=error
        del subject['index_date']

    subject['submitter_id'] = subject.pop('case_submitter_id') # rename
    subject['studies'] = {
        'submitter_id': study_submitter_id
    }
    pdc_metadata['subject'].append(subject)

    for demographic in demographics:
        demographic['submitter_id'] = demographic.pop('demographic_submitter_id') # rename
        demographic['subjects'] = {
            'submitter_id': subject_id
        }

        # remove unknown ints
        if demographic['year_of_birth']:
            demographic['year_of_birth'] = int(demographic['year_of_birth']) # to integer
        else:
            del demographic['year_of_birth']
        if demographic['days_to_birth']:
            demographic['days_to_birth'] = int(demographic['days_to_birth'])
        else:
            del demographic['days_to_birth']
        if demographic['days_to_death']:
            demographic['days_to_death'] = int(demographic['days_to_death'])
        else:
            del demographic['days_to_death']
        if demographic['year_of_death']:
            demographic['year_of_death'] = int(demographic['year_of_death'])
        else:
            del demographic['year_of_death']

        # unknown enum
        if demographic['ethnicity'] == "":
            demographic['ethnicity'] = "Unknown"
        if demographic['race'] == "":
            demographic['race'] = "Unknown"

        pdc_metadata['demographic'].append(demographic)

    for diagnosis in diagnoses:
        diagnosis['submitter_id'] = diagnosis.pop('diagnosis_submitter_id') # rename
        diagnosis['subjects'] = {
            'submitter_id': subject_id
        }
        pdc_metadata['diagnosis'].append(diagnosis)

    for sample in samples:
        sample['submitter_id'] = sample.pop('sample_submitter_id') # rename
        sample['intermediate_dimension'] = sample.pop('Intermediate_dimension') # rename
        sample['subjects'] = {
            'submitter_id': subject_id
        }
        sample['composition'] = sample['aliquots'][0]['analyte_type']
        del sample['aliquots']
        del sample['composition'] # 'Protein' not in composition enum dict -> remove for now (TODO?)

        # remove unknown ints
        if not sample['days_to_sample_procurement']:
            del sample['days_to_sample_procurement']
        if not sample['days_to_collection']:
            del sample['days_to_collection']
        if not sample['initial_weight']:
            del sample['initial_weight']

        # remove unknown enum
        if not sample['is_ffpe']:
            del sample['is_ffpe']
        if not sample['current_weight']:
            del sample['current_weight']
        if not sample['biospecimen_anatomic_site']:
            del sample['biospecimen_anatomic_site']
        
        pdc_metadata['sample'].append(sample)


def process_files(files_data):
    lookup_node_name = {
        'RAW': 'raw_protein_mass_spectrometry',
        'PSM': 'psm_protein_mass_spectrometry',
        'MZML': 'mzml_protein_mass_spectrometry',
        'PROT_ASSEM': 'protein_expression'
    }
    result = defaultdict(list)
    i=0
    for f in files_data:
        raw_file_name = f.get('file_name', '')
        f['file_name'] = raw_file_name.rstrip() # get rid of the \r at the end of file names

        # separate raw, psm and mwml files
        file_type = f.get('file_type', '')
        del f['file_type']
        node_name = lookup_node_name.get(file_type, None)
        if node_name:
            parts = f['file_name'].split('.')
            # data_format is 'TSV', 'RAW', 'MZID.GZ' or 'MZML.GZ'
            f['data_format'] = '.'.join(parts[1:]).upper() # complete file extension
            f['data_type'] = file_type # for RAW and MZML
            if file_type == 'PSM': # for PSM-MZID and PSM-TSV
                if '.mzid' in raw_file_name:
                    f['data_type'] = 'PSM-MZID'
                elif '.psm' in raw_file_name:
                    f['data_type'] = 'PSM-TSV'
                    f['data_format'] = 'TSV'
                else:
                    print('Could not check if PSM file is PSM-MZID or PSM-TSV for file {}'.format(raw_file_name))
            # try:
            #     data_type = more_data_dict[f['file_name']][file_type]
            #     print(data_type, f['data_type'])
            # except:
            #     print('no')
            # if f['data_type'] != data_type:

            print(f)
            file_metadata = get_file_metadata(f['file_name'], f['data_type']) # get the metadata for this file

            # instrument and faction are moved to run_study_meta_data
            del file_metadata['instrument']
            del file_metadata['fraction']

            f.update(file_metadata)
            date = get_file_date(f.get('original_file_name', ''))
            del f['folder_name'] # remove unused data from file

            # there is no '20170527' folder... the files are in the '20170515' folder
            # if date == '20170527':
            #     date = '20170515'

            # file size and url
            try:
                f['file_size'] = files_dict[date][f['data_type']][f['original_file_name']]['file_size']
                f['urls'] = files_dict[date][f['data_type']][f['original_file_name']]['url']
                # f['file_size'] = int(all_file_sizes[date][f['data_type']])
            except:
                print('Could not find file size and url for file {} (folder date: {})'.format(f['original_file_name'], date))
                f['file_size'] = None
                f['urls'] = None
                # break

            # link to the file  
            # f['urls'] = get_file_url(f.get('original_file_name', ''), date, f.get('data_type', ''))

            # link RAW/non-RAW
            name_without_extension = f['original_file_name'].split('.')[0]
            if file_type == 'RAW':
                raw_file_name_to_id[name_without_extension] = file_metadata['submitter_id']
            else:
                raw_submitter_id = raw_file_name_to_id.get(name_without_extension, '')
                f['raw_protein_mass_spectrometries'] = {
                    'submitter_id': raw_submitter_id
                }
            
            # link workflow/non-RAW (assuming there is only one workflow per study)
            if file_type != 'RAW':
                f['proteomic_workflows'] = {
                    'submitter_id': pdc_metadata['proteomic_workflow'][0]['submitter_id']
                }

            result[node_name].append(f)

        else:
            print('Could not get file node type for type {} of file {}: ignoring file'.format(file_type, f['file_name']))

        i+=1
        if (i % 50 == 0 or i == len(files_data)):
            print(' ', i, '/', len(files_data))
        # if (i >= 100):
        #     break
        # if i >= 1:
        # if file_type == 'MZML':
        # if not f.get('urls', None):
        #     print(f)
            # break
        # break
    return result


def get_file_date(file_path):
    parts = file_path.split('/')
    file_name = parts[len(parts) - 1]
    # parse date from file name
    found = re.search('[_][0-9]{8}', file_name)
    if found:
        date = found.group()[1:]
        # print(date)
    else:
        print(('Could not find date for folder {}'.format(file_name)))
        date = ''
        # raise Exception('Could not find date for folder {}'.format(folder_name))
    return date


def get_file_metadata(file_name, data_type):
    query = """
    {{
        getFileMetadata (file_name: "{}\\r") {{
            original_file_name
            folder_name
            sample_submitter_id
            instrument
            fraction
            experiment_type
            analyte
        }}
    }}""".format(file_name) # removed file_location
    all_metadata = query_pdc(query)['data']['getFileMetadata']

    # some metadata is common to all samples
    file_metadata = all_metadata[0].copy()
    del file_metadata['sample_submitter_id']
    file_metadata['experimental_strategy'] = file_metadata.pop('experiment_type') # rename
    file_metadata['data_category'] = file_metadata.pop('analyte')
    file_metadata['submitter_id'] = build_file_submitter_id(file_metadata['original_file_name'], file_metadata['data_category'])

    # link sample to raw file
    if data_type == 'RAW':
        # i = 1
        file_metadata['samples'] = []
        for sample in all_metadata:
            file_metadata['samples'].append({'submitter_id': sample['sample_submitter_id']})
            # file_metadata['samples'].append({
            #     'submitter_id': sample['sample_submitter_id']
            # })
            # file_metadata['sample_submitter_id#' + str(i)] = sample.get('sample_submitter_id', None)
            # i += 1

    return file_metadata


def build_file_submitter_id(original_file_name, data_category):
    parts = original_file_name.split('_')
    last = parts[len(parts)-1]
    extensions = parts[len(parts)-1].split('.')
    if extensions[0].lower() == data_category.lower(): # for protein_expression
        to_add = extensions[1]
    elif '.raw.cap.psm' in last:
        to_add = '{}_{}'.format(extensions[0], 'tsv')
    else:
        to_add = '_'.join(extensions[:2])
    return '{}_{}_{}'.format(parts[0], data_category.lower(), to_add.lower())


def get_workflow_for_study(study_submitter_id):
    print('processing proteomic workflow')

    # link workflow/RAW files
    all_raw_submitter_ids = [
        {'submitter_id': raw['submitter_id']}
        for raw in pdc_metadata['raw_protein_mass_spectrometry']
    ]

    query = """
    {{
        workflowMetadata (study_submitter_id: "{}") {{
            workflow_metadata_submitter_id
            refseq_database_version
            uniport_database_version
            hgnc_version
            raw_data_processing
            raw_data_conversion
            sequence_database_search
            search_database_parameters
            phosphosite_localization
            ms1_data_analysis
            psm_report_generation
            cptac_dcc_mzidentml
            mzidentml_refseq
            mzidentml_uniprot
            gene_to_prot
            cptac_galaxy_workflows
            cptac_galaxy_tools
            cdap_reports
            cptac_dcc_tools
        }}
    }}""".format(study_submitter_id) # removed protocol_submitter_id analytical_fraction study_submitter_name cptac_study_id
    # instrument study_submitter_id submitter_id_name experiment_type
    workflow_data = query_pdc(query)['data']['workflowMetadata']
    if len(workflow_data) > 1:
        print('Found more than one proteomic_workflow for this study :s Using the first one to proceed.')
    workflow_data = workflow_data[0]
    workflow_data['submitter_id'] = workflow_data.pop('workflow_metadata_submitter_id') # rename
    workflow_data['raw_protein_mass_spectrometries'] = all_raw_submitter_ids
    pdc_metadata['proteomic_workflow'].append(workflow_data)
    # search_database_parameters contains unicode characters but they may be handled properly when we submit: maybe not a problem?

    # write results in files
    clean_up_dict(['proteomic_workflow'])
    for item in pdc_metadata['proteomic_workflow']:
        item['type'] = 'proteomic_workflow'
    with open(study_id+'/proteomic_workflow.json', 'w') as f:
        json.dump(pdc_metadata['proteomic_workflow'], f, indent=4)


def get_protocol_for_study(study_submitter_id):
    print('processing protocol')
    query = """
    {{
        uiProtocol (study_submitter_id: "{}") {{
            protocol_submitter_id
            asp_enrichment
            asp_fractions
            asp_starting_amount
            asp_labelling
            cp_column_type
            cp_column_length
            cp_inside_diameter
            cp_particle_size
            cp_particle_type
            cp_gradient_length
            msp_name
            msp_instrument
            msp_dissociation
            msp_ms1_resolution
            msp_ms2_resolution
            msp_collision_energy
        }}
    }}""".format(study_submitter_id) # removed protocol_id project_submitter_id protocol_submitter_name analytical_fraction experiment_type asp_name
    # asp_type asp_proteolysis asp_alkylation asp_fractionation asp_updated asp_document cp_name cp_injected cp_updated
    # cp_document msp_type msp_precursors msp_updated msp_document
    protocol = query_pdc(query)['data']['uiProtocol'][0]
    protocol['studies'] = {
        'submitter_id': study_submitter_id
    }
    protocol = protocol_field_mapping(protocol)
    protocol['ms1_resolution'] = int(protocol['ms1_resolution']) # to integer
    protocol['ms2_resolution'] = int(protocol['ms2_resolution'])
    pdc_metadata['protocol'].append(protocol)

    # write results in files
    clean_up_dict(['protocol'])
    for item in pdc_metadata['protocol']:
        item['type'] = 'protocol'
    with open(study_id+'/protocol.json', 'w') as f:
        json.dump(pdc_metadata['protocol'], f, indent=4)


def protocol_field_mapping(protocol):
    protocol['submitter_id'] = protocol.pop('protocol_submitter_id') # rename
    protocol['enrichment_strategy'] = protocol.pop('asp_enrichment')
    protocol['ms1_resolution'] = protocol.pop('msp_ms1_resolution')
    protocol['ms2_resolution'] = protocol.pop('msp_ms2_resolution')
    protocol['starting_amount'] = protocol.pop('asp_starting_amount')
    protocol['dissociation_type'] = protocol.pop('msp_dissociation')
    protocol['instrument_model'] = protocol.pop('msp_instrument')
    protocol['protocol_name'] = protocol.pop('msp_name')
    protocol['collision_energy'] = protocol.pop('msp_collision_energy')
    protocol['column_inner_diameter'] = protocol.pop('cp_inside_diameter')
    protocol['column_type'] = protocol.pop('cp_column_type')
    protocol['column_length'] = protocol.pop('cp_column_length')
    protocol['particle_size'] = protocol.pop('cp_particle_size')
    protocol['particle_type'] = protocol.pop('cp_particle_type')
    protocol['fractions_produced_count'] = protocol.pop('asp_fractions')
    protocol['gradient_length'] = protocol.pop('cp_gradient_length')
    protocol['labeling_strategy'] = protocol.pop('asp_labelling')
    return protocol


def get_study_run_metadata(study_submitter_id):
    # we can get the study_run_metadata fields from any random file of the study
    # file_name = files_data[0].get('file_name', None).rstrip()
    # file_metadata = get_file_metadata(file_name)
    # pdc_metadata['study_run_metadata'].append({
    #     'study_submitter_id': study_submitter_id,
    #     'instrument': file_metadata.get('instrument'),
    #     'fraction': file_metadata.get('fraction')
    # })

    print('processing study_run_metadata')
    print('/!\ this is harcoded and depends on the study')
    study_run_metadata = {
        'submitter_id': 'SRM-S039-1',
        'analyte': 'protein',
        'experiment_number': 425,
        'experiment_type': 'TMT10',
        'fraction': 'proteome',
        'instrument': 'Orbitrap Fusion',
        'studies': {
            'submitter_id': study_submitter_id
        },
        'protocols': {
            'submitter_id': pdc_metadata['protocol'][0]['submitter_id']
        }
    }
    pdc_metadata['study_run_metadata'].append(study_run_metadata)

    # write results in files
    clean_up_dict(['study_run_metadata'])
    for item in pdc_metadata['study_run_metadata']:
        item['type'] = 'study_run_metadata'
    with open(study_id+'/study_run_metadata.json', 'w') as f:
        json.dump(pdc_metadata['study_run_metadata'], f, indent=4)


def get_program_project():
    print('processing program and project')
    query = """
    {{
        program (program_submitter_id: "{}") {{
            program_submitter_id
            name
            projects {{
                    project_submitter_id
                    name
            }}
        }}
    }}""".format('CPTAC') # we could get the program_submitter_id from the study.program_name?
    program = query_pdc(query)['data']['program']
    program['dbgap_accession_number'] = program.pop('program_submitter_id') # rename
    projects = program['projects']
    for project in projects:
        # only add the project that contains this study
        if project['name'] == pdc_metadata['study'][0]['project_name']:
            # link program to project
            project['programs'] = {
                'name': program['dbgap_accession_number']
            }
            project['code'] = project['project_submitter_id']
            project['dbgap_accession_number'] = project['code']
            del project['project_submitter_id']
            # pdc_metadata['project'].append(project)
            pdc_metadata['project'] = project

            # link project to study
            for study in pdc_metadata['study']:
                study['projects'] = {
                    'code': project['code']
                }
    del pdc_metadata['study'][0]['project_name'] # remove unused data from study
    del program['projects']

    pdc_metadata['program'] = program

    # write results in files
    node_list = ['program', 'project']
    for k in node_list:
        pdc_metadata[k]['type'] = k
        with open(study_id+'/'+k+'.json', 'w') as f:
            json.dump(pdc_metadata[k], f, indent=4)
    
    with open(study_id+'/study.json', 'w') as f:
            json.dump(pdc_metadata['study'], f, indent=4)


def clean_up_dict(node_list): # remove None keys
    for node in pdc_metadata:
        if node in node_list:
            for item in pdc_metadata[node]:
                for key in item:
                    if item[key] is None:
                        item[key] = ""
    # return pdc_metadata


def query_pdc(query):
    api_url = 'http://pdc.esacinc.com/graphql'
    response = requests.post(api_url, headers={'Content-Type': 'application/json'}, json={'query': query})

    data = json.loads(response.content)
    if data.get('errors', None):
        raise Exception(data['errors'][0]['message'])
    return data


def compare():
    # check that all the raw files have been added
    got_raws = set() # files added
    for r in pdc_metadata['raw_protein_mass_spectrometry']:
        got_raws.add(r['original_file_name'])
    all_raws = set() # files found in the PDC folder
    for date in files_dict:
        for name in files_dict[date]['RAW'].keys():
            all_raws.add(name)
    print(len(all_raws.difference(got_raws)))


if __name__== "__main__":

    # settings
    study_id = 'S039-1'
    folder_name = '_Proteome' # title of the file folders for this study

    import time; start = time.time()
    
    files_dict = {}
    try:
        with open(study_id+'/files_list', 'r') as f:
            files_dict = json.load(f)
    except:
        files_dict = get_all_files(study_id, folder_name)

    try:
        with open(study_id+'/study.json', 'r') as f:
            pdc_metadata['study'] = json.load(f)
        with open(study_id+'/program.json', 'r') as f:
            pdc_metadata['program'] = json.load(f)
        with open(study_id+'/project.json', 'r') as f:
            pdc_metadata['project'] = json.load(f)
    except:
        get_study_info(study_id)
        get_program_project()

    try:
        with open(study_id+'/raw_protein_mass_spectrometry.json', 'r') as f:
            pdc_metadata['raw_protein_mass_spectrometry'] = json.load(f)
        with open(study_id+'/proteomic_workflow.json', 'r') as f:
            pdc_metadata['proteomic_workflow'] = json.load(f)
        with open(study_id+'/psm_protein_mass_spectrometry.json', 'r') as f:
            pdc_metadata['psm_protein_mass_spectrometry'] = json.load(f)
        with open(study_id+'/mzml_protein_mass_spectrometry.json', 'r') as f:
            pdc_metadata['mzml_protein_mass_spectrometry'] = json.load(f)
    except:
        get_files_for_study(study_id)

    try:
        with open(study_id+'/protein_expression.json', 'r') as f:
            pdc_metadata['protein_expression'] = json.load(f)
    except:
        get_protein_expression_for_study(study_id)

    try:
        with open(study_id+'/subject.json', 'r') as f:
            pdc_metadata['subject'] = json.load(f)
        with open(study_id+'/sample.json', 'r') as f:
            pdc_metadata['sample'] = json.load(f)
        with open(study_id+'/demographic.json', 'r') as f:
            pdc_metadata['demographic'] = json.load(f)
        with open(study_id+'/diagnosis.json', 'r') as f:
            pdc_metadata['diagnosis'] = json.load(f)
    except:
        get_subjects_for_study(study_id)

    try:
        with open(study_id+'/protocol.json', 'r') as f:
            pdc_metadata['protocol'] = json.load(f)
    except:
        get_protocol_for_study(study_id)
    
    try:
        with open(study_id+'/study_run_metadata.json', 'r') as f:
            pdc_metadata['study_run_metadata'] = json.load(f)
    except:
        get_study_run_metadata(study_id)

    t = int((time.time() - start) / 60)
    print('done! in {} min'.format(t))

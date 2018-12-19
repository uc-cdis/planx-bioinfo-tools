# dbGap automation tool

ETL tool to automate dbGap data submission to Gen3 portal:
	
	Run dbgap_to_gen3.py to convert dbGap data to tsv files in the correct format for submission
	Then use the sheepdog API to submit files to Gen3 in the correct order

Usage

	usage: dbgap_to_gen3.py [-h] -d DICTIONARY -a API_URL -rf RAW_FILE -mf MAPPING_FILE
               -prog PROGRAM -proj PROJECT -auth AUTH_FILE [-o OUTPUT]
               [-s STUDY_ID]

	Submit data to Gen3 Commons from DbGap dictionary data

	optional arguments:
	  -h, --help            show this help message and exit
	  -d DICTIONARY, --dictionary DICTIONARY
	                        Data Dictionary being used in Gen3 Commons
	  -a API_URL, --api_url API_URL
	                        Api Url to submit data to
	  -rf RAW_FILE, --raw_file RAW_FILE
	                        Raw DbGap data file
	  -mf MAPPING_FILE, --mapping_file MAPPING_FILE
	                        Mapping file for DbGap data
	  -prog PROGRAM, --program PROGRAM
	                        program submitting to e.x. DEV
	  -proj PROJECT, --project PROJECT
	                        project sumittion to e.x. test
	  -auth AUTH_FILE, --auth_file AUTH_FILE
	                        Auth file for sheepdog submissions
	  -o OUTPUT, --output OUTPUT
	                        output path for sheepdog submission logs
	  -s STUDY_ID, --study_id STUDY_ID
	                        If there is a specific study id that you would like to
	                        append to the case nodes

Example submission

	python dbgap_to_gen3.py -d https://s3.amazonaws.com/dictionary-artifacts/gtexdictionary/3.0.11/schema.json -a https://mlukowski.planx-pla.net -rf data/GTEx_Subject.txt -mf data/mapped_subject_dictionary.txt -prog DEV -proj test -auth credentials.json -s 1234

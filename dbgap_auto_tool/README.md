# dbGap automation tool

ETL tool to automate dbGap data submission to Gen3 portal:

	1. Run dbgap_convert_dict.py to organize the original dictionary into the format for edition
		python dbgap_convert_dict.py --dictionary dictionary_file
	2. Manually edit the formatted dictionary excel file to select and map the variable into gen3 dictionary
	3. based on the editted mapping table, run dbgap_tsv _automation.py to generate submittable tsv file

		python dbgap_tsv _automation.py --file_raw dbGap_data --mapping_file file_map

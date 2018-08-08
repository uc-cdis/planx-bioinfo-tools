# planx-bioinfo-tools
Collection of helpful scripts for mapping, ETL, automation and others related to PlanX bioinformatics team. It includes tools for data model and data dictionary creation as well as data submission.
* ETL tool to automate dbGap data submission to gen3 portal
	1. Run dbgap_convert_dict.py to organize the original dictionary into the format for edition
		python dbgap_convert_dict.py --dictionary dictionary_file
	2. Manually edit the formatted dictionary excel file to select and map the variable into gen3 dictionary
	3. based on the editted mapping table, run dbgap_tsv _automation.py to generate submittable tsv file

		python dbgap_tsv _automation.py --file_raw dbGap_data --mapping_file file_map

# dictionary-creator

Python script to help creating new nodes in any data dictionary in YAML format. It requires the following arguments:
	`--variables` List of varibles and their characteristics in TSV format to add to the new dictionary nodes (see [a example here](variables_example.tsv))
	`--nodes` List of new nodes and their characteristics in TSV format (see [a example here](nodes_example.tsv))
	`--schema` YAML template to create dictionary nodes (see [a example here](yaml_template.yaml))

Usage example:

` python dict_creator.py --variables variables_example.tsv --nodes nodes_examples.tsv --schema yaml_template.yaml


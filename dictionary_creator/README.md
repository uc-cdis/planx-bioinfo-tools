# dictionary-creator

Python script to help creating new nodes in any data dictionary in YAML format. It requires the following arguments:

* `--variables` List of varibles and their characteristics in TSV format to add to the new dictionary nodes (see [a example here](variables_example.tsv))
* `--nodes` List of new nodes and their characteristics in TSV format (see [a example here](nodes_example.tsv))
* `--schema` YAML template to create dictionary nodes (see [a example here](yaml_template.yaml))
* `--link` YAML template to create multiple links in the schemas (see [a example here](link_template.yaml)) 
* `--separator` Indicates the separator used for enumerations in the variable list file. `","` by default.

Usage example:

```
python dict_creator.py --variables variables_example.tsv --nodes nodes_examples.tsv --schema yaml_template.yaml`
```

The list of variables is collected in a TSV with the following columns (headers):

* `Node`: Schema file (node/category) where the variable belongs.
* `Field`: Name for this variable.
* `Description`: Description provided for this variable in the dictionary.
* `Type`: Type of the variable. Typically, `integer`, `number`, `enum`, `string`.
* `Options`: If Type is `enum`, list of possible values for this variable. Both `|` or `","` separators can be used.
* `Required`: Yes/No depending on whether this variable will be required or not in the dictionary.
* `Term`: (OPTIONAL) Associated standard vocabulary term associated to this variable. E.g. CDISC term.

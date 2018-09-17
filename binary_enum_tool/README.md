`binary_dict.py` is a Python script which searches a given dictionary (set of schema YAML files) for enum properties which could possibly be converted to boolean values. For example, if a property has an enum list with only yes/no options, then perhaps we could convert this property to a boolean. The properties are flagged based on whether or not certain keywords (e.g., 'yes', 'no') appear in either the enum list or the property description. If the user would like to add or remove keywords to modify the search, then the `keywords` list in `config.yaml` can be modified as desired.

The folder structure is as follows:
* `code/` contains the script, as well as a configuration file config.yaml
* `dictionaries/` contains the target dictionaries for testing, for example it could contain `ndhdictionary/` (or any other dictionary), as cloned from git
* `reports/` contains report files detailing results of running the script for a particular dictionary. Each dictionary has its own designated folder of resulting tsv files. Additionally, the reports are broken down by node, so each node gets its own tsv file detailing which properties were flagged and why. The aggregate results for the whole dictionary can be viewed in the master report, named `_master_summary.tsv`

The command to execute the script takes one argument, `-d/--dictionary` which is the name of directory which corresponds to the target dictionary for testing. For example, if we want to test the `ndhdictionary`, then we would first move to the directory `dictionaries/`, clone `ndhdictionary` from git, then move to the `code/` directory and run the following command:

```
python binary_dict.py -d ndhdictionary
```

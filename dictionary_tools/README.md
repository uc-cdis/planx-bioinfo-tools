# Modify/Make Demo:

Get this repo.

1. `git clone git@github.com:uc-cdis/planx-bioinfo-tools.git`
2. `cd planx-bioinfo-tools/`

Switch to the appropriate branch.

3. `git checkout feat/auto_tools`

Move to the directory containing the `modify.py` and `make.py` modules.

4. `cd dictionary_tools/code/modify`

Run this command.

5. `python modify.py -p input/dictionaries/example_dictionary -i examples -n demo_namespace -o demo`

Notes on Usage:
- `-p/--path_to_schemas`: Required. Path to input schemas, relative to directory `dictionary_tools/`.
- `-i/--input_tsv`: Required. Name of directory containing target nodes and variables TSV files.
- `-n/--namespace`: Required. Desired namespace for the output dictionary - e.g., `niaid.bionimbus.org`.
- `-o/--out_dict_name`: Optional. Name of output dictionary.

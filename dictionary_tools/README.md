# modify/make demo

Get this repo.

1. `git clone git@github.com:uc-cdis/planx-bioinfo-tools.git`
2. `cd planx-bioinfo-tools/`

Checkout this branch.

3. `git checkout feat/auto_tools`

Move to the directory containing the `modify.py` and `make.py` modules.

4. `cd dictionary_tools/code/modify`

Run this command:

5. `python modify.py -p input/dictionaries/example_dictionary -i examples -n demo_namespace -o demo`

View modify results in `output/modify`

Notes on usage:
- `-p/--path_to_schemas`: Optional. Path to input schemas, relative to directory `dictionary_tools/`.
- `-i/--input_tsv`: Required. Name of directory containing target nodes and variables TSV files.
- `-n/--namespace`: Required. Desired namespace for the output dictionary - e.g., `niaid.bionimbus.org`.
- `-o/--out_dict_name`: Optional. Name of output dictionary.

# compare demo

After running the above demo, move to directory `code/compare` and run this command:

1. `python compare.py -a input/dictionaries/example_dictionary -b output/modify/demo -o demo`

View comparison results in `output/compare`

Notes on usage:
- `-a`: Required. Path to one set of dictionary files, relative to directory `dictionary_tools/`.
- `-b`: Required. Path to the other set of dictionary files, relative to directory `dictionary_tools/`.
- `-o`: Optional. Name of output summary JSON file.

# get_tsv demo

Move to directory `code/get_tsv` and run this command:

1. `python get_tsv.py -p input/dictionaries/example_dictionary -o demo`

View get_tsv results in `output/get_tsv`

Notes on usage:
- `-p/--path_to_schemas`: Required. Path to the target set of dictionary files, relative to directory `dictionary_tools/`.
- `-o/--out_dir_name`: Optional. Name of output directory.

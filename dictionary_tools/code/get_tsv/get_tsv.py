import json
import os
import yaml
import argparse
from collections import OrderedDict
from datetime import datetime
import pandas

'''Be sure to update the doc strings, so they are coherent and helpful.'''

def setup():
    '''Performs all setup necessary to run convert_dictionary().'''
    parse_options()
    create_output_path()
    create_master_out()

def parse_options():
    '''Obtain path_to_schemas and name of output directory.'''
    global args

    parser = argparse.ArgumentParser(description="Obtain path_to_schemas and name of output directory.")
    parser.add_argument("-p", "--path_to_schemas", dest="path_to_schemas", required=True, help="Path to input schemas, relative to directory dictionary_tools.")
    parser.add_argument("-o", "--out_dir_name", dest="out_dir_name", required=False, help="Name of output directory.")

    args = parser.parse_args()

    return args

def mkdir(directory):
    '''Create directory if it does not already exist.'''
    if not os.path.exists(directory):
        os.makedirs(directory)

def create_output_path():
    '''Create path to the output directory: dictionary_tools/output/get_tsv/<out_dir_name>'''
    global out_path

    if args.out_dir_name:
        out_dir_name = args.out_dir_name
    else:
        out_dir_name = datetime.strftime(datetime.now(), 'output_tsv_%m.%d_%H.%M')

    out_path = '../../output/get_tsv/' + out_dir_name + '/'

    mkdir(out_path)

def create_master_out():
    global master_out
    master_out = {'nodes': [], 'variables': []}

def get_input_dict():
    '''Returns a list containing all the filenames from the input dictionary.'''
    global path_to_schemas

    # path from args, relative to dictionary_tools/
    # e.g., input/dictionaries/gdcdictionary/gdcdictionary/schemas/
    path_to_schemas = '../../' + args.path_to_schemas

    if path_to_schemas[-1] != '/':
        path_to_schemas += '/'

    input_dict = os.listdir(path_to_schemas)

    return input_dict

def get_schema(schema_file):
    '''Load and return contents of schema_file as dictionary.'''
    path = path_to_schemas + schema_file
    # 'input/dictionaries/gdcdictionary/gdcdictionary/schemas/' + 'sample.yaml'

    schema_dict = yaml.load(open(path))

    return schema_dict

def get_headers():
    '''Could create a config file.. for now just loading here.'''
    nodes_head = ['<node>', '<node_action>', '<title>', '<category>', '<submittable>', '<description>', '<link_name>', '<backref>', '<label>', '<target>', '<multiplicity>', '<link_required>', '<link_group_required>', '<group_exclusive>']
    var_head = ['<node>', '<field_action>', '<field>', '<description>', '<type>', '<options_action>', '<options>', '<required>', '<term>']

    return nodes_head, var_head

def write_out():
    '''
    Eventually:
    out.to_csv(path_or_buf='test_out.tsv', sep='\t', index=False, columns=head)

    where 'out' is a pandas DataFrame isomorphic to the desired output tsv
    '''
    nodes_out = pandas.DataFrame(master_out['nodes'])
    variables_out = pandas.DataFrame(master_out['variables'])

    # out_path = '../../output/get_tsv/' + out_dir_name + '/'
    # presently only creating the master nodes and var's TSV files
    # can create the pairs for individual nodes l8r

    mkdir(out_path)

    nodes_path = out_path + 'nodes.tsv'
    variables_path = out_path + 'variables.tsv'

    nodes_head, var_head = get_headers()

    nodes_out.to_csv(path_or_buf=nodes_path, sep='\t', index=False, columns=nodes_head, encoding='utf-8')
    variables_out.to_csv(path_or_buf=variables_path, sep='\t', index=False, columns=var_head, encoding='utf-8')

# okay
def convert_dictionary():
    '''Creates a collection of nodes and variables TSV files corresponding to the input dictionary.'''
    schema_files = get_input_dict()

    # can put this elsewhere
    ignore_schemas = ['projects', 'README.md', '_definitions.yaml', '_settings.yaml', '_terms.yaml', '.DS_Store']

    for schema_file in sorted(schema_files):
        if schema_file not in ignore_schemas:
            convert_schema(schema_file)

# incomplete subroutines
def convert_schema(schema_file):
    schema = get_schema(schema_file)

    # 'sample', 'case', etc.
    node = schema['id']

    # put variables rows in master_out
    get_variables(node, schema) # okay

    # put nodes row in master_out
    get_nodes(node, schema) # okay

def list_to_str(lst):
    '''If lst is a list, converts lst to the appropriate string respresentation of this list used in the TSV files.
    Else lst is returned untouched.
    '''
    if type(lst) is list:
        lst = str(lst)[1:-1].replace('\'', '')

    return lst

def get_link_names(schema_dict):
    '''Return a list containing all the link names from the links section of the given schema dictionary.'''
    link_names = []

    try:
        links = schema_dict['links']
        for link in links:
            if 'subgroup' in link:
                group = link['subgroup']
                for item in group:
                    link_names.append(item['name'])
            else:
                link_names.append(link['name'])

    except KeyError:
        print('no links for - ' + schema_dict['id'])

    return link_names

# okay
def get_variables(node, schema):
    var_list = schema['properties']

    link_names = get_link_names(schema)
    req_vars = schema['required']

    for req_var in req_vars:
        if req_var not in var_list:
            handle_req_var(node, req_var)

    for var in sorted(var_list):
        if var not in link_names and var != '$ref':
            var_block = var_list[var]
            handle_var(node, var, var_block, req_vars)

def handle_req_var(node, req_var):
    row = {'<node>': node,
           '<field>': req_var,
           '<required>': 'True'
           }

    master_out['variables'].append(row)

# okay - see notes here
def handle_var(node, var, var_block, req_vars):
    '''Construct dictionary (row) corresponding to this variable.'''

    # note: some properties only have $ref listed, for the whole block
    # these get their type listed as 'enum' presently, which is incorrect

    # presently ignoring <field_action> and <options_action> since these will be blank columns
    row = {'<node>': node,
           '<field>': var,
           '<description>': var_block.get('description'),
           '<type>': var_block.get('type', 'enum'), # some property type entries are lists - see acknowledgement.yaml#/properties/submitter_id
           '<options>': list_to_str(var_block.get('enum')), # not sure if this will work - will probably have to convert list into string list
           '<required>': var in req_vars,
           '<term>': var_block.get('term', {'$ref': None})['$ref']
           }

    # remaining things to handle - probably <options>
    # maybe convert boolean <required> to yes/no? - hopefully not
    master_out['variables'].append(row)

# okay - see janky subroutine
def get_nodes(node, schema):
    '''Construct dictionary (row) corresponding to this schema and its link section.'''

    row = {'<node>': node,
           '<node_action>': 'add', # only using this default value for now, for the demo - can remove later
           '<title>': schema['title'],
           '<category>': schema['category'],
           '<submittable>': schema['submittable'],
           '<description>': schema['description']
           }

    row.update(handle_links(row, schema))

    master_out['nodes'].append(row)

# impressively janky, but should work
def handle_links(row, schema):
    '''Here we convert the links section from schema to spreadsheet format.'''
    try:
        links = schema['links']

    except KeyError:
        print('no links for - ' + schema_dict['id'])
        return {}

    out = {'<link_name>': [],
           '<backref>': [],
           '<label>': [],
           '<target>': [],
           '<multiplicity>': [],
           '<link_required>': [],
           '<link_group_required>': [],
           '<group_exclusive>': []}

    '''
    Notes
    Groups of properties:
    1. <backref>
    2. <link_group_required>, <group_exclusive>
    3. the rest

    Definitely encapsulate these bigger code blocks.
    Maybe create a lookup table for headers <-> yaml keys
    '''

    for link in links:
        if 'subgroup' in link:

            # 1
            if out['<backref>'] == []:
                out['<backref>'].append(link['subgroup'][0]['backref'])

            # 2
            out['<link_group_required>'].append(link['required'])
            out['<group_exclusive>'].append(link['exclusive'])

            # 3
            sub_out = {'<link_name>': [],
                   '<label>': [],
                   '<target>': [],
                   '<multiplicity>': [],
                   '<link_required>': []
                   }

            group = link['subgroup']

            for item in group:
                sub_out['<link_name>'].append(item['name'])
                sub_out['<label>'].append(item['label'])
                sub_out['<target>'].append(item['target_type'])
                sub_out['<multiplicity>'].append(item['multiplicity'])
                sub_out['<link_required>'].append(item['required'])

                # uh yeah fix this ^

            for key in sub_out:
                out[key].append(sub_out[key])

        else:
            # 1
            if out['<backref>'] == []:
                out['<backref>'].append(link['backref'])

            # 3 - notice identical block to above
            out['<link_name>'].append(link['name'])
            out['<label>'].append(link['label'])
            out['<target>'].append(link['target_type'])
            out['<multiplicity>'].append(link['multiplicity'])
            out['<link_required>'].append(link['required'])

    for key in out:
        out[key] = list_to_str(out[key])

    # print json.dumps(out, indent=2)

    return out

if __name__ == "__main__":

    setup()
    convert_dictionary()
    write_out() # should I put this in convert_dictionary()? what difference does it make

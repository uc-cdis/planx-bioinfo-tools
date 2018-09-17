import json
import os
import yaml
import argparse
from shutil import rmtree
from copy import deepcopy

config_doc = yaml.load(open('config.yaml'))

ignore_schemas = config_doc['ignore_schemas']

header = 'Node\tProperty\tType\tEnum_Values\tDescription\tFlags\n'

keywords = config_doc['keywords']

def parse_options():
    global args

    parser = argparse.ArgumentParser(description="Pass the name of dictionary you would like to test.")
    parser.add_argument("-d", "--dictionary", dest="dict", required=True, help="Name of directory corresponding to the dictionary to be tested.")

    args = parser.parse_args()

def setup():
    global prop_defs, term_defs, schemas_path, output_path, master_out_file

    parse_options()

    # example path: binary_enum_tool/dictionaries/ndhdictionary/gdcdictionary/schemas

    dict_name = args.dict # ndhdictionary

    if not os.path.exists('../reports'):
        os.mkdir('../reports')

    schemas_path = '../dictionaries/' + dict_name + '/gdcdictionary/schemas/'
    output_path = '../reports/' + dict_name + '_report_files/'

    prop_defs = yaml.load(open(schemas_path + '_definitions.yaml'))
    term_defs = yaml.load(open(schemas_path + '_terms.yaml'))

    if os.path.exists(output_path):
        rmtree(output_path)

    os.mkdir(output_path)

    master_out_file = open(output_path + '_master_summary.tsv', 'w')

    master_out_file.write(header)

def check_enum(prop_block, out_dict):

    if 'enum' in prop_block:
        out_dict['type'] = 'enum'
        enum_list = prop_block['enum']
        out_dict['enum_values'] = enum_list

        for val in enum_list:

            for word in keywords:
                if word in val.strip().lower():
                    out_dict['collect_me'] = True
                    out_dict['flags'].append(word)

            if val.strip().lower() in ['no']:
                out_dict['collect_me'] = True
                out_dict['flags'].append('no')

def check_boolean(prop_block, out_dict):

    try:
        if ('type' in prop_block) and (prop_block['type'].lower().strip() == 'boolean'):
            # out_dict['collect_me'] = True
            out_dict['type'] = 'boolean'
            out_dict['flags'].append('boolean')

    except:
        pass
        '''
        view_flag = True
        for term in ['type', 'id', 'data', 'year']:
            if term in prop.lower():
                view_flag = False

        if view_flag:
            print 'the property type is a list:'
            print prop
            print json.dumps(prop_block, indent=2)
        '''

def check_description(prop_block, out_dict):

    desc = ''

    if 'description' in prop_block:
        desc = prop_block['description']

    # _terms.yaml#/weight
    elif 'term' in prop_block:
        try:
            term_path = prop_block['term']['$ref'].split('/')
            term_name = term_path[1]
            term_entry = term_defs[term_name]
            desc = term_entry['description']
        except:
            print 'term issue: '
            print prop
            print json.dumps(prop_block, indent=2)

    # create general dereference function

    # $ref: "_definitions.yaml#/datetime"
    elif '$ref' in prop_block:
        '''
        print 'here is a reference in the the block'
        print prop
        print json.dumps(prop_block, indent=2)
        '''
        # wrap this into a function - dereference definition
        prop_path = prop_block['$ref'].split('/')
        prop_name = prop_path[1]
        prop_entry = prop_defs[prop_name]
        if 'description' in prop_entry:
            desc = prop_entry['description']
        elif 'term' in prop_entry:
            # encapsulate this bit into a function - dereference term
            term_path = prop_entry['term']['$ref'].split('/')
            term_name = term_path[1]
            term_entry = term_defs[term_name]
            desc = term_entry['description']

    else:
        pass
        '''
        view_flag = True
        for term in ['type', 'id']:
            if term in prop:
                view_flag = False

        if view_flag:
            print 'WARNING : No desc, term or $ref for prop - ' + prop
            print json.dumps(prop_block, indent=2)
        '''

    if desc is None and prop != 'type':
        print '\nWARNING : Could not find a desc for prop - ' + prop

    # words to indicate boolean type response
    for word in keywords:
        if word in desc.lower():
            out_dict['collect_me'] = True
            out_dict['flags'].append(word)

    out_dict['description'] = desc.strip().encode('utf-8')

def check_prop(node_name, node_props, prop, write_header):

    out_dict = deepcopy(config_doc['output'])

    out_dict['node'] = node_name
    out_dict['property'] = prop

    prop_block = node_props[prop]

    # if enum with yes/no options present
    check_enum(prop_block, out_dict)

    # note: presently not collecting boolean values, but we can choose to collect boolean values if we'd like to do so
    # if type is boolean
    # check_boolean(prop_block, out_dict)

    # if keywords appear in description - e.g., 'yes', 'no', 'ever', 'positive', 'negative'
    check_description(prop_block, out_dict)

    # by now we should have caught all the issues
    # collect them and write the output - make this as clear, easy to read, and useful information as possible
    write_out(out_dict, write_header)

def write_out(out_dict, write_header):

    if out_dict['collect_me'] and out_dict['type'] not in [None, 'boolean']:
        output = (out_dict['node'], out_dict['property'], out_dict['type'], out_dict['enum_values'], out_dict['description'], out_dict['flags'])
        master_out_file.write('%s\t%s\t%s\t%s\t%s\t%s\n' % output)

        with open(output_path + out_dict['node'] + '.tsv', 'a+') as out_file:
            if write_header:
                out_file.write(header)
                write_header = False
            out_file.write('%s\t%s\t%s\t%s\t%s\t%s\n' % output)

def check_schema(schema_file):

    node_name = schema_file[:-5]

    print '----- ' + node_name + ' -----'

    schema = yaml.load(open(schemas_path + schema_file))

    node_props = schema['properties']

    while '$ref' in node_props:
        prop_path = node_props.pop('$ref').split('/')

        try:
            # all referenced property lists are contained in
            # _definitions.yaml (i.e., ubiquitous_properties, data_file_properties)
            node_props.update(prop_defs[prop_path[1]])
        except:
            print('not in _defintions.yaml - see path:')
            print(prop_path)

    # now node_props contains all properties, with no $ref lists

    write_header = True

    for prop in node_props:

        check_prop(node_name, node_props, prop, write_header)


def run_test():

    setup()

    print '\nBeginning to search - ' + args.dict + ' -\n'

    schema_files = os.listdir(schemas_path)

    for schema_file in schema_files:

        if schema_file not in ignore_schemas:

            check_schema(schema_file)

    print '\nSuccessfully completed search through - ' + args.dict + ' -\n'

if __name__ == "__main__":

    run_test()

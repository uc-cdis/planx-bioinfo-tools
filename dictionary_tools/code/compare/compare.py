import json
import os
import yaml
import argparse
from collections import OrderedDict
from datetime import datetime

# not processing these files/folders
ignore_schemas = ['projects', 'README.md', '_definitions.yaml', '_settings.yaml', '_terms.yaml']

def csv_list(string):
    '''Takes a csv list given as a string and returns it as a list.'''
    return string.split(',')

def parse_options():
    '''Obtain paths to the two target dictionaries to compare.'''
    global args

    parser = argparse.ArgumentParser(description="Obtain paths to the two dictionaries to compare, where paths are relative to dictionary_tools.")
    parser.add_argument("-a", dest="dict_a", required=True, help="Path to one set of dictionary files, relative to dictionary_tools.")
    parser.add_argument("-b", dest="dict_b", required=True, help="Path to other set of dictionary files, relative to dictionary_tools.")
    parser.add_argument("-o", dest="out_name", required=False, help="Name of output summary JSON file.")

    # parser.add_argument("-n", "--nodes", dest="nodes", type=csv_list, help="Comma separated list of nodes to compare.")
    # the above feature is not yet supported in the script - but this is a simple extension

    args = parser.parse_args()

def mkdir(directory):
    '''Create input directory if it does not already exist.'''
    if not os.path.exists(directory):
        os.makedirs(directory)

def compare_list(la, lb):
    '''
    Return values:
    0 - lists differ in content (and so also in order)
    1 - lists have same content but different order
    2 - lists have same content and same order
    '''
    if la == lb:
        return 2

    elif sorted(la) == sorted(lb):
        return 1

    else:
        return 0

def sort_sets(a, b, _type):
    '''Given two dictionaries or directories, return a triplet (common_elts, unique_elts_a, unique_elts_b),
    where common_elts is the set of elements that appear in both entities (keys or files),
    unique_elts_a is the set of elements that appear only in a, and
    unique_elts_b is the set of elements that appear only in b.
    '''
    if _type is dict:
        elts_a = set(a.keys())
        elts_b = set(b.keys())

    elif _type == 'path':
        elts_a = set(os.listdir(a))
        elts_b = set(os.listdir(b))

    unique_elts_a = elts_a.difference(elts_b)
    unique_elts_b = elts_b.difference(elts_a)
    common_elts = set.intersection(elts_a, elts_b)

    return common_elts, unique_elts_a, unique_elts_b

def keys_analysis(da, db, parent_out):
    keys_a, keys_b = [set(d.keys()) for d in [da, db]]
    common_keys, unique_keys_a, unique_keys_b = sort_sets(da, db, dict)

    if len(set([len(k) for k in [keys_a, keys_b, common_keys]])) > 1:
        # eliminate repetition in code here, a and b blocks are symmetric
        if len(unique_keys_a) > 0:
            for key in sorted(unique_keys_a):
                parent_out.update({key: {'A': da[key], 'B': '<key_missing>'}})

        if len(unique_keys_b) > 0:
            for key in sorted(unique_keys_b):
                parent_out.update({key: {'A': '<key_missing>', 'B': db[key]}})

def compare_schema(schema_file):
    node = schema_file[:-5]

    schema_a = yaml.load(open(path_a + schema_file))
    schema_b = yaml.load(open(path_b + schema_file))

    master_out['comparison_results'][node] = {}

    keys_analysis(schema_a, schema_b, master_out['comparison_results'][node])

    common_keys = sorted(list(sort_sets(schema_a, schema_b, dict)[0]))

    common_keys.remove('properties')

    for key in common_keys + ['properties']:
        compare_val(key, schema_a, schema_b, 'yaml', master_out['comparison_results'][node])

def compare_val(key, da, db, level, parent_out):
    # maybe there's a way to modify this function so that it doesn't append empty comparisons..
    val_a = da[key]
    val_b = db[key]

    # only reporting lists which differ in content - not reported if same content but different order
    '''
    try:
        flag_1 = type(val_a) is list and compare_list(val_a, val_b) == 0
    except:
        print 'key: ' + key
        print 'val_a, val_b'
        print val_a, val_b
        raise Exception("Here's a problem")
    '''
    flag_1 = type(val_a) is list and compare_list(val_a, val_b) == 0
    flag_2 = type(val_a) is str and val_a.strip() != val_b.strip()
    flag_3 = type(val_a) not in [list, str] and val_a != val_b
    flag_4 = val_a is None and val_b is None

    if True in [flag_1, flag_2, flag_3] and not flag_4:
        if level == 'property':
            # master
            parent_out.update({key: {'A': val_a, 'B': val_b}})

        elif level == 'property_list':

            if key == '$ref':
                parent_out.update({key: {'A': val_a, 'B': val_b}})

            else:
                parent_out[key] = {}

                keys_analysis(val_a, val_b, parent_out[key])

                common_prop_keys = sort_sets(val_a, val_b, dict)[0]

                for prop_key in sorted(common_prop_keys):
                    compare_val(prop_key, val_a, val_b, 'property', parent_out[key])

        elif level == 'yaml':
            if key == 'properties':
                parent_out[key] = {}

                keys_analysis(da['properties'], db['properties'], parent_out[key])

                common_props = sort_sets(da['properties'], db['properties'], dict)[0]

                for prop in sorted(common_props):
                    compare_val(prop, da['properties'], db['properties'], 'property_list', parent_out[key])

            else:
                # master
                parent_out[key] = {'A': val_a, 'B': val_b}

def get_schema_paths():
    global path_a, path_b

    path_a = '../../' + args.dict_a
    if path_a[-1] != '/':
        path_a = path_a + '/'

    path_b = '../../' + args.dict_b
    if path_b[-1] != '/':
        path_b = path_b + '/'

    # master
    master_out['paths'] = {'A': path_a,
                           'B': path_b}

    # return path_a, path_b
    # not returning, since global names

# master
def create_master_out():
    global master_out
    # master
    master_out = {}

def file_breakdown():
    common_schemas, unique_a, unique_b = sort_sets(path_a, path_b, 'path')

    # master
    master_out['files'] = {'unique_to_A': sorted(unique_a),
                           'unique_to_B': sorted(unique_b),
                           'common': sorted(common_schemas)}

def compare_schemas():
    '''
    if args.nodes:
        common_schemas = sorted(args.nodes) # HERERE - right now only handling the case we work with filenames, not node names

        # master
        master_out['files'] = {'user_defined_node_list': common_schemas}

    else:
        file_breakdown()
    '''

    file_breakdown()

    common_schemas = sort_sets(path_a, path_b, 'path')[0]

    master_out['comparison_results'] = {}

    for schema_file in sorted(common_schemas):
        if schema_file not in ignore_schemas:
            compare_schema(schema_file)

def handle_master_out():
    # print json.dumps(master_out, indent=2, ensure_ascii=False)

    # recursively remove empty dictionaries
    clean_dict(master_out)

    out_path = '../../output/compare/'

    mkdir(out_path)

    if args.out_name:
        report_file_name = out_path + args.out_name + '.json'
    else:
        report_file_name = out_path + datetime.strftime(datetime.now(), 'results_%m.%d_%H.%M') + '.json'

    with open(report_file_name, 'w') as out_file:
        out_file.write(json.dumps(master_out, indent=2))

def clean_dict(d, parent=None, parent_key=None):
    '''Recursively remove empty dictionaries from a dictionary of nested dictionary.'''
    for key in d.keys():
        if d[key] == {}:
            d.pop(key)
        elif type(d[key]) is dict:
            clean_dict(d[key], d, key)
    if d == {}:
        parent.pop(parent_key)

if __name__ == "__main__":

    parse_options()
    create_master_out()
    get_schema_paths()
    compare_schemas()
    handle_master_out()

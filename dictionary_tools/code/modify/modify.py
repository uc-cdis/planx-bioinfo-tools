import json
import os
import yaml
import argparse
import make
from collections import OrderedDict
from shutil import copy as copy_file

# first function called in main script - before modify_dictionary()
def setup():
    '''Performs all the necessary preparation work so that we can run modify_dictionary().'''
    parse_options()
    create_output_path()
    load_make_config()
    get_all_changes_map()

# first function called in setup()
def parse_options():
    '''Obtain path_to_schemas, namespace value, name of directory containing target nodes and variables TSV files, and name of output dictionary.'''
    global args

    parser = argparse.ArgumentParser(description="Obtain path_to_schemas, namespace value, name of directory containing target nodes and variables TSV files, and name of output dictionary.")
    parser.add_argument("-p", "--path_to_schemas", dest="path_to_schemas", required=True, help="Path to input schemas, relative to directory dictionary_tools.")
    parser.add_argument("-n", "--namespace", dest="namespace", required=True, help="Desired namespace for this dictionary - e.g., niaid.bionimbus.org")
    parser.add_argument("-i", "--input_tsv", dest="input_tsv", required=True, help="Name of directory containing target nodes and variables TSV files.")
    parser.add_argument("-o", "--out_dict_name", dest="out_dict_name", required=False, help="Name of output dictionary.")

    args = parser.parse_args()

    return args

# second function called in setup()
def create_output_path():
    '''Create path to the output dictionary: dictionary_tools/output/modify/<out_dict_name>'''
    global out_path

    if args.out_dict_name:
        out_dict_name = args.out_dict_name
    else:
        out_dict_name = datetime.strftime(datetime.now(), 'out_dict_%m.%d_%H.%M')

    out_path = '../../output/modify/' + out_dict_name + '/'

    make.mkdir(out_path)

# third function called in setup()
def load_make_config():
    '''Load templates used for creating new nodes and constructing links section text-blocks.'''
    global content_template, link_template, group_template, link_props
    content_template, link_template, group_template, link_props = make.load_config()

# fourth function called in setup()
def get_all_changes_map():
    '''
    Aggregates information from nodes and variables input TSV sheets into one data structure.

    Result is a dictionary with node names (e.g., 'sample', 'case') as keys, and the values are dictionaries:

    {
    'action': 'add'/'update'/'delete',
    'link': [{<row>}],
    'variable': [{<row_1>}, {<row_2>}, ..., {<row_k>}]
    }

    Where 'link' maps to the list of rows corresponding to the node in the nodes.tsv file,
    and 'variable' maps to the list of rows corresponding to the node in the variables.tsv file.

    The dictionaries which correspond to rows in the TSV sheets have the headers from the sheet as keys,
    and the values are the row's values for that header/column.
    '''
    global all_changes_map

    nodes, variables = make.get_data(args.input_tsv)

    nodes_to_modify = set(list(nodes.keys()) + list(variables.keys()))

    all_changes_map = {}

    for node in nodes_to_modify:
        action = 'update' # action is always update, unless field <node_action> is specified as 'add' or 'delete' in nodes.tsv

        # determine if the node_action is add or delete
        if nodes.get(node):
            for node_action in ['add', 'delete']:
                if nodes[node][0]['<node_action>'] == node_action:
                    action = node_action

        all_changes_map[node] = {'action': action,
                                 'link': nodes.get(node),
                                 'variable': variables.get(node)}

    # return all_changes_map
    # not returning, since using it as a global name

# second function called in main script - after setup()
def modify_dictionary():
    '''Iterates through the node list and passes each node into the handle_node() processing pipeline.'''
    node_list = get_node_list() # this is a list of all the nodes we need to process

    for node in node_list:
        # node is 'sample', 'case', etc.
        handle_node(node)

# called in modify_dictionary()
def handle_node(node):
    '''Main pipeline for processing nodes.
    Each node is handled first on whether or not we need to process it at all,
    and then if we need to process it, if we are adding, updating, or deleting this node.
    The first check is made by seeing if the node appears in all_changes_map,
    and if it does, then we read the 'action' value associated with that node
    to determine what action to take: add/update/delete.

    If the node does not appear in all_changes_map, then we keep that schema
    with no changes except to populate the namespace with the value from args.
    '''
    print '\n~~~~~ ' + node + ' ~~~~~'

    if node in all_changes_map:

        if all_changes_map[node]['action'] == 'delete':
            print 'Removing node - ' + node + '\n'
            return None

        elif all_changes_map[node]['action'] == 'add':
            print 'Creating node - ' + node + '\n'
            make_schema(node)

        elif all_changes_map[node]['action'] == 'update':
            print 'Modifying node - ' + node + '\n'
            modify_schema(node)

        else: # for debugging purposes
            print '\nHey here is a problem: ' + all_changes_map[node]['action']

    else:
        print 'Keeping node - ' + node + '\n'
        keep_schema(node)

# called in handle_node()
def make_schema(node):
    '''This is a new node which needs to be created, so we refer to the make.py module,
    which contains the functionality from the old dict_creator.py script.
    We pass this node into the make.create_node_schema() pipeline which
    results in the creation of the YAML file for the new node.

    See the make.py module for details.
    '''
    make.create_node_schema(node, args, all_changes_map, out_path)

# called in handle_node()
def keep_schema(node):
    '''No changes are specified for this node, but we always update the namespace.
    Here we load the schema, make the namespace change, and then write the file.
    '''
    schema_text, schema_dict = get_schema(node)

    schema_text = modify_namespace(schema_text, schema_dict)

    write_file(schema_text, schema_dict)

# called in handle_node()
def modify_schema(node):
    '''Pipeline for the 'update' node action.
    Loads in existing schema as a string and a dictionary.
    Updates the namespace in schema_text,
    then updates the links in both the text and the dictionary,
    next updates the properties in the dictionary,
    and finally passes the fully updated (text, dictionary)
    pair to write_file() to create the new YAML file.
    '''
    schema_text, schema_dict = get_schema(node)

    schema_text = modify_namespace(schema_text, schema_dict)

    # if no changes, schema_text and schema_dict are returned untouched
    schema_text, schema_dict = modify_links(schema_text, schema_dict)

    # if no changes, schema_dict is returned untouched
    schema_dict = modify_properties(schema_dict)

    write_file(schema_text, schema_dict)

# called in keep_schema() and modify_schema()
def get_schema(node):
    '''Load and return contents of node YAML file, as a (string, dictionary) pair.'''
    path = path_to_schemas + node + '.yaml'
    # 'input/dictionaries/gdcdictionary/gdcdictionary/schemas/' + 'sample' + '.yaml'

    schema_text = open(path).read()
    schema_dict = yaml.load(open(path))

    return schema_text, schema_dict

# called in keep_schema() and modify_schema()
def modify_namespace(schema_text, schema_dict):
    '''Update namespace in schema_text.'''
    if 'namespace' in schema_dict:
        schema_text = schema_text.replace(schema_dict['namespace'], args.namespace)

    else: # no namespace listed!
        print '\nWARNING: No namespace listed in file - ' + schema_dict['id'] + '.yaml\n'

    return schema_text

# called in modify_schema()
def modify_properties(schema_dict):
    '''Takes the schema dictionary as input,
    makes all the property changes for the given node (to the property list and required list)
    as indicated in all_changes_map (which is the information from variables.tsv),
    and returns the appropriately modified schema dictionary.
    '''
    node = schema_dict['id']

    if all_changes_map[node]['variable']:
        print ' - Updating Property List -\n'
        for row in all_changes_map[node]['variable']:
            print '\t' + row['<field_action>'] + ' - ' + row['<field>'] + '\n'

            if row['<field_action>'] in ['add', 'update']:
                prop_entry = make.build_prop_entry(schema_dict, row)
                schema_dict['properties'][row['<field>']] = prop_entry

            elif row['<field_action>'] == 'delete':
                schema_dict['properties'].pop(row['<field>'])
                if row['<field>'] in schema_dict['required']:
                    schema_dict['required'].remove(row['<field>'])

            if row['<required>'].lower() == 'yes' and row['<field>'] not in schema_dict['required']:
                schema_dict['required'].append(row['<field>'])

            elif row['<required>'].lower() == 'no' and row['<field>'] in schema_dict['required']:
                schema_dict['required'].remove(row['<field>'])

    return schema_dict

# called in modify_schema()
def modify_links(schema_text, schema_dict):
    '''For the given node, reads the link update information in all_changes_map (if any),
    creates the new link section (as a text block) as specified in the nodes.tsv file,
    updates the schema dictionary with this new link section,
    replaces the old links section in the schema text with the new links section,
    puts the links in the property list in the schema dictionary,
    and finally returns the updated (text, dictionary) pair.
    '''
    node = schema_dict['id']

    # if there are changes to be made
    # None (False) if no changes, else it is a list containing a single row from nodes.tsv
    if all_changes_map[node]['link']:
        print ' - Updating Links -\n'

        # remove old links from property list and required list if there
        schema_dict = remove_old_links(schema_dict)

        # put new links in property list and required if specified as such
        schema_dict = put_links_in_prop_list(node, schema_dict)

        # create new links section text block
        updated_link_block = make.return_link_block(node, all_changes_map)

        # update the 'links' entry in schema_dict
        schema_dict['links'] = yaml.load(updated_link_block)

        # update 'links' block in schema_text
        prev_link_block = get_links_text(schema_text)
        schema_text = schema_text.replace(prev_link_block, updated_link_block)

    return schema_text, schema_dict

# called in modify_dictionary()
def get_node_list():
    '''Returns the list of all nodes that we need to consider:
    1) Nodes from the input dictionary, and
    2) Nodes listed in the input TSV sheets
    '''
    input_dict = set(get_input_dict()) # files from input dictionary

    ignore_files = set(['projects', 'README.md', '_definitions.yaml', '_settings.yaml', '_terms.yaml', '.DS_Store'])

    handle_ignore_files(ignore_files)

    # get just the node names, without file extensions
    input_nodes = [k[:-5] for k in input_dict.difference(ignore_files)]

    # pool these node names with those in the input_tsv sheets (in all_changes_map), remove duplicates, convert back to a list
    node_list = list(set(input_nodes + list(all_changes_map.keys())))

    return sorted(node_list)

# called in get_node_list()
def handle_ignore_files(ignore_files):
    '''Copies the ignore files (if they exist in the input dictionary) over from input dictionary to the output dictionary.'''
    for file_name in ignore_files:
        in_file = path_to_schemas + file_name

        # this filters out non-file entities, e.g., directories - see directory 'projects'
        if os.path.isfile(in_file):
            out_file = out_path + file_name
            copy_file(in_file, out_file)

# called in get_node_list()
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

# called in modify_links()
def get_links_text(schema_text):
    '''Returns the link section text from the yaml file. As in '<link>' in the config yaml_template.'''
    temp = schema_text.split('links:\n')
    temp = temp[1].split('\n\nuniqueKeys:')
    return temp[0]

# called in modify_links()
def remove_old_links(schema_dict):
    '''Remove old links from property list and required list if there.'''
    old_link_names = get_link_names(schema_dict)

    for old_link in old_link_names:
        schema_dict['properties'].pop(old_link)
        if old_link in schema_dict['required']:
            schema_dict['required'].remove(old_link)

    return schema_dict

# called in modify_links()
def put_links_in_prop_list(node, schema_dict):
    '''Updates the property list and required list of the given node
    with the new links as specified in all_changes_map (which is the information from nodes.tsv)'''
    link_map = make.build_link_map(node, all_changes_map)

    for i in range(len(link_map['<link_name>'])):
        if type(link_map['<link_name>'][i]) is str:
            schema_dict = make_link_property(link_map['<link_name>'][i], link_map['<multiplicity>'][i], schema_dict)

            if link_map['<link_required>'][i].lower() == 'true':
                schema_dict['required'].append(link_map['<link_name>'][i])

        else:
            link_group = link_map['<link_name>'][i]
            link_mult_group = link_map['<multiplicity>'][i]

            for k in range(len(link_group)):
                schema_dict = make_link_property(link_group[k], link_mult_group[k], schema_dict)

                if link_map['<link_required>'][i][k].lower() == 'true':
                    schema_dict['required'].append(link_group[k])

    return schema_dict

# called in put_links_in_prop_list()
def make_link_property(link_name, link_mult, schema_dict):
    '''Updates the schema_dict property list with an entry for the given link.'''
    if 'to_one' in link_mult:
        schema_dict['properties'][link_name] = {'$ref': "_definitions.yaml#/to_one"}
    else:
        schema_dict['properties'][link_name] = {'$ref': "_definitions.yaml#/to_many"}

    return schema_dict

# called in modify_links()
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

# called in modify_schema() and keep_schema
def write_file(schema_text, schema_dict):
    '''Pipeline for creating a YAML file from the given schema text and dictionary.'''
    node = schema_dict['id']

    with open(out_path + node + '.yaml', 'w') as out_file:
        schema_content = schema_text.split('\nrequired:')[0]

        # write everything through 'uniqueKeys' here
        out_file.write(schema_content)

        '''
        .
        .
        .

        links:
          - name: subjects
            backref: samples
            label: derived_from
            target_type: subject
            multiplicity: many_to_one
            required: TRUE

        uniqueKeys:
          - [id]
          - [project_id, submitter_id]


        ^ this much is written - start next with writing '\nrequired:\n'
        '''

        # here we write the list of required properties/links
        out_file.write('\nrequired:\n')
        for req in sorted(schema_dict['required']):
            out_file.write('  - %s\n' % req)

        # finally we write ordered property list
        out_file.write('\nproperties:\n')

        ordered_properties = OrderedDict(sorted(schema_dict['properties'].items(), key=lambda t: t[0]))

        if '$ref' in ordered_properties:
            ref_list = ordered_properties.popitem(last=False)[1]
            out_file.write('  $ref: "%s"\n' % ref_list)
        '''
        else:
            print 'No $ref property list!'
        '''

        link_names = get_link_names(schema_dict)
        links = []

        for pair in ordered_properties.items():
            if pair[0] in link_names:
                links.append(pair) # collect the links to write at the bottom of the list
            else:
                write_property(pair, out_file)

        # first we write all the properties, then lastly the links as properties
        for pair in links:
            write_property(pair, out_file)

# called in write_file()
def write_property(pair, out_file):
    '''Writes the property entry for the given property pair, where
    pair[0] is the property name, and
    pair[1] is the property entry in dictionary form.'''
    # clean up, break into smaller bits
    # pair[0] is the property name
    # pair[1] is the property block
    out_file.write('\n')
    out_file.write('  %s:\n' % pair[0].strip().encode("utf-8"))

    if '$ref' in pair[1]:
        out_file.write('    $ref: "%s"\n' % pair[1]['$ref'].strip().encode("utf-8"))
        pair[1].pop('$ref')

    # write systemAlias (for 'id' on, e.g., keyword.yaml)
    if 'systemAlias' in pair[1]:
        out_file.write('    systemAlias: %s\n' % pair[1]['systemAlias'].strip().encode("utf-8"))
        pair[1].pop('systemAlias')

    # write term
    if 'term' in pair[1]:
        out_file.write('    term:\n')
        out_file.write('      $ref: "%s"\n' % pair[1]['term']['$ref'].strip().encode("utf-8"))
        pair[1].pop('term')

    # write description
    if 'description' in pair[1]:
        if isinstance(pair[1]['description'], unicode):
            desc = pair[1]['description'].strip().encode("utf-8")
        else:
            desc = unicode(pair[1]['description'], 'utf-8').strip().encode("utf-8")
        desc = desc.replace('\n', '\n      ')
        out_file.write('    description: >\n')
        out_file.write('      %s\n' % desc)
        pair[1].pop('description')

    # see 'in_review' on project
    if 'default' in pair[1]:
        out_file.write('    default: %s\n' % pair[1]['default'])
        pair[1].pop('default')

    # write type
    # presently NOT handling the case where type is a list
    if 'type' in pair[1]:
        '''
        if type(pair[1]['type']) is list:
            print 'Type is a list, not a string - ' + pair[0]
        '''
        out_file.write('    type: %s\n' % pair[1]['type']) #.strip().encode("utf-8") if string, not on list
        pair[1].pop('type')

    for item in ['format', 'minimum', 'maximum']:
        if item in pair[1]:
            out_file.write('    %s: %s\n' % (item, pair[1][item]))
            pair[1].pop(item)

    # write enum
    if 'enum' in pair[1]:
        out_file.write('    enum:\n')
        for option in sorted(pair[1]['enum']):
            out_file.write('      - "%s"\n' % option.strip().encode("utf-8"))
        pair[1].pop('enum')

    if len(pair[1]) > 0:
        print 'WARNING: unaddressed items for this property!! - ' + pair[0]
        print json.dumps(pair[1], indent=2)

if __name__ == "__main__":

    setup()
    modify_dictionary()
    # call to COMPARE module

# This is a submodule to be imported by the main 'modify' script
# This module contains the (extended) functionality from the original dict_creator.py script
import yaml
import os
from pandas import read_table
from copy import deepcopy

class InputError(Exception):
    '''A class to represent input errors on the nodes.tsv and variables.tsv sheets.'''
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

        print '\n' + self.message + '\n'
        print json.dumps(self.expression, indent=2)
        print ''

# called in modify.create_output_path()
def mkdir(directory):
    '''Create directory if it does not already exist.'''
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_config():
    '''Load template data (as strings) for schema creation from the YAML template config files.'''
    # Read schema template
    with open('config/yaml_template.yaml', 'r') as schemaFile:
        content = schemaFile.read()

    # Read link template
    with open('config/link_template.yaml', 'r') as linkFile:
        link = linkFile.read()

    # Read link group template
    with open('config/group_template.yaml', 'r') as groupFile:
        link_group = groupFile.read()

    # Read headers
    headerFile = yaml.load(open('config/headers.yaml'))
    link_props = headerFile['link_properties']

    return content, link, link_group, link_props

def run_load_config():
    global content_template, link_template, group_template, link_props
    content_template, link_template, group_template, link_props = load_config()

# called in modify.get_all_changes_map()
def get_data(directory):
    '''Returns data from the target nodes.tsv and variables.tsv files as two separate dictionaries - one dictionary for each file.'''
    global nodes_file, var_file

    path = '../../input/input_tsv/' + directory + '/'

    nodes_file = path + 'nodes.tsv'
    var_file = path + 'variables.tsv'

    return load_tsv(nodes_file), load_tsv(var_file)

# called in get_data()
def load_tsv(filename):
    '''Reads the TSV file and returns the data in a dictionary format,
    where the keys are nodes and the values are lists of dictionaries,
    where each dictionary corresponds to a row for that node in the TSV.
    '''
    out = {}
    data_frame = read_table(filename, na_filter=False)
    temp_dict = data_frame.to_dict('records')

    for row in temp_dict:

        # suppressing this functionality at the moment
        # so we can list required variables
        # that do not appear in the property list
        # not exactly sure how to handle this case right now
        # this is a TEMPORARY solution

        # check_row(row, filename)

        node = row['<node>']
        if node in out:
            out[node].append(row)
        else:
            out[node] = [row]

    return out

# called in modify_properties()
def build_prop_entry(schema_dict, row):
    '''Creates and returns the new or updated property entry
    corresponding to the given row in the variables.tsv sheet.
    '''
    if row['<field_action>'] == 'update':
        entry = deepcopy(schema_dict['properties'][row['<field>']])

    elif row['<field_action>'] == 'add':
        entry = {}

    else:
        print 'Handle this unforeseen <field_action>! - ' + row['<field_action>'] + '\n'

    if row['<description>']:
        entry['description'] = row['<description>'].strip()
        entry.pop('term', None)

    elif row['<term>']:
        entry['term'] = {'$ref': row['<term>']}
        entry.pop('description', None)

    if row['<type>']:
        if row['<type>'] != 'enum':
            entry['type'] = row['<type>']
            entry.pop('enum', None)
        elif row['<type>'] == 'enum' and row['<field_action>'] != 'update':
            entry['enum'] = parse_entry(row['<options>'])
            entry.pop('type', None)

    if row['<field_action>'] == 'update' and row['<options>'] != '':
        # 'add' is the default <options_action>
        if row['<options_action>'] in ['', 'add'] and not row['<type>']:
            entry['enum'].extend(parse_entry(row['<options>']))

        elif row['<options_action>'] == 'delete':
            del_list = parse_entry(row['<options>'])
            for val in del_list:
                entry['enum'].remove(val)

        elif row['<options_action>'] == 'replace' or row['<type>'] == 'enum':
            entry['enum'] = parse_entry(row['<options>'])
            entry.pop('type', None)

    return entry

# called in load_tsv()
def check_row(row, filename):
    '''Function for inspecting rows in a TSV to check for errors - blank entries or entries which do not correctly correspond.'''
    # can be cleaned up

    # check nodes.tsv rows
    if filename == nodes_file:

        for field in ['<node>', '<node_action>']:
            if not row[field]:
                raise InputError(row, 'ERROR: Blank field - ' + field)

        if row['<node_action>'] in ['add', 'update']:

            if row['<node_action>'] == 'add':
                for field in ['<title>', '<category>', '<description>']:
                    if not row[field]:
                        raise InputError(row, 'ERROR: Blank field - ' + field)

            # check for any blank fields
            for field in ['<link_name>', '<backref>', '<label>', '<target>', '<multiplicity>', '<link_required>']:
                if not row[field]:
                    raise InputError(row, 'ERROR: Blank field - ' + field)

            parsed_row = row.copy()

            lengths = set()
            group_lengths = set()

            # check correctly corresponding entries in general, for number of entries in each cell
            prev_field = ''
            for field in link_props:
                parsed_row[field] = parse_entry(str(parsed_row[field]), field)

                if field not in ['<link_group_required>', '<group_exclusive>', '<backref>']:
                    lengths.add(len(parsed_row[field]))
                    if len(lengths) > 1:
                        raise InputError(row, 'ERROR: Field - ' + field + ' - does not correspond with field - ' + prev_field)

                elif field in ['<link_group_required>', '<group_exclusive>']:
                    group_lengths.add(len(parsed_row[field]))
                    if len(group_lengths) > 1:
                        raise InputError(row, 'ERROR: Field - ' + field + ' - does not correspond with field - ' + prev_field)

                if field != '<backref>':
                    prev_field = field

            # check correctly corresponding entries for groups
            length = lengths.pop()

            n_groups = 0

            for i in range(length):
                if type(parsed_row['<link_name>'][i]) is list:
                    n_groups += 1
                    prev_field = ''
                    for field in link_props:
                        if field not in ['<link_group_required>', '<group_exclusive>','<backref>']:
                            if type(parsed_row[field][i]) is not list:
                                raise InputError(row, 'ERROR: Field - ' + field + ' - does not correspond with field - ' + prev_field)

                            lengths.add(len(parsed_row[field][i]))
                            if len(lengths) > 1:
                                raise InputError(row, 'ERROR: Field - ' + field + ' - does not correspond with field - ' + prev_field)
                            prev_field = field

            for field in ['<link_group_required>', '<group_exclusive>']:
                if len(parsed_row[field]) != n_groups:
                    raise InputError(row, 'ERROR: Link group field - ' + field + ' - does not correspond with the number of link groups designated in other fields.')

    # check variables.tsv rows
    elif filename == var_file:

        # for add/update/delete, <field> and <node> must always be specified
        for prop in ['<field>', '<node>']:
            if row[prop] == '':
                raise InputError(row, 'ERROR: Blank field - ' + prop)

        if row['<field_action>'] in ['', 'add']:
            # check for any blank fields
            for prop in ['<type>', '<required>']:
                if row[prop] == '':
                    raise InputError(row, 'ERROR: Blank field - ' + prop)

            # check if type enum then options field populated
            if row['<type>'] == 'enum' and row['<options>'] == '':
                raise InputError(row, 'ERROR: Type enum requires - <options> - field to be populated')

            # in the end, each property must have a term or (exclusive) description given
            # it is not an error, but it is a warning, when there is no term or description given
            if row['<description>'] == '' and row['<term>'] == '':
                print 'WARNING: No description or term $ref given for field - ' + row['<field>']

        elif row['<field_action>'] == 'update':
            if set([row['<description>'], row['<type>'], row['<options_action>'], row['<options>'], row['<required>'], row['<term>']]) == set(['']):
                raise InputError(row, 'ERROR: Field <field_action> is - update - but all other fields are blank')

            # <options> populated and <options_action> blank implies 'add' in <options_action>

            if row['<options_action>'] in ['add', 'delete', 'replace'] and row['<options>'] == '':
                raise InputError(row, 'ERROR: Field <options_action> is populated but field <options> is blank')

def create_node_schema(node, args, all_changes_map, out_path):
    '''Creates a dictionary YAML file for input node.'''
    # node is 'sample', 'case', etc.
    content = content_template # good

    # Populate namespace
    content = content.replace('<namespace>', args.namespace)

    # Get links
    link_block = return_link_block(node, all_changes_map)

    # Add links to schema template
    content = content.replace('<link>', link_block)

    # Fill node fields in schema
    # e.g., title, category, description
    for node_field in all_changes_map[node]['link'][0]:
        if node_field not in link_props and node_field != '<submittable>': # make this cleaner, revise this later, after demo
            content = content.replace(node_field, all_changes_map[node]['link'][0][node_field].strip())

    # a quick patch for demo to work - revise and clean later
    # if field specified, take that value - else, default is true
    if str(all_changes_map[node]['link'][0]['<submittable>']):
        submittable = str(all_changes_map[node]['link'][0]['<submittable>']).lower().strip()
    else:
        submittable = 'true'

    content = content.replace('<submittable>', submittable)

    if '_file' in all_changes_map[node]['link'][0]['<category>'].lower().strip():
        dfprops = '- file_state\n  - error_type\n'
        content = content.replace('<data_file_properties>', dfprops)
    else:
        content = content.replace('<data_file_properties>', '')

    # Write output
    write_new_schema(node, content, all_changes_map, out_path)

def build_link_map(node, all_changes_map):
    '''Return a dictionary containing link data for input node.'''

    link_map = {}

    for i in range(len(link_props)):
        prop = link_props[i]
        input_str = str(all_changes_map[node]['link'][0][prop])
        if len(input_str) > 0:
            link_map[prop] = parse_entry(input_str, prop)

    return link_map

def parse_entry(input_str, field=None):
    '''Function for parsing entries in the TSV files, taking a string input and returning a list.'''
    # currently only making lower case the fields which are boolean
    # can modify to adjust capitalization for other fields as well

    if field in ['<link_group_required>', '<group_exclusive>', '<link_required>']:
        input_str = input_str.lower()

    if '[' not in input_str:
        out = input_str.split(',')
        out = [k.strip() for k in out if k.strip() != '']
        return out

    out = []

    temp = input_str.split('[')

    for part in temp:

        if ']' in part:
            group_temp = part.split(']')
            group = group_temp[0]
            entry = group.split(',')

            out_entry = [k.strip() for k in entry if k.strip() != '']

            out.append(out_entry)

            non_group = group_temp[1]

        else:
            non_group = part

        non_group = non_group.strip(',')
        non_groups = non_group.split(',')

        for one_piece in non_groups:
            if len(one_piece.strip()) > 0:
                out.append(one_piece.strip())

    return out

def return_link_block(node, all_changes_map):
    '''Return the populated links section (as a string) for input node.'''
    link_map = build_link_map(node, all_changes_map)

    blocks = []

    group_counter = 0

    for map_place in range(len(link_map['<link_name>'])):

        if type(link_map['<link_name>'][map_place]) is str:
            out_block = build_link(link_map, map_place)

        elif type(link_map['<link_name>'][map_place]) is list:
            out_block = build_link_group(link_map, map_place, group_counter)
            group_counter += 1

        blocks.append(out_block.strip('\n'))

    blocks.sort(key = lambda b: len(b), reverse=True)

    link_block = '\n'.join(blocks)

    return link_block

def build_link_group(link_map, map_place, group_counter):
    '''Return a populated link group block (as a string).'''
    link_group = link_map['<link_name>'][map_place]

    out_block = group_template

    for group_prop in ['<group_exclusive>', '<link_group_required>']:
        group_prop_val = link_map[group_prop][group_counter]
        out_block = out_block.replace(group_prop, group_prop_val)

    group_blocks = []

    for k in range(len(link_group)):
        sub_block = build_link(link_map, map_place, True, k)
        group_blocks.append(sub_block)

    group_block = ''.join(group_blocks)

    out_block = out_block.replace('<subgroup>', group_block)

    return out_block

def build_link(link_map, map_place, link_group=False, group_place=None):
    '''Return a populated single link block (as a string).'''
    out = link_template

    if link_group:
        out = out.strip('\n')
        old_lines = out.split('\n')
        new_lines = []
        for line in old_lines:
            new_line = '    ' + line + '\n'
            new_lines.append(new_line)
        out = ''.join(new_lines)

    for link_prop in link_props:
        if link_prop not in ['<link_group_required>', '<group_exclusive>','<backref>']:

            if link_group:
                link_prop_val = link_map[link_prop][map_place][group_place]

            else:
                link_prop_val = link_map[link_prop][map_place]

            out = out.replace(link_prop, link_prop_val)

    out = out.replace('<backref>', link_map['<backref>'][0])

    return out

# as of now, acting on the notion that 'type' and 'submitter_id' are required on every node
# (except maybe 'project' and 'program'? - these are never going to get 'created' by this program though, I don't think)
def get_required_list(node, all_changes_map):
    req = ['type', 'submitter_id']

    link_map = build_link_map(node, all_changes_map)

    for i in range(len(link_map['<link_name>'])):
        if type(link_map['<link_name>'][i]) is str:
            link_name = link_map['<link_name>'][i]
            link_req = link_map['<link_required>'][i]

            if link_req.lower() == 'true':
                req.append(link_name)

        else:
            link_group = link_map['<link_name>'][i]
            link_req_group = link_map['<link_required>'][i]

            for k in range(len(link_group)):
                link_name = link_group[k]
                if link_req_group[k].lower() == 'true':
                    req.append(link_name)

    for row in all_changes_map[node]['variable']:
        if str(row['<required>']).lower().strip() == 'true':
            req.append(row['<field>'])

    return sorted(list(set(req))) # in case there are duplicates (i.e., type or submitter_id)

# this can definitely be cleaned up a bit
# encapsulate sections/blocks into functions
def write_new_schema(node, content, all_changes_map, out_path):
    '''Write the output dictionary YAML file.'''

    out_file = out_path + node + '.yaml'

    with open(out_file, 'w') as output:

        # encapsulate this bit into a function
        if '_file' in all_changes_map[node]['link'][0]['<category>'].lower().strip():
            ref_props = '_definitions.yaml#/data_file_properties'

        elif all_changes_map[node]['link'][0]['<category>'].lower().strip() == 'analysis':
            ref_props = '_definitions.yaml#/workflow_properties'

        else:
            ref_props = '_definitions.yaml#/ubiquitous_properties'

        output.write(content)

        # Write requirements in schema
        # requirements are sorted alphabetically - should this be changed?
        req = get_required_list(node, all_changes_map)

        for val in req:
            output.write('  - %s\n' % val)

        # Write variables in schema
        output.write('\n')
        output.write('properties:\n')



        output.write('  $ref: "%s"\n' % ref_props)

        for row in all_changes_map[node]['variable']:
            # make this a better condition - basically if there is any content in the row besides required
            if row['<description>'] or row['<term>'] or row['<type>'] or row['<options>']:


                output.write('\n')
                output.write('  %s:\n' % row['<field>'])

                # Add description if given
                if row['<description>']:
                    output.write('    description: >\n')
                    output.write('      %s\n' % row['<description>'].strip())

                # Else, add term ref if given
                elif row['<term>'] != '':
                    output.write('    term:\n')
                    output.write('      $ref: "%s"\n' % row['<term>'])

                # Add type
                if row['<type>'] == 'enum':
                    output.write('    enum:\n')
                    for option in sorted(parse_entry(row['<options>'])):
                        output.write('      - "%s"\n' % option)

                else:
                    # I don't really like having to handle this case
                    # why are some (very few!) types lists, with one option as null?
                    if ',' in row['<type>']:
                        temp = row['<type>'][1:-1].replace('\'', '')
                        type_list = parse_entry(temp)
                        output.write('    type:\n')
                        for option in type_list:
                            output.write('      - "%s"\n' % str(option))
                    else:
                        output.write('    type: %s\n' % row['<type>'])

        link_map = build_link_map(node, all_changes_map)

        for i in range(len(link_map['<link_name>'])):
            if type(link_map['<link_name>'][i]) is str:
                link_name = link_map['<link_name>'][i]
                link_mult = link_map['<multiplicity>'][i]
                output.write('\n')
                output.write('  %s:\n' % link_name)
                if 'to_one' in link_mult:
                    output.write('    $ref: "_definitions.yaml#/to_one"\n')
                else:
                    output.write('    $ref: "_definitions.yaml#/to_many"\n')

            else:
                link_group = link_map['<link_name>'][i]
                link_mult_group = link_map['<multiplicity>'][i]

                for k in range(len(link_group)):
                    link_name = link_group[k]
                    link_mult = link_mult_group[k]
                    # a lot of repetition here - encapsulate these bits into functions
                    output.write('\n')
                    output.write('  %s:\n' % link_name)
                    if 'to_one' in link_mult:
                        output.write('    $ref: "_definitions.yaml#/to_one"\n')
                    else:
                        output.write('    $ref: "_definitions.yaml#/to_many"\n')

# so the templates and everything are floating in this namespace
run_load_config()

import argparse
import json
import os
from pandas import read_table

# make this cleaner, or create another config file and put these things there
all_link_props = ['<link_name>', '<backref>', '<label>', '<target>', '<multiplicity>', '<link_required>', '<link_group_required>', '<group_exclusive>']
single_link_props = ['<link_name>', '<label>', '<target>', '<multiplicity>', '<link_required>']
req_var_fields = ['<field>', '<type>', '<node>', '<required>', '<description>']
req_link_fields = ['<node>', '<title>', '<category>', '<description>'] + all_link_props

def parse_options():
    '''Obtain the name of the directory containing the target nodes.tsv and variables.tsv files - store this directory name in args.dir'''
    global args

    parser = argparse.ArgumentParser(description="Introduce variables and nodes files to generate dictionary schemas")
    parser.add_argument("-d", "--directory", dest="dir", required=True, help="Directory containing target nodes.tsv and variables.tsv files")
    parser.add_argument("-n", "--namespace", dest="namespace", required=True, help="Namespace for this dictionary - e.g., niaid.bionimbus.org")

    args = parser.parse_args()

def create_schemas():
    '''Generates dictionary YAML files from nodes.tsv and variables.tsv contained in target directory.'''
    global content_template, link_template, group_template, nodes, variables

    mkdir('../output_yaml')

    mkdir('../output_yaml/' + args.dir + '_dict')

    nodes, variables = get_data(args.dir)

    content_template, link_template, group_template = get_templates()

    for node in nodes:

        create_node_schema(node)

def mkdir(directory):
    '''Create input directory if it does not already exist.'''
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_data(directory):
    '''Returns data from the target nodes.tsv and variables.tsv files as two separate dictionaries - one dictionary for each file.'''
    global nodes_file, var_file

    path = '../input_tsv/' + directory + '/'
    nodes_file = path + 'nodes.tsv'
    var_file = path + 'variables.tsv'

    return load_tsv(nodes_file), load_tsv(var_file)

def get_templates():
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

    return content, link, link_group

def create_node_schema(node):
    '''Creates a dictionary YAML file for input node.'''
    content = content_template

    # Populate namespace
    content = content.replace('<namespace>', args.namespace)

    # Get links
    link_block = return_link_block(node)

    # Add links to schema template
    content = content.replace('<link>', link_block)

    # Fill node properties in schema
    for prop in nodes[node][0]:
        if prop not in all_link_props:
            content = content.replace(prop, nodes[node][0][prop])

    # Write output
    write_file(node, content)

def load_tsv(filename):
    '''Reads the TSV file and returns the data in a dictionary format,
    where the keys are nodes and the values are lists of dictionaries,
    where each dictionary corresponds to a row for that node in the TSV.
    '''
    out = {}
    data_frame = read_table(filename, na_filter=False)
    temp_dict = data_frame.to_dict('records')

    for row in temp_dict:

        check_row(row, filename)

        node = row['<node>']
        if node in out:
            out[node].append(row)
        else:
            out[node] = [row]

    return out

def check_row(row, filename):
    '''Function for inspecting rows in a TSV to check for errors - blank entries or entries which do not correctly correspond.'''
    # can be cleaned up
    # lots of repetition - write a few functions, and/or take advantage of list comprehension
    if filename == nodes_file:

        # check for any blank fields
        for field in req_link_fields:
            if field not in ['<link_group_required>', '<group_exclusive>', '<backref>'] and row[field] == '':
                raise InputError(row, 'ERROR: Blank field - ' + field)

        # use build_link_map() here - already wrote this function!
        parsed_row = row.copy()

        lengths = set()
        group_lengths = set()

        # check correctly corresponding entries in general, for number of entries in each cell
        prev_field = ''
        for field in all_link_props:
            parsed_row[field] = parse_entry(parsed_row[field], field)

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
                for field in all_link_props:
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

        # check for any blank fields
        for field in req_var_fields:
            if row[field] == '':
                raise InputError(row, 'ERROR: Blank field - ' + field)

        # check if type enum then options field populated
        if row['<type>'] == 'enum' and row['<options>'] == '':
            raise InputError(row, 'ERROR: Type enum requires - <options> - field to be populated')

def parse_entry(input_str, field):
    '''Function for parsing entries in the TSV files, taking a string input and returning a list.'''
    # currently only making lower case the fields which are boolean
    # can modify to adjust capitalization for other fields as well

    if field in ['<link_group_required>', '<group_exclusive>', '<link_required>']:
        input_str = input_str.lower()

    if '[' not in input_str:
        out = input_str.split(',')
        out = [k for k in out if k != '']
        return out

    out = []

    temp = input_str.split('[')

    for part in temp:

        if ']' in part:
            group_temp = part.split(']')
            group = group_temp[0]
            entry = group.split(',')

            # remove empty strings in order to enable error checking later on in check_row()
            out_entry = [k for k in entry if k != '']

            out.append(out_entry)

            non_group = group_temp[1]

        else:
            non_group = part

        non_group = non_group.strip(',')
        non_groups = non_group.split(',')

        for one_piece in non_groups:
            if len(one_piece) > 0:
                out.append(one_piece)

    return out

class InputError(Exception):
    '''A class to represent input errors on the nodes.tsv and variables.tsv sheets.'''
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

        print '\n' + self.message + '\n'
        print json.dumps(self.expression, indent=2)
        print ''

def build_link_map(node):
    '''Return a dictionary containing link data for input node.'''

    link_map = {}

    for i in range(len(all_link_props)):
        prop = all_link_props[i]
        input_str = nodes[node][0][prop]
        if len(input_str) > 0:
            link_map[prop] = parse_entry(input_str, prop)

    return link_map

def return_link_block(node):
    '''Return the populated links section (as a string) for input node.'''
    link_map = build_link_map(node)

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

    for link_prop in single_link_props:

        if link_group:
            link_prop_val = link_map[link_prop][map_place][group_place]

        else:
            link_prop_val = link_map[link_prop][map_place]

        out = out.replace(link_prop, link_prop_val)

    out = out.replace('<backref>', link_map['<backref>'][0])

    return out

def write_file(node, content):
    '''Write the output dictionary YAML file.'''
    # encapsulate a lot of these writing segments into functions
    global nodes, variables, args

    out_file = '../output_yaml/' + args.dir + '_dict/' + node + '.yaml'

    with open(out_file, 'w') as output:
        output.write(content)

        # Write requirements in schema
        link_map = build_link_map(node)

        for i in range(len(link_map['<link_name>'])):
            if type(link_map['<link_name>'][i]) is str:
                link_name = link_map['<link_name>'][i]
                link_req = link_map['<link_required>'][i]

                if link_req.lower() == 'true':
                    output.write('  - %s\n' % link_name)

            else:
                link_group = link_map['<link_name>'][i]
                link_req_group = link_map['<link_required>'][i]

                for k in range(len(link_group)):
                    link_name = link_group[k]
                    if link_req_group[k].lower() == 'true':
                        output.write('  - %s\n' % link_name)

        for v in variables[node]:
            if v['<required>'].lower() == 'yes':
                output.write('  - %s\n' % v['<field>'])

        # Write variables in schema
        output.write('\n')
        output.write('properties:\n')
        output.write('  $ref: "_definitions.yaml#/ubiquitous_properties"\n')

        for v in variables[node]:

            # Add description
            output.write('\n')
            output.write('  %s:\n' % v['<field>'])
            output.write('    description: >\n')
            output.write('      %s\n' % v['<description>'])

            # Add type
            if v['<type>'] == 'enum':        # MUST determine a standard, cleaner notation for indicating option lists in the TSV
                output.write('    enum:\n')
                temp = v['<options>'].split('"')
                options = []
                for term in temp:
                    option = term.strip(',')
                    option = option.strip()
                    if option != '':
                        output.write('      - "%s"\n' % option)

            else:
                output.write('    type: %s\n' % v['<type>'])

            # Add ontology term if existing
            if v['<term>'] != '':
                output.write('    term:\n')
                output.write('       termDef:\n')
                output.write('          cde_id: %s\n' % v['<term>'])

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

if __name__ == "__main__":

    parse_options()
    create_schemas()

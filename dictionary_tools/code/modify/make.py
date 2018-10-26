import yaml
# this is a submodule to be called and referred to by the main 'modify' script

# previous main function in dict_creator.py
# not being used now, but preserved for reference
def create_schemas():
    '''Generates dictionary YAML files from nodes.tsv and variables.tsv contained in target directory.'''
    global content_template, link_template, group_template, req_link_fields, req_var_fields, link_props, nodes, variables

    mkdir('../../output/make')

    mkdir('../../output/make/' + args.dir + '_out')

    content_template, link_template, group_template, req_link_fields, req_var_fields, link_props = load_config()

    # nodes is all_changes_map[node]['link']
    # variables is all_changes_map[node]['variable']
    nodes, variables = get_data(args.dir)

    for node in nodes:
        # a node is 'sample', 'case', etc.
        create_node_schema(node) # covered

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
    req_link_fields = headerFile['req_link_fields']
    req_var_fields = headerFile['req_var_fields']
    link_props = req_link_fields[4:]

    return content, link, link_group, req_link_fields, req_var_fields, link_props

def run_load_config():
    global content_template, link_template, group_template, req_link_fields, req_var_fields, link_props
    content_template, link_template, group_template, req_link_fields, req_var_fields, link_props = load_config()

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
        if node_field not in link_props:
            content = content.replace(node_field, all_changes_map[node]['link'][0][node_field])

    # Write output
    write_file(node, content, all_changes_map, out_path)

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
        if row['<required>'].lower() == 'yes':
            req.append(row['<field>'])

    return sorted(req)

# this can definitely be cleaned up a bit
def write_file(node, content, all_changes_map, out_path):
    '''Write the output dictionary YAML file.'''

    out_file = out_path + node + '.yaml'

    with open(out_file, 'w') as output:
        output.write(content)

        # Write requirements in schema
        # requirements are sorted alphabetically - should this be changed?
        req = get_required_list(node, all_changes_map)

        for val in req:
            output.write('  - %s\n' % val)

        # Write variables in schema
        output.write('\n')
        output.write('properties:\n')
        # maybe revise this next line
        # not every node has ubiquitous_properties (? - ask)
        output.write('  $ref: "_definitions.yaml#/ubiquitous_properties"\n')

        for row in all_changes_map[node]['variable']:

            # Add description
            output.write('\n')
            output.write('  %s:\n' % row['<field>'])
            output.write('    description: >\n')
            output.write('      %s\n' % row['<description>'])

            # Add type
            if row['<type>'] == 'enum':
                output.write('    enum:\n')
                for option in sorted(parse_entry(row['<options>'])):
                    output.write('      - "%s"\n' % option)

            else:
                output.write('    type: %s\n' % row['<type>'])

            # Add ontology term if existing
            if row['<term>'] != '':
                output.write('    term:\n')
                output.write('       termDef:\n')
                output.write('          cde_id: %s\n' % row['<term>'])

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

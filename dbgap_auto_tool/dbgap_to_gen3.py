import os
import argparse

from dictionaryutils import DataDictionary, dictionary
from dbgap_to_tsv import parse_mapping, assign_values, write_tables
from datasimulator import graph
from submitter import submit

def initalize_dictionary(url):
	dictionary.init(DataDictionary(url=url))

def initalize_graph(dictionary, program, project):
	built_graph = graph.Graph(dictionary, program, project)
	built_graph.generate_nodes_from_dictionary()
	built_graph.construct_graph_edges()
	return built_graph

def parse_arguments():
	parser = argparse.ArgumentParser(description="Submit data to Gen3 Commons from DbGap dictionary data")
	parser.add_argument('-d', '--dictionary', required=True, help="Data Dictionary being used in Gen3 Commons")
	parser.add_argument('-a', '--api_url', required=True, help="Api Url to submit data to")
	parser.add_argument('-rf', '--raw_file', required=True, help="Raw DbGap data file")
	parser.add_argument('-mf', '--mapping_file', required=True, help="Mapping file for DbGap data")
	parser.add_argument('-prog', '--program', required=True, help="program submitting to e.x. DEV")
	parser.add_argument('-proj', '--project', required=True, help="project sumittion to e.x. test")
	parser.add_argument('-auth', '--auth_file', required=True, help="Auth file for sheepdog submissions")
	parser.add_argument('-o', '--output', default="./output/", help="output path for sheepdog submission logs")
	parser.add_argument('-s', '--study_id', help="If there is a specific study id that you would like to append to the case nodes")
	return parser.parse_args()

if __name__ == '__main__':
	# parse the arguments 
	args = parse_arguments()

	# initalize the dictionary
	initalize_dictionary(str(args.dictionary))

	program = args.program
	project = args.project

	# initalize the graph object using the dictionary, program and project
	built_graph = initalize_graph(dictionary, program, project)

	# once the graph is initalized we then generate the nodes and construct the graph edges
	built_graph.generate_nodes_from_dictionary()
	built_graph.construct_graph_edges()

	print "\nwe are now generating the submission order\n"

	raw_file = args.raw_file
	mapping_file = args.mapping_file

	# We then create the output data files using the raw and mapping files
	# first we create the data structure necessary for creating the output files
	gen3_data = parse_mapping(raw_file, mapping_file)
	gen3_data = assign_values(raw_file, gen3_data)
	
	study_id = args.study_id
	# the output table function also returns a list of the nodes for us to itterate through
	node_list = write_tables(gen3_data, study_id)

	# we we have to create a dictionary to itterate through to make sure that all nodes have been submitted
	node_dict = {"project": True, "study": True}
	for x in node_list:
		node_dict[x] = False

	# we set up the api_url and the auth file required for submission
	api_url = args.api_url
	authfile = args.auth_file

	# we loop until all of the values in the dictionary are true
	while not all(value == True for value in node_dict.values()):
		# loop through node list and see if we can load the specific node based on what is already loaded
		for item in node_list:
			print item
			submission_order = []
			# we establish a node object from the graph using a node from the node_list
			node = built_graph.get_node_with_name(item)
			# if the node is within the graph then we go through with finding the submission order
			if node:
				print "generating submission order for node: " + node.name
				# generating the submission order
				submission_order = built_graph.generate_submission_order_path_to_node(node)
				for z in submission_order:
					print z.name
				for x in submission_order:
					if node_dict[str(x)] == False and x == submission_order[-1]:
						print "submitting " + str(x) + " node file"
						file_name = "output_" + str(x) + ".txt"
						print "running submission for " + file_name
						submit(file_name, api_url, str(program + '/' + project), authfile)
						node_dict[str(x)] = True
						# and then we submit the file
			
			# if the node is not in the graph then we skip the submission and set the node to true so that we can continue with the submission
			else:
				print "This node is not in the dictionary and we have to skip it"
				node_dict[item] = True
	
	print "Submitted all possible files"


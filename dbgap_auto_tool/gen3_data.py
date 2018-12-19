class data_dictionary(object):
	"""
	gen3_data stores data nodes in dictionary with key of node string
	e.x. data["case"] = gen3_data_node(case)
	"""

	def __init__(self):
		self.data = {}

	def set_data_node(self, gen3_data_node):
		self.data[gen3_data_node.node_name] = gen3_data_node

	def get_data_from_node(self, node_name):
		return self.data[node_name]

	def get_data_node_names(self):
		return self.data.keys()

class data_node(object):
	"""
	gen3_data_node contains all data in node
	
	node_name: string 
		the name of the node

	mappings: list[dict] 
		A list of dictionaries that contain mappings from dbgap variable names to gen3 variables
	
	suffix: dict{pair:string}
		a dictionary with a pair key string value
			pair is dbGap variable, gen3 variable
			string is the suffix to be added to end of the value for the specific mapping
	
	code_mapping: dict{dict}:
		a dictionary that contains a mapping between a code and code value mapping
			e.x. code_mapping[gender] == {1 : male}

	indicies: list[int]
		a list of integers that are the index for mapping dbGap variables to gen3 variables in the raw file

	value: list[string]
		a list of strings containing the values for the specific data_node
	"""

	def __init__(self, node_str):
		self.node_name = node_str
		self.mappings = []
		self.suffix = {}
		self.convertable = []
		self.code_mapping = {}
		self.indicies = []
		self.value = []

	def append_mapping(self, dbGap_variable, gen3_variable):
		# append a new dbgap to gen3 variable mapping
		self.mappings.append({dbGap_variable: gen3_variable})

	def append_suffix(self, dbGap_variable, gen3_variable, gen3_suffix):
		# append a new suffix that is added to the gen3_variable value
		self.suffix[(dbGap_variable, gen3_variable)] = gen3_suffix

	def append_convertable(self, boolean):
		# append
		if boolean:
			self.convertable.append(True)
		else:
			self.convertable.append(False)

	def set_code_mapping(self, gen3_variable, code_mapping):
		# if the variable is an enum type then we establish a code mapping
		self.code_mapping.setdefault(gen3_variable, {})
		self.code_mapping[gen3_variable][code_mapping[0]] = [code_mapping[1]]

	def append_index(self, mapping_index):

		self.indicies.append(mapping_index)

	def append_value(self, value):
		self.value.append(value)





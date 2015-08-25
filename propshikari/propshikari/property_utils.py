from __future__ import unicode_literals
import frappe
import json



def validate_property_data(data, property_field_list):
	
	"""  
	    Validate if given mandatory property from property_field_list exists in request data.
	    If not found then user request will not procced further.

	"""
	
	for property_field in property_field_list:
		if not data.has_key(property_field):
			print property_field
			return False
	return True	

def generate_search_query(property_data):

	""" 
        Generate search query for property search from given sets of criteria 
        like property-type, property_subtype, budget, area etc.

	"""

	property_field_dict = {"operation":"opertaion", "property_type":"property_type", "property_subtype":"property_subtype", "location":"location", "property_subtype_option":"property_subtype_option"}
	must_clause_list = [ {"match":{ property_field : property_data.get(request_field) } } for request_field,property_field in property_field_dict.items() if property_data.get(request_field,False)]
	range_field_dict = { "area":"carpet_area", "budget":"price" }
	range_list = [ {"range":{ property_field : {  "gte":property_data.get(request_field).get("from") if isinstance(property_data.get(request_field),dict) else 0 , "lte":property_data.get(request_field).get("to") if isinstance(property_data.get(request_field),dict) else property_data.get(request_field) } } } for request_field,property_field in range_field_dict.items() if property_data.get(request_field,False)]
	must_clause_list.extend(range_list)
	search_query = { "query":{ "bool":{ "must":must_clause_list } } }
	return search_query	



def validate_property_posting_data(property_data):

	" Validate property posting data for valid datatype, fields and for mandatory fields "

	property_mapper = {}
	with open("/home/indictrans/Documents/prop_shikari/frappe-bench/apps/propshikari/propshikari/propshikari/property_mapper.json","r") as pi:
		property_mapper = json.loads(pi.read())

	for field_name,schema in property_mapper.items():
		if schema.get("is_mandatory"):
			if not property_data.get(field_name,False):
				return "Mandatory field {0}".format(field_name)
			elif property_data.get(field_name):
				validate_for_field_type(schema, property_data.get(field_name), field_name)	
		elif property_data.get(field_name,False):
			return validate_for_field_type(schema, property_data.get(field_name), field_name)


def validate_for_field_type(schema, field_value, field_name):
	field_type = schema.get("field_type")
	print [schema, field_value, field_name]
	if field_type == "string":
		if not isinstance(field_value,unicode):
			return "Invalid Type of field {0}".format(field_name)
	elif field_type == "number":
		if not isinstance(field_value,(int,long,float)):
			return "Invalid Type of field {0}".format(field_name)
	elif field_type == "integer":
		if not isinstance(field_value,int):
			return "Invalid Type of field {0}".format(field_name)
	elif field_type == "nested":
		if not isinstance(field_value,list):
			return "Invalid Type of field {0}".format(field_name)
		elif isinstance(field_value,list):
			for key in field_value:
				if not isinstance(key,dict):
					return "Invalid Type of field {0}".format(field_name)	
	elif field_type == "list":
		if not isinstance(field_value,list):
			return "Invalid Type of field {0}".format(field_name)
	elif field_type == "object":
		if not isinstance(field_value,dict):
			return "Invalid Type of field {0}".format(field_name)			




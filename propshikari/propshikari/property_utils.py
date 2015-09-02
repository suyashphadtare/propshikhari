from __future__ import unicode_literals
import frappe
import os
import time
import json
from api_handler.api_handler.exceptions import *



def validate_property_data(data, property_field_list):
	
	"""  
	    Validate if given mandatory property from property_field_list exists in request data.
	    If not found then user request will not procced further.

	"""
	
	for property_field in property_field_list:
		if not data.get(property_field,False):
			raise MandatoryError("Mandatory field {0} missing".format(property_field))
	return True	

def generate_search_query(property_data):

	""" 
        Generate search query for property search from given sets of criteria 
        like property-type, property_subtype, budget, area etc.

	"""

	property_field_dict = {"operation":"opertaion", "property_type":"property_type", "property_subtype":"property_subtype", "location":"location", "property_subtype_option":"property_subtype_option"}
	must_clause_list = [ {"match":{ property_field : property_data.get(request_field) } } for request_field,property_field in property_field_dict.items() if property_data.get(request_field,False)]
	range_field_dict = { "carpet_area":["min_area", "max_area"], "price" :["min_budget", "max_budget"] }
	range_dict = {}
	for key,value in range_field_dict.items():
		result = get_range_query(key,value,property_data)
		if result:
			range_dict[key] = result		
	if range_dict:
		range_list = [ {"range": {range_key:range_value} } for range_key,range_value in range_dict.items() ]
		must_clause_list.extend(range_list)
	search_query = { "query":{ "bool":{ "must":must_clause_list } } }
	return search_query	

def get_range_query(key,value,request_data):
	new_dict = {}
	if request_data.get(value[0]) and request_data.get(value[1]):
		new_dict["gte"] = request_data.get(value[0])
		new_dict["lte"] = request_data.get(value[1])
	elif request_data.get(value[0]) and not request_data.get(value[1]):
		new_dict["gte"] = request_data.get(value[0])
	elif not request_data.get(value[0]) and request_data.get(value[1]):
		new_dict["gte"] = 0
		new_dict["lte"] = request_data.get(value[1])
	return new_dict			


def validate_property_posting_data(property_data,file_name):

	" Validate property posting data for valid datatype, fields and for mandatory fields "


	property_mapper = {}
	with open(os.path.join(os.path.dirname(__file__),file_name),"r") as pi:
		property_mapper = json.loads(pi.read())

	property_mapper_keys = property_mapper.keys()
		
	for field_name,schema in property_mapper.items():
		if schema.get("is_mandatory") and not property_data.get(field_name,False):
			raise MandatoryError("Mandatory field {0} missing".format(field_name))
		elif property_data.has_key(field_name):
			validate_for_field_type(schema, property_data.get(field_name), field_name)
	
	return {key:property_data.get(key) for key in property_data if key in property_mapper_keys}



def validate_for_field_type(schema, field_value, field_name):
	field_type = schema.get("field_type")
	type_mapper = {"string":unicode, "number":(int,long,float), "integer":int, "list":list, "object":dict, "nested":list}
	if not isinstance(field_value,type_mapper.get(field_type)):
		raise InvalidDataError("Invalid input of field {0}".format(field_name))
	if field_type == "nested":
	   if isinstance(field_value,list):
			for key in field_value:
				if not isinstance(key,dict):
					raise InvalidDataError("Invalid input of field {0}".format(field_name))



def validate_for_user_id_exists(user_id):
	email = frappe.db.get_value("User", {"user_id": user_id}, "email")
	if not email:
		raise DoesNotExistError("User id does not exists")					 
	return email


def generate_hash(txt=None):
	import hashlib
	return hashlib.sha224((txt or "") + repr(time.time()))
from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint
import property_utils as putil
import json
import time
import random
from api_handler.api_handler.exceptions import *

"""
	Get List of all property types and subtypes.
	return the response in format specified in api 
"""
def get_property_types(data):
	if data:
		
		data = json.loads(data)
		types_list = []
		
		for property_type in get_types():
			subtypes = get_subtypes(property_type[0])
			subtypes_list = [d.property_subtype for d in subtypes]
			types_list.append({"property_type":property_type[0],"sub_types":subtypes_list})
		
		response_msg = "Property Types Not Found" if len(types_list) == 0 else "Property Types Found"
			
		return {"operation":"Search","message":response_msg,"data":types_list}	


"""
	Get List of all Amenities.
	return the response in format specified in api 
"""
def get_amenities(data):
	if data:
		data = json.loads(data)
		amenities_list = []
		
		for property_type in get_types():
			amenities = get_amenities_subs(property_type[0])
			amenities_list.append({property_type[0]:amenities})
		
		response_msg = "Amenities Not Found" if len(amenities_list) == 0 else "Amenities Found"
			
		return {"operation":"Search","message":response_msg,"data":amenities_list}


"""
	Get List of all Flat Facilities.
	return the response in format specified in api 
"""
def get_flat_facilities(data):
	if data:
		data = json.loads(data)
		facilities_list = []
		
		for property_type in get_types():
			facilities = get_facility_subs(property_type[0])
			facilities_list.append({property_type[0]:facilities})
		
		response_msg = "Flat Facilities Not Found" if len(facilities_list) == 0 else "Flat Facilities Found"
			
		return {"operation":"Search","message":response_msg,"data":facilities_list}


def get_types():
	return frappe.db.sql("""select property_type from 
		`tabProperty Type`""",as_list=1)

def get_subtypes(property_type):
	return frappe.db.get_all("Property Subtype",
		filters={"property_type": property_type},fields=["property_subtype"])

def get_amenities_subs(property_type):
	return frappe.db.get_all("Amenities",
		filters={"property_type": property_type},fields=["amenity_name","icon"])

def get_facility_subs(property_type):
	return frappe.db.get_all("Flat Facilities",
		filters={"property_type": property_type},fields=["facility"])
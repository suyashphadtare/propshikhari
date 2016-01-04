from __future__ import unicode_literals
import frappe
import os
import time
import json
import math
from api_handler.api_handler.exceptions import *
from frappe.utils import cstr, cint, date_diff, flt
from dateutil import relativedelta
from datetime import datetime



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
	

	property_field_dict = {"operation":"operation", "property_type":"property_type", "property_subtype":"property_subtype", "location":"location", "property_subtype_option":"property_subtype_option", "city":"city"}
	must_clause_list = [ {"match":{ property_field : property_data.get(request_field) } } for request_field,property_field in property_field_dict.items() if property_data.get(request_field,False)]
	must_clause_list.append({"match":{ "status": "Active" } })
	
	range_field_dict = { "carpet_area":["min_area", "max_area"], "price" :["min_budget", "max_budget"] }
	range_dict = {}
	for key,value in range_field_dict.items():
		result = get_range_query(key,value,property_data)
		if result:
			range_dict[key] = result		
	if range_dict:
		range_list = [ {"range": {range_key:range_value} } for range_key,range_value in range_dict.items() ]
		must_clause_list.extend(range_list)
	search_query = { "query":{ "bool":{ "must":must_clause_list } }, "sort": [{ "posted_datetime": { "order": "desc" }}] }
	# print search_query
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
	if not isinstance(field_value, type_mapper.get(field_type)) and field_value:
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


def validate_for_property_photo_fields(request_data):
	for property_photo in request_data:
		if not property_photo.get("file_data"):
			raise MandatoryError("File data not found in property photo")
		if not property_photo.get("file_ext"):
			raise MandatoryError("File extension not found in property photo")


def validate_property_status(status):
	if not status:
		raise MandatoryError("Property Status Not found")	
	else:
		if status not in ["Deactivated" ,"Active", "Sold"]:
			raise InvalidDataError("Invalid input of property status field")




def generate_search_query_from_property_data(property_data):

	""" 
        Generate search query for get similar property from given sets of criteria 
        like property-type, property_subtype, budget, area etc.

	"""

	
	property_field_dict = {"operation":"operation", "property_type":"property_type", "property_subtype":"property_subtype", "location":"location", "property_subtype_option":"property_subtype_option", "city":"city"}
	must_clause_list = [ {"match":{ property_field : property_data.get(request_field) } } for request_field,property_field in property_field_dict.items() if property_data.get(request_field,False)]
	must_clause_list.append({"match":{ "status": "Active" } })
	range_list = [ {"range": {range_key:{"lte":property_data.get(range_key)}} } for range_key in ["carpet_area","price"] if property_data.get(range_key,False)]
	must_clause_list.extend(range_list)
	search_query = { "query":{ "bool":{ "must":must_clause_list } }, "sort": [{ "posted_datetime": { "order": "desc" }}] }
	return search_query				


def validate_for_postings_available(email):
	user_data = frappe.db.get_value("User",{"email":email}, "user_type", as_dict=True)
	if user_data.get("user_type") != "System User":
		subs_name = frappe.db.get_value("User Subscription",{"user":email},"name")
		if subs_name:
			subs_doc = frappe.get_doc("User Subscription",subs_name)
			remaining = cint(subs_doc.allowed) - cint(subs_doc.posted)
			if remaining == 0:
				raise ValidationError("Posting Limit Exhausted")
			else:
				return subs_doc					 

def get_subscriptions(user):
	subs_dic = {}
	subs_name = frappe.db.get_value("User Subscription",{"user":user},"name")
	if subs_name:
		subs_doc = frappe.get_doc("User Subscription",subs_name)
		subs_dic["posting_allowed"] = cint(subs_doc.allowed)
		subs_dic["total_posted"] = cint(subs_doc.posted) or 0
		subs_dic["posting_available"] = cint(subs_doc.allowed) - cint(subs_doc.posted)
	return subs_dic



def prepare_amenities_data(amenities_data, property_type):
	amenities = []
	amenity_list = frappe.db.sql(" select ifnull(amenity_name,'') as name ,ifnull(icon,'') as image  from `tabAmenities` where property_type='{0}' ".format(property_type),as_dict=True)
	for amenity in amenity_list:
		amenity_dict = {}
		amenity_dict["status"] = "Yes" if amenity.get("name") in amenities_data else "No"
		amenity_dict["name"] = amenity.get("name")
		amenity_dict["image"] = amenity.get("image")
		amenities.append(amenity_dict)
	return amenities


def prepare_flat_facilities_data(facility_data, property_type):
	flat_facilities = []
	flat_facilities_list = frappe.db.sql(" select ifnull(facility,'') as name ,ifnull(icon,'') as image  from `tabFlat Facilities` where property_type='{0}' ".format(property_type),as_dict=True)
	for flat_facility in flat_facilities_list:
		facility_dict = {}
		facility_dict["status"] = "Yes" if flat_facility.get("name") in facility_data else "No"
		facility_dict["name"] = flat_facility.get("name")
		facility_dict["image"] = flat_facility.get("image")
		flat_facilities.append(facility_dict)
	return flat_facilities


def get_date_diff_from_posting(response_data):
	for response in response_data:
		current_date = datetime.now()
		if response.get("posted_datetime"):
			posting_date = datetime.strptime(response.get("posted_datetime"), "%Y-%m-%d %H:%M:%S")
			r = relativedelta.relativedelta(current_date, posting_date)
			if r.years:
				response["elapsed_time"] = "{0} year ago".format(r.years)
			elif r.months:
				response["elapsed_time"] = "{0} month ago".format(r.months)
			elif r.days:
				response["elapsed_time"] = "{0} days ago".format(r.days)
			elif r.hours:
				response["elapsed_time"] = "{0} hours ago".format(r.hours)
			elif r.minutes:
				response["elapsed_time"] = "{0} minutes ago".format(r.minutes)
			elif r.seconds:
				response["elapsed_time"] = "{0} seconds ago".format(r.seconds)			
	return response_data


def isolate_city_from_location(property_data):
	if property_data.get("location"):
		location_city_list = property_data.get("location").split(',')
		if len(location_city_list) == 2: 
			property_data["location"] = location_city_list[0]
			property_data["city"] = location_city_list[1]
		elif len(location_city_list) > 2:
			raise InvalidDataError("Invalid Input of Location Field")


def init_for_location_or_city_creation(property_data):
	if property_data.get("location"):
		location_city_list = property_data.get("location").split(',')
		condition = ",".join('"{0}"'.format(loc) for loc in location_city_list)
		area_list = frappe.db.sql(""" select * from `tabArea` where name in ({0}) """.format(condition), as_dict=True)
		if area_list: 
			property_data["location"] = ",".join([ area.get("area") for area in area_list ])
			city_ids = [area.get("city_name") for area in area_list if area.get("city_name")]
			city_name = frappe.db.get_value("City", {"name":city_ids[0]}, "city_name")
			property_data["city"] = city_name if city_name else ""
		else:
			city_name = frappe.db.get_value("City", {"name":property_data.get("location")}, "city_name")
			property_data["city"] = city_name if city_name else ""
			property_data.pop("location")



def generate_advance_search_query(adv_search_query, property_data):
	adv_search_dict = {"transaction_type":"transaction_type", "property_age":"property_age", "listed_by":"listed_by",
						"possession":"possession_status", "posting_date":"posting_date"}
	adv_list = [ {"match":{ property_field : property_data.get(request_field) } } 
							for request_field, property_field in adv_search_dict.items() if property_data.get(request_field,False)]
	must_clause_list = adv_search_query.get("query").get("bool").get("must")
	must_clause_list.extend(adv_list)
	prepare_amenities_query(must_clause_list, property_data)
	adv_search_query["query"]["bool"]["must"] = must_clause_list
	if property_data.get("sort_by",""):
		sort_mapper = {"Posting Date":"posted_datetime", "Budget":"price"}
		adv_search_query["sort"]  = [{ sort_mapper.get(property_data.get("sort_by")): { "order": property_data.get("sort_order", "desc") }}]	




def prepare_amenities_query(must_clause_list, property_data):
   if property_data.get("amenities"):
		amenity_query = [ { "match": { "amenities.name" : amenity } } 
								for amenity in property_data.get("amenities") if amenity ]
		nested_query = [{
				          "nested": {
										"path": "amenities", 
										"query": { "bool": { 
																"must":[{ "match" :{ "amenities.status":"Yes" }} ],
																"should": amenity_query, 
																"minimum_should_match":1 } 
															}
				        			}
				        }]
		must_clause_list.extend(nested_query)    


def generate_project_search_query(project_data):

	""" 
        Generate search query for project search from given sets of criteria 
        like project-type, project_subtype, budget, area etc.

	"""
	

	project_field_dict = {"project_type", "project_subtype", "location", "city"}
	must_clause_list = [ {"match":{ project_field : project_data.get(project_field) } } for project_field in project_field_dict if project_data.get(project_field,False)]
	must_clause_list.append({"match":{ "status": "Active" } })
	range_dict = {	
					"property_details.min_area":["min_area","gte"], 
					"property_details.max_area":["max_area", "lte"], 
					"property_details.min_price":["min_budget","gte"], 
					"property_details.max_price":["max_budget","lte"]
				}	
	
	range_list = [ {"range": {range_key: {range_value[1]:project_data.get(range_value[0])  } } } for range_key,range_value in range_dict.items() if project_data.get(range_value[0])]
	filter_query = prepare_nested_query(range_list, project_data)
	search_query = { "query": { "filtered":{ "query":{ "bool":{ "must":must_clause_list } }, "filter":filter_query}   }, "sort": [{ "posted_datetime": { "order": "desc" }}] }
	return search_query


def prepare_nested_query(range_list, project_data):
	if project_data.get("property_subtype_option"):
		property_subtype_option_query = { 
											"match":  
												{
                                               		"property_subtype_option": project_data.get("property_subtype_option")
												}											
	                                    }
		range_list.append(property_subtype_option_query)
	if range_list:	                         		      
		return { "nested":
					{ 
						"path":"property_details",
						"query":{ 
							"bool":{ "must":range_list }  
						} 
					} 
				}
	else:
		return {}			



def convert_area_to_sqft_for_posting(request_data):
	uom_mapper = {"Acres" :43560, "Hectares":107639}
	uom = request_data.get("unit_of_area")
	validate_for_valid_uom(uom) if uom else ""
	if uom and uom != "Sq.Ft.":
		request_data["carpet_area"] = uom_mapper.get(uom) * request_data.get("carpet_area",0)


def convert_area_to_sqft_for_search(request_data):
	uom_mapper = {"Acres" :43560, "Hectares":107639}
	uom = request_data.get("unit_of_area")
	validate_for_valid_uom(uom) if uom else ""
	if uom and uom != "Sq.Ft.":
		for area in ["min_area", "max_area"]:
			if request_data.get(area,False):
				request_data[area] = uom_mapper.get(uom) * flt(request_data.get(area,0))


def convert_area_according_to_uom(response_data, uom):
	for response in response_data:
		response["carpet_area"] = get_carpet_area(response.get("carpet_area"),uom) if uom != "Sq.Ft." else response.get("carpet_area")
		response["unit_of_area"] = uom


def get_carpet_area(carpet_area, uom):
	uom_mapper = {"Acres" :43560, "Hectares":107639}
	return  round( carpet_area / flt(uom_mapper.get(uom)),2)


def validate_for_valid_uom(uom):
	if uom not in ["Sq.Ft.", "Acres", "Hectares"]:
		raise InvalidDataError("Unit of area must be from Sq.Ft. , Acres, Hectares")


def get_discounted_price(request_data):
	discount_price = request_data.get("price",0.0) - (  request_data.get("price",0.0) * request_data.get("discount_percentage",0.0) / 100 )
	return discount_price


def validate_project_posting_data(property_data,file_name):

	" Validate project posting data for valid datatype, fields and for mandatory fields "


	property_mapper = {}
	property_details_list = []
	with open(os.path.join(os.path.dirname(__file__),file_name),"r") as pi:
		property_mapper = json.loads(pi.read())

	property_mapper_keys = property_mapper.keys()
		
	for prop in property_data:
		for field_name,schema in property_mapper.items():
			if schema.get("is_mandatory") and not prop.get(field_name,False):
				raise MandatoryError("Mandatory field {0} missing".format(field_name))
			elif prop.has_key(field_name):
				validate_for_field_type(schema, prop.get(field_name), field_name)
	
		property_details_list.append({key:prop.get(key) for key in prop if key in property_mapper_keys})

	return property_details_list


"""
	Calculate percent completion while property posting

"""


def calculate_percent_completion(prop, mand_list):
	count = 0
	if mand_list:
		length_total_fields = len(mand_list)
		for field in mand_list:
			if prop.get(field):
				count += 1
		try:
			return round((count / float(length_total_fields)) * 100, 0)
		except  ArithmeticError,e:
			raise InvalidDataError("Arithmatcic Exception while calculating percent completion.")	




""" This is common paginator and response dictionary generator  """



def init_pagination_and_response_generatrion(request_data, response_data, msg, total_records):
	
	from_record = ( request_data.get("page_number",1) - 1 ) * cint( request_data.get("records_per_page",40) ) + 1
	old_to_record = from_record + request_data.get("records_per_page",40) - 1
	to_record = (from_record +  len(response_data) - 1) if response_data else old_to_record 
	no_of_pages = math.ceil( flt(total_records) / request_data.get("records_per_page",40))
	
	return {
				"operation":"Search", 
				"message":msg ,
				"total_records":total_records,
				"records_per_page":request_data.get("records_per_page",40),
				"from_record":from_record ,
				"to_record":to_record,
				"data":response_data, 
				"user_id":request_data.get("user_id"), 
				"no_of_pages":no_of_pages
			}


def show_amenities_with_yes_status(response_data):
	for response in response_data:
		if response.get("amenities", ""):
			response["amenities"] = [ amenity for amenity in response.get("amenities") if amenity.get("status") == "Yes"]
		if response.get("flat_facilities", ""):
			response["flat_facilities"] = [ facility for facility in response.get("flat_facilities") if facility.get("status") == "Yes"]
	



def get_exclude_list_for_search(request_source):
	exclude_list = ["agent_name", "agent_no", "contact_no", "contact_person", "created_by", 
			"modified_by", "creation_date", "modified_date", "modified_datetime"]
	if request_source == "Hunterscamp":
		exclude_list = ["created_by", "modified_by", "creation_date", "modified_date", "posted_datetime", "modified_datetime"]		
	return exclude_list	




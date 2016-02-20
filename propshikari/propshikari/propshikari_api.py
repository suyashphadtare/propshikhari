from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, flt
from elastic_controller import ElasticSearchController
from frappe.utils import add_days, getdate, now, nowdate ,random_string ,add_months, date_diff
from property_masters import create_lead_from_userid, make_conditions_for_duplicate_group
from percent_completion import property_mandatory_fields
from frappe.auth import _update_password
import property_utils as putil
import json ,ast
import time
import random
from collections import OrderedDict
import datetime
from PIL import Image
import os
import base64
import elasticsearch
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import math
from api_handler.api_handler.exceptions import *
from frappe import _, msgprint




def post_property(data):
	try:
		request_data = json.loads(data)
		property_data, email, subs_doc = validate_data_before_property_posting(request_data)
		custom_id = process_property_data_before_posting(property_data, request_data, email)
		
		es = ElasticSearchController()
		response_data = es.index_document("property",property_data, custom_id)
		subscription = get_subscription_of_user(subs_doc, response_data, email)
		response_msg = "Property posted successfully" if response_data.get("created",False) else "Property posting failed" 
		return {
					"operation":"Create", 
					"message":response_msg, 
					"property_id":response_data.get("_id"), 
					"user_id":request_data.get("user_id"),
					"data":{"subscriptions":subscription}
				}	
	except elasticsearch.RequestError,e:
		raise ElasticInvalidInputFormatError(e.error)
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)
	except Exception,e:
		raise e	






def validate_data_before_property_posting(request_data):
	
	"""
		Validate property posting data, convert area to sqft
		& other validatory tasks.
	"""

	email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	subs_doc = putil.validate_for_postings_available(email)
	putil.convert_area_to_sqft_for_posting(request_data)
	putil.validate_property_status(request_data.get("status"))
	property_data = putil.validate_property_posting_data(request_data,"property_json/property_mapper.json")
	return property_data, email, subs_doc






def process_property_data_before_posting(property_data, request_data, email):
	
	"""
		Add necessary fields to property dictionary
		before indexing property data, 
		store image in full size & thumbnails format. 

	"""
	
	custom_id = "PROP-"  + cstr(int(time.time())) + '-' +  cstr(random.randint(10000,99999))
	property_data["property_id"] = custom_id
	meta_dict = add_meta_fields_before_posting(request_data)
	property_data.update(meta_dict)
	property_photo_url_dict = store_property_photos_in_propshikari(request_data.get("property_photos"),custom_id)
	property_data["full_size_images"] = property_photo_url_dict.get("full_size",[])
	property_data["thumbnails"] = property_photo_url_dict.get("thumbnails",[])
	property_data["property_photo"] = property_photo_url_dict.get("thumbnails")[0] if len(property_photo_url_dict.get("thumbnails")) else ""
	property_data["posted_by"] = request_data.get("user_id")
	property_data["user_email"] = email
	property_data["posting_date"] = property_data.get("posting_date") if property_data.get("posting_date") else property_data.get("creation_date")
	property_data["amenities"] = putil.prepare_amenities_data(property_data.get("amenities",""), property_data.get("property_type"))
	property_data["flat_facilities"] = putil.prepare_flat_facilities_data(property_data.get("flat_facilities",""), property_data.get("property_type"))
	property_data["possession_status"] = "Immediate" if property_data.get("possession") else property_data.get("possession_date")
	property_data["discounted_price"] = putil.get_discounted_price(property_data) if property_data.get("discount_percentage") else 0.0
	mandatory_list = property_mandatory_fields.get(property_data.get("property_type"))
	property_data["percent_completion"] = putil.calculate_percent_completion(property_data, mandatory_list)
	# added by arpit for  published_status
	property_data["published_status"] = "Unpublished"
	property_data["tag"] = property_photo_url_dict.get("tag",[])
	# end of code
	if not property_data.get("possession_date"):
		property_data.pop("possession_date", None)
	return custom_id	




def get_subscription_of_user(subs_doc, response_data, email):
	if subs_doc and response_data.get("created"):
		subs_doc.posted = cint(subs_doc.posted) + 1
		subs_doc.save(ignore_permissions=True)
	return putil.get_subscriptions(email)




"""
	Search property according to given criteria
	like property_type, sub_type, price, area.

"""

def search_property(data):
	
	property_data = json.loads(data)
	property_data = putil.validate_property_posting_data(property_data, "property_json/property_search.json")
	putil.init_for_location_or_city_creation(property_data)
	putil.convert_area_to_sqft_for_search(property_data)
	try:	
		
		# generate search query & result generation & list of fields which should be excluded.

		exclude_list = putil.get_exclude_list_for_search(property_data.get("request_source", ""))

		search_query = putil.generate_search_query(property_data)
		adv_search_query = search_query
		search_query = cstr(search_query)
		putil.generate_advance_search_query(adv_search_query, property_data)

		es = ElasticSearchController()
		response_data, total_records = es.search_document(["property"], adv_search_query, property_data.get("page_number",1), 
										property_data.get("records_per_page",40), exclude_list)
		
		# post property-search operation

		if not property_data.get("request_id"):	
			request_id = store_request_in_elastic_search(property_data, search_query, "Property Search", adv_search_query)
		if property_data.get("user_id") != "Guest":				
			response_data = check_for_shortlisted_property(response_data,property_data.get("user_id"))
		response_data = putil.get_date_diff_and_count_from_posting(response_data)
		putil.convert_area_according_to_uom(response_data, property_data.get("unit_of_area", "Sq.Ft."))
		putil.show_amenities_with_yes_status(response_data)
		
		# response data & pagination logic

		msg = "Property found for specfied criteria" if len(response_data) else "Property not found"
		response_dict = putil.init_pagination_and_response_generatrion(property_data, response_data, msg, total_records)
		response_dict["request_id"] = property_data.get("request_id") if property_data.get("request_id") else request_id 
		return response_dict

	except elasticsearch.RequestError,e:
		raise ElasticInvalidInputFormatError(e.error)
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)
	except Exception,e:
		raise e

# code added by arpit

def search_unpublished_property(data):
	
	property_data = json.loads(data)
	
	try:	
		
		# generate search query & result generation & list of fields which should be excluded.

		exclude_list = putil.get_exclude_list_for_search(property_data.get("request_source", ""))
	
	 
		#property_field_dict = {"operation":"operation", "property_type":"property_type", "property_subtype":"property_subtype", "location":"location", "property_subtype_option":"property_subtype_option", "city":"city"}
		#must_clause_list = [ {"match":{ property_field : property_data.get(request_field) } } for request_field,property_field in property_field_dict.items() if property_data.get(request_field,False)]

		#must_clause_list.append([{"match":{ "published_status": "Unpublished" } }, { "match": { "status": "Deactivated" }}])
		must_clause_list= [{"match":{ "published_status": "Unpublished" } }]
		# range_field_dict = { "carpet_area":["min_area", "max_area"], "price" :["min_budget", "max_budget"] }
		# range_dict = {}
		# for key,value in range_field_dict.items():
		# 	result = get_range_query(key,value,property_data)
		# 	if result:
		# 		range_dict[key] = result	
		# #msgprint(_(range_dict))	
		# if range_dict:
		# 	range_list = [ {"range": {range_key:range_value} } for range_key,range_value in range_dict.items() ]
		# 	must_clause_list.extend(range_list)
		search_query = { "query":{ "bool":{ "must":must_clause_list } }, "sort": [{ "posted_datetime": { "order": "desc" }}] }

		#msgprint(_(search_query))



		es = ElasticSearchController()
		response_data, total_records = es.search_document(["property"], search_query, property_data.get("page_number",1), 
										property_data.get("records_per_page",40), exclude_list)
		
		#msgprint(_(response_data))
		##msgprint(_("############"))
		#msgprint(_(total_records))
		#frappe.throw(_("############"))
		# post property-search operation

		#if not property_data.get("request_id"):	
		#	request_id = store_request_in_elastic_search(property_data, search_query, "Property Search", adv_search_query)
		if property_data.get("user_id") != "Guest":				
			response_data = check_for_shortlisted_property(response_data,property_data.get("user_id"))
		response_data = putil.get_date_diff_and_count_from_posting(response_data)
		putil.convert_area_according_to_uom(response_data, property_data.get("unit_of_area", "Sq.Ft."))
		putil.show_amenities_with_yes_status(response_data)
		
		# response data & pagination logic

		msg = "Property found for specfied criteria" if len(response_data) else "Property not found"
		response_dict = putil.init_pagination_and_response_generatrion(property_data, response_data, msg, total_records)
		#response_dict["request_id"] = property_data.get("request_id") if property_data.get("request_id") else request_id 
		return response_dict

	except elasticsearch.RequestError,e:
		raise ElasticInvalidInputFormatError(e.error)
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)
	except Exception,e:
		raise e


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
	#msgprint(_(new_dict))	
	return new_dict	




def update_unpublished_property_flag(request_data):
	if request_data:
		#email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		#putil.validate_property_data(request_data, ["property_id"])
		#putil.validate_property_status(request_data.get("property_status"))	
		try:
			property_data = prepare_query_of_published_properties(request_data.get("property_ids"))
			es = ElasticSearchController()
			print property_data
			# response = es.updatupe_docuemnt("property", request_data.get("property_id"), search_query)
			response = es.bulk_upload(property_data)
			return {"operation":"Update" , "message":"Unpublished property status changed" if response else "upublished Status not changed", "user_id":request_data.get("user_id")}
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except elasticsearch.ElasticsearchException,e:
			raise e	
		except Exception,e:
			raise OperationFailed("Update Property Status Operation Failed")




def prepare_query_of_published_properties(properties):
	data = []
	for prop in properties:
		dict_data ={}
		dict_data["_op_type"] ='update'
	 	dict_data["_index"] ='propshikari'
	 	dict_data["_type"] ='property'
	 	dict_data["_id"] = prop
	 	dict_data["script"] ="""ctx._source.status = prop_status; ctx._source.published_status = published_flag ; 
	 								ctx._source.tag += tags"""
	 	dict_data["params"] ={"prop_status":"Active","published_flag":"published","tags":["Verified"]}
	 	data.append(dict_data)
	return data
# end of code



@frappe.whitelist(allow_guest=True)
def check_connection():
	return dir()





def log_out_from_propshikari(data):
	request_data = json.loads(data)
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	try:
		frappe.local.login_manager.logout()
		frappe.db.commit()
		return {"operation":"Log Out", "message":"Successfully Logged Out"}
	except Exception:
		raise LogOutOperationFailed("Log Out Unsuccessful")



def get_states_cities_locations_from_propshikari(data):
	request_data = json.loads(data)
	try:
		state_list = frappe.db.sql("select name as state_name from `tabState` ",as_dict=True)
		city_list =  frappe.db.sql("select city_name, name as city_nm, state_name from `tabCity` ",as_dict=True)
		address_list = []
		for state in state_list:
			address_dict = OrderedDict()
			address_dict["state_name"] = state.get("state_name")
			address_dict["state_id"] = state.get("state_name")
			address_dict["cities"] = [  { 
			                              "city_name":city.get("city_name"), 
										  "city_id": city.get("city_nm"),
										  "location":frappe.db.sql(""" select name as location_id,
										  									area as location_name , 
																			lattitude as geo_location_lat ,
																			longitude as geo_location_lon 
																			from `tabArea` 
																			where city_name='{0}'  and state_name='{1}' """.format(city.get("city_nm"), state.get("state_name")),as_dict=True) 
										  }  
										for city in city_list if city.get("state_name") == state.get("state_name")] 
			address_list.append(address_dict)
		state_dict = {"states":address_list}	
		return { "operation":"search", "message":"States Information Found", "user_id":request_data.get("user_id"), "data":state_dict}
	except Exception,e:
		raise GetStateInfoOperationFailed("Get State info Operation Failed")





def store_request_in_elastic_search(property_data, search_query, request_type, adv_search_query=None):
	request_id =  "REQ-"  + cstr(int(time.time())) + '-' +  cstr(random.randint(100000,999999))
	request_dict = {
		"user_id":property_data.get("user_id"),
		"request_id":request_id, 
		"operation":property_data.get("operation"), 
		"property_type":property_data.get("property_type"), 
		"property_subtype":property_data.get("property_subtype"),
		"project_type":property_data.get("project_type"), 
		"project_subtype":property_data.get("project_subtype"),  
		"location":property_data.get("location"), 
		"property_subtype_option":property_data.get("property_subtype_option"), 
		"min_area":property_data.get("min_area"),
		"max_area":property_data.get("max_area"), 
		"min_budget":property_data.get("min_budget"), 
		"max_budget":property_data.get("max_budget"),
		"city":property_data.get("city"),
		"unit_of_area":property_data.get("unit_of_area"),
		"search_query":cstr(search_query),
		"adv_search_query":cstr(adv_search_query),
		"request_type":request_type,

	}
	meta_dict = add_meta_fields_before_posting(property_data)
	request_dict.update(meta_dict)
	es = ElasticSearchController()
	es_result = es.index_document("request",request_dict, request_id)
	return request_id


def add_meta_fields_before_posting(property_data):
	new_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	new_date = datetime.datetime.now().strftime("%d-%m-%Y")
	return {
		"created_by":property_data.get("user_id"),
		"modified_by":property_data.get("user_id"),
		"creation_date":new_date,
		"modified_date":new_date,
		"modified_datetime":new_datetime,
		"posted_datetime":new_datetime
	}



def store_property_photos_in_propshikari(request_data, custom_id):
	property_url_dict = {"full_size":[], "thumbnails":[],"tag":[]}
	size = 400,400
	if request_data:
		putil.validate_for_property_photo_fields(request_data)
		if not os.path.exists(frappe.get_site_path("public","files",custom_id)):
			os.makedirs(frappe.get_site_path("public","files",custom_id,"regular"))
			os.mkdir(frappe.get_site_path("public","files",custom_id,"thumbnail"))
		for property_photo in request_data:
			file_ext = property_photo.get("file_ext")	
			try:
				base64_data = property_photo.get("file_data").encode("utf8")				
				base64_data = base64_data.split(',')[1]
				imgdata = base64.b64decode(base64_data)
			 	old_file_name = "PSPI-" + cstr(time.time()) + random_string(5) + "." + file_ext
				
				with open(frappe.get_site_path("public","files",custom_id,"regular",old_file_name),"wb+") as fi_nm:
					fi_nm.write(imgdata)
				file_name = "files/" + custom_id + "/regular/" + old_file_name
				regular_image_url = frappe.request.host_url + file_name
				property_url_dict.get("full_size").append(regular_image_url)
				
				thumbnail_file_name = frappe.get_site_path("public","files",custom_id,"thumbnail",old_file_name)
				im = Image.open(frappe.get_site_path("public","files",custom_id,"regular",old_file_name))
				im.thumbnail(size, Image.ANTIALIAS)
				im.save(thumbnail_file_name)
				thumbnail_file_url = "files/" + custom_id + "/thumbnail/" + old_file_name	
				property_url_dict.get("thumbnails").append(frappe.request.host_url + thumbnail_file_url)
			except Exception,e:
				raise ImageUploadError("Image Upload Error")
	return property_url_dict


"""  
	Search group according to given request_id also 
	check whether user already joined group or not.

"""


def search_group_with_given_criteria(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data, ["request_id"])
		try:
			es = ElasticSearchController()
			response = es.search_document_for_given_id("request",request_data.get("request_id"))
			group_search_conditions = make_conditions_for_duplicate_group(response, "Group")
			group_result = frappe.db.sql(""" SELECT    
												name AS group_id,
												operation,
												property_type,
												property_subtype,
												group_title,
												ifnull(property_subtype_option, "") AS property_subtype_option,
												ifnull(location, "") AS location,
												ifnull(city, "") AS city,
												ifnull(min_budget, "") AS min_budget,
												ifnull(max_budget, "") AS max_budget,
												ifnull(min_area, "") AS min_area,
												ifnull(max_area, "") AS max_area
											FROM `tabGroup` {0} """.format(group_search_conditions),as_dict=True)
			for group in group_result:
				join_flag = frappe.db.get_value("Group User" , {"group_id":group.get("group_id"), "user_id":request_data.get("user_id")},"name")
				group["user_joined"] = 1 if join_flag else 0
			group_result = group_result[0] if group_result else {} 
			return {	
						"operation":"Search", 
						"request_id":request_data.get("request_id"), 
						"data":group_result, 
						"message":"Matching Group Found" if len(group_result) else "Group Not Found" 
					}
		except elasticsearch.TransportError:
			raise DoesNotExistError("Request Id does not exists")
		except Exception,e:
			raise SearchGroupOperationFailed("Search Group Operation Failed")




def make_conditions_for_group_search(response):
	group_search_conditions = "where operation='{0}' and property_subtype='{1}' and property_type='{2}' and status='Active' ".format(response.get("operation"),response.get("property_subtype"),response.get("property_type"))
	non_mandatory_fields = ["property_subtype_option", "city"]
	for field in non_mandatory_fields:
		if response.get(field):
			group_search_conditions += " and {0} = '{1}' ".format(field,response.get(field))
	if response.get("location"):
		group_search_conditions += " and location like '%{0}%' ".format(response.get("location"))
	
	range_dict = {"min_area":"max_area", "min_budget":"max_budget"}
	
	for min_field,max_field in range_dict.items():
		if response.get(min_field) and not response.get(max_field):
			group_search_conditions += " and  {0} >= {1} ".format(min_field, response.get(min_field))
		elif not response.get(min_field) and response.get(max_field):
			group_search_conditions += " and {0} <= {1} ".format(max_field , response.get(max_field))
		elif response.get(min_field) and response.get(max_field):
			group_search_conditions += " and {0} >= {1} and {2} <= {3}".format(min_field, response.get(min_field),max_field , response.get(max_field)) 			
	return group_search_conditions




""" Get property details of given pproperty Id """


def get_property_of_given_id(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		try:
			exclude_list = ["agent_name", "agent_no", "contact_no", "contact_person", "created_by", 
							"modified_by", "creation_date", "modified_date", "posted_datetime", "modified_datetime", 
							"full_size_images", "thumbnails"]
			es = ElasticSearchController()
			response = es.search_document_for_given_id("property",request_data.get("property_id"), exclude_list)
			return {
						"operation":"Search",
						"message":"Property found" if len(response) else "Property Not Found", 
						"user_id":request_data.get("user_id"), 
						"data":response
					 }
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except Exception,e:
			raise GetPropertyOperationFailed("Get Property Operation Failed")




"""  Get property details having particular tag  """


def get_property_of_particular_tag(request_data):
	if request_data:
		request_data = json.loads(request_data)
		if not request_data.get("tag"):
			raise MandatoryError("Mandatory Field Tag missing")
		try:
			
			exclude_list = ["agent_name", "agent_no", "contact_no", "contact_person", "created_by", 
				"modified_by", "creation_date", "modified_date", "posted_datetime", "modified_datetime"]

			must_clause_list = [{ "match":{ "tag":request_data.get("tag") } }, { "match":{ "status":"Active" } } ] 	
			search_query = { "query":{ "bool":{ "must":must_clause_list } } } 
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40),exclude_list)	
			putil.show_amenities_with_yes_status(response_data)

			msg = "Property found for specfied criteria" if len(response_data) else "Property not found"
			response_dict = putil.init_pagination_and_response_generatrion(request_data, response_data, msg, total_records)
			response_dict["tag"] = request_data.get("tag")
			return response_dict

		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Get Tagged Property Operation Failed")





def get_property_contact(request_data):

	"""
		Get Contact person name, contact_no form property &
		generate lead & enquiry against that user. 

	"""

	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))	
		if not request_data.get("property_id"):
			raise MandatoryError("Mandatory Field Property Id missing")
		try:
			es = ElasticSearchController()
			response = es.search_document_for_given_id("property",request_data.get("property_id"),[],[])
			mapper = {"Owner":["contact_person", "contact_no"], "Agent":["agent_name", "agent_no"], "Broker":["agent_name", "agent_no"] }
			person_key = response.get("listed_by") if response.get("listed_by") else "Owner" 
			person_no_key = response.get("listed_by") if response.get("listed_by") else "Owner" 
			new_response = { 
								"contact_person": response.get(mapper.get(person_key)[0] ), 
								"contact_no":response.get(mapper.get(person_no_key)[1] ),
								"listed_by":person_key  
							}
			create_lead_from_userid(request_data, email, response)
			return {	
						"operation":"Search",
						"message":"Contact Details found" if len(new_response) else "Contact Details Not Found", 
						"user_id":request_data.get("user_id"), 
						"data":new_response
					}
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except Exception,e:
			print frappe.get_traceback()
			raise e





"""  Get properties which are shortlisted by particular User  """


def get_shortlisted_property(request_data):
	if request_data:
		request_data = json.loads(request_data)
		
		# Check if shortlisted property existed against user 

		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		property_ids_list = frappe.db.get_values("Shortlisted Property", {"user_id":request_data.get("user_id"), "status":"Active"}, "property_id")
		if not property_ids_list:
			return {"operation":"Search", "message":"No Single Shortlisted property found", "user_id":request_data.get("user_id")}
		property_ids_list = [ property_id[0] for property_id in property_ids_list if property_id]
		try:
			# generate search_query and resultset & fields to be included in response 

			sp_include_fields= ["property_photo", "city", "location", "carpet_area", "amenities", "no_of_floors", 
								"price", "status","floor_no", "price_per_sq_ft", "property_id", "property_title", 
								"tag", "possession_status", "property_subtype_option", "unit_of_area", "property_age"]

			search_query = { "query":{ "ids":{ "values":property_ids_list } }  } 
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), 
																request_data.get("records_per_page",40), [], sp_include_fields)	
			
			# response data & pagination logic 

			append_shortlisted_tag(response_data)
			msg = "Shortlisted Property Found" if len(response_data) else "Shortlsited Property not found"
			return putil.init_pagination_and_response_generatrion(request_data, response_data, msg, total_records)

		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
		 	raise OperationFailed("Get Shortlisted Property Operation Failed")




def append_shortlisted_tag(response_data):
	for response in response_data:
		new_list = response.get("tag",[])
		new_list.append("Shortlisted")
		response["tag"] = new_list
		if response.get("amenities", ""):
			response["amenities"] = [ amenity for amenity in response.get("amenities") if amenity.get("status") == "Yes"]






"""  Get properties which are posted by particular user only  """


def get_user_properties(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		search_query =  { "query": { "match":{ "posted_by":request_data.get("user_id") } } }
		try:

			# fields_to_be_excluded from response and resultset generation 

			include_list = ["property_photo", "city", "location", "carpet_area", "amenities", "no_of_floors", "price", "status",
					"floor_no", "price_per_sq_ft", "property_id", "property_title", "tag", "possession_status", "property_subtype_option"]
			
			es = ElasticSearchController()
			response_data, total_records  = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40), [], include_list)
			response_data = check_for_shortlisted_property(response_data, request_data.get("user_id"))
			putil.show_amenities_with_yes_status(response_data)

			# response data & pagination logic

			msg = "User Property Found" if len(response_data) else "User Property not found"
			return putil.init_pagination_and_response_generatrion(request_data, response_data, msg, total_records)

		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Get User Properties Operation Failed")



def check_for_shortlisted_property(response_data, user_id):
	short_prop = frappe.db.get_values("Shortlisted Property",{"user_id":user_id, "status":"Active"}, "property_id" ,as_dict=True)
	short_prop = [sp.get("property_id") for sp in short_prop if sp]
	for response in response_data:
		if response.get("property_id") in short_prop:
			new_list = response.get("tag",[])
			new_list.append("Shortlisted")
			response["tag"] = new_list
	return response_data		





def share_property(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		user_name = frappe.db.get_value("User", {"user_id":request_data.get("user_id")}, ["first_name", "last_name"],as_dict=True)
		putil.validate_property_data(request_data, ["comments", "email_id"])		
		try:
			property_ids_list = {  comment.get("property_id"):comment.get("comment","")  for comment in request_data.get("comments") if comment.get("property_id")}
			search_query = { "query":{ "ids":{ "values":property_ids_list.keys() } }} 
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40))				
			if response_data:
				for response in response_data:
					response["comments"] = property_ids_list.get(response.get("property_id"),"")
				args = { "title":"Property Shared by  {0}".format(email) , "property_data":response_data ,"first_name":user_name.get("first_name"), "last_name":user_name.get("last_name")}
				send_email(request_data.get("email_id"), "Propshikari properties shared with you", "/templates/share_property_template.html", args)
				return { "operation":"Share", "message":"Property Shared"}
			else:
				raise DoesNotExistError("Property Id does not exists in elastic search")
		except frappe.OutgoingEmailError:
			raise OutgoingEmailError("Email can not be sent,Outgoing email error")
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Share Property Operation Failed")




def send_email(email, subject, template, args):
	frappe.sendmail(recipients=email, sender=None, subject=subject,
			message=frappe.get_template(template).render(args))



def get_property_images(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		if not request_data.get("property_id"):
			raise MandatoryError("Property Id not provided")
		try:
			es = ElasticSearchController()
			response = es.search_document_for_given_id("property",request_data.get("property_id"),[],["full_size_images", "thumbnails"])
			return { "operation":"Search", "message":"Property Images Found" if response else "Property Images Not Found", "user_id":request_data.get("user_id"), "data":response }
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)	
		except Exception,e:
			raise OperationFailed("Get Property Images Operation Failed")



def update_property_status(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data, ["property_id"])
		putil.validate_property_status(request_data.get("property_status"))	
		try:
			search_query = {"doc":{ "status":request_data.get("property_status") }}
			es = ElasticSearchController()
			response = es.update_docuemnt("property", request_data.get("property_id"), search_query)
			return {"operation":"Update" , "message":"User property status changed" if response else "Property Status not changed", "user_id":request_data.get("user_id")}
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)	
		except Exception,e:
			raise OperationFailed("Update Property Status Operation Failed")



def get_similar_properties(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data, ["request_type", "id"])
		search_dict = {"property_id":get_search_query_of_property_id ,"request_id":get_search_query_of_request_id}
		if request_data.get("request_type") not in ["property_id", "request_id"]:
			raise InvalidDataError("Request type contains Invalid Data")
		search_query, uom = search_dict.get(request_data.get("request_type"))(request_data)
		try:
			
			sp_include_fields = ["property_photo", "property_id", "location", "address",
			                      "city", "carpet_area", "price","property_title"]
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",4), [], sp_include_fields)
			uom = "Sq.Ft." if uom not in ["Sq.Ft.", "Acres", "Hectares"] else uom
			putil.convert_area_according_to_uom(response_data, uom)
			response_msg = "Similar Property Found" if response_data else "Similar property not found"
			return {
						"operation":"Search", 
						"message":response_msg ,
						"total_records":len(response_data),
						"data":response_data, 
						"user_id":request_data.get("user_id")
					}
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Get Similar property Operation Failed")	 


def get_search_query_of_property_id(request_data):
	try:
		es = ElasticSearchController()
		response = es.search_document_for_given_id("property",request_data.get("id"))		
		search_query = putil.generate_search_query_from_property_data(response)
		return search_query, "Sq.Ft."
	except elasticsearch.TransportError:
		raise DoesNotExistError("Property Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)	


def get_search_query_of_request_id(request_data):
	try:
		es = ElasticSearchController()
		response = es.search_document_for_given_id("request",request_data.get("id"),[],["search_query", "unit_of_area"])
		search_query = ast.literal_eval(response.get("search_query").encode("utf8"))
		return search_query, response.get("unit_of_area")
	except elasticsearch.TransportError:
		raise DoesNotExistError("Request Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)		



		

def get_alerts(request_data):
	
	"""
		Get property alerts based on two types
		 1. Check if alert is already set against that user else
		 2. Check for last search request & based on that search request
		    show properties to user. 
	"""

	request_data = json.loads(request_data)
	email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	alert = frappe.db.sql("""	select * from `tabAlerts` where user_id='{0}' 
								order by creation desc limit 1""".format(request_data.get("user_id")),as_dict=1)
	try:
		if alert:
			property_search_query, uom = get_alerts_based_on_alert_doctype(alert)
		else:
			property_search_query, uom = get_alerts_based_on_last_request(request_data, email)
		
		# fields to be included in response and resultset generation

		include_fields_list = ["property_id", "property_title", "price", "property_photo", "location", 
								"city", "carpet_area", "unit_of_area", "posted_datetime", "modified_datetime"]		
		es = ElasticSearchController()
		response_data, total_records = es.search_document(["property"], property_search_query, request_data.get("page_number",1), 
										request_data.get("records_per_page",40), [], include_fields_list)
		putil.convert_area_according_to_uom(response_data, uom)
		response_data = modify_alert_resultset(response_data, request_data.get("user_id"))

		#  response generation and pagination logic 

		msg = "Property Found" if response_data else "Property not found"
		return putil.init_pagination_and_response_generatrion(request_data, response_data, msg, total_records)

	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)
	except Exception,e:
		raise e





def get_alerts_based_on_alert_doctype(alert):
	
	"""
		Generate search query from alert set by user &
		check for properties which are posted after creation date of alert only.  
	"""

	uom = alert[0].get("unit_of_area")
	alert[0]["unit_of_area"] = "Sq.Ft." if uom not in ["Sq.Ft.", "Acres", "Hectares"] else uom
	putil.convert_area_to_sqft_for_search(alert[0])
	property_search_query = putil.generate_search_query(alert[0])
	new_query = property_search_query.get("query").get("bool").get("must")
	new_query.append({
					    "range" : {
					        "modified_datetime" : {
					            "gte": alert[0].get("creation").strftime("%Y-%m-%d %H:%M:%S"),
					        }
					    }
					})
	property_search_query["query"]["bool"]["must"] = new_query
	return property_search_query, alert[0].get("unit_of_area")




def get_alerts_based_on_last_request(request_data, email):
	
	"""
		Generate search query from last search request of that user &
		check for properties which are posted from last month only. 
	"""

	try:
		search_query = {	
							"sort": [{ "posted_datetime": { "order": "desc" }}],
							"query":{ "bool":{ "must":[ {"match":{ "user_id":request_data.get("user_id")  } } ] }    } 
						}						
		es = ElasticSearchController()
		response_data, total_records = es.search_document(["request"], search_query, 1, 1)
		if response_data:
			last_month_date = add_months(datetime.datetime.now() ,-1).strftime("%Y-%m-%d %H:%M:%S")
			property_search_query = response_data[0].get("search_query")
			property_search_query = ast.literal_eval(property_search_query.encode("utf8"))
			new_query = property_search_query.get("query").get("bool").get("must")
			new_query.append({
								    "range" : {
								        "modified_datetime" : {
								            "gte":last_month_date,
								        }
								    }
								})
			property_search_query["query"]["bool"]["must"] = new_query
			uom = response_data[0].get("unit_of_area")
			uom = "Sq.Ft." if uom not in ["Sq.Ft.", "Acres", "Hectares"] else uom
			return property_search_query,  uom
		else:
			raise OperationFailed("No Alerts and Request Id found against User {0}".format(email))
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)




def modify_alert_resultset(response_data, user_id):
	property_ids = frappe.db.get_values("Property Alerts", {"user_id":user_id}, "property_id",as_dict=True)
	property_ids = [ prop.get("property_id") for prop in property_ids if prop.get("property_id")]
	new_property, modified_property, viewed_property = [], [], []
	modified_response = []
	for response in response_data:
		if response.get("property_id") not in property_ids:
			if response.get("posted_datetime") == response.get("modified_datetime"):
				response["alert_property_status"] = "New"
				pop_datetime_from_response(response)
				new_property.append(response)
			else:
				response["alert_property_status"] = "Modified"
				pop_datetime_from_response(response)
				modified_property.append(response)	
		else:
			response["alert_property_status"] = "Viewed"
			pop_datetime_from_response(response)
			viewed_property.append(response)
	modified_response.extend(new_property)
	modified_response.extend(modified_property)
	modified_response.extend(viewed_property)
	return modified_response		


def pop_datetime_from_response(response):
	response.pop("posted_datetime",None)
	response.pop("modified_datetime",None)





""" Get Basic Property details & location details.   """


def get_location_details_for_map(request_data):
	request_data = json.loads(request_data)
	email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	putil.validate_property_data(request_data, ["request_id"])
	try:
		es = ElasticSearchController()
		response = es.search_document_for_given_id("request",request_data.get("request_id"),[],
														["search_query", "unit_of_area", "adv_search_query"])
		search_query = ast.literal_eval(response.get("adv_search_query").encode("utf8"))
		uom = response.get("unit_of_area")

		include_fields = ["property_title", "property_id", "location", "property_subtype_option",
			                      "operation", "carpet_area", "price", "geo_location_lat", "geo_location_lon" ]

		size = get_count_of_property_records(es)            
		response_data, total_records = es.search_document(["property"], search_query, 1, size, [], include_fields)
		uom = "Sq.Ft." if uom not in ["Sq.Ft.", "Acres", "Hectares"] else uom
		putil.convert_area_according_to_uom(response_data, uom)
		response_msg = "User Property Found" if response_data else "User property not found"
		return {
					"operation":"Search",
					"user_id":request_data.get("user_id"),
					"message":response_msg,
					"data":response_data
				}
	except elasticsearch.TransportError:
		raise DoesNotExistError("Request Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)


def get_count_of_property_records(es):
	search_query = { "query": { "match_all":{} } }
	response_data, total_records = es.search_document(["property"], search_query, 1)
	return total_records



def get_total_owner_count():
	search_query =  get_owner_count_query()
	es = ElasticSearchController()
	response_data = es.get_aggregated_data(["property"], search_query)
	return response_data.get("owner_count", {}).get("value", 0.0)


def get_owner_count_query():
	return  { "query": 
					{ "bool": {
		            		"must": [
		               				{
		                   			"match": {
		                      			"listed_by": "Owner"
		                   				}
		               				}
		            			]
		        			}
		    			},
		    			"aggs":{
					      "owner_count":{
					            "cardinality" : {
					                "field" : "posted_by"
					            }
					      }  
		    		}
			}

















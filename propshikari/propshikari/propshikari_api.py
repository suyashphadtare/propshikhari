from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, flt
from elastic_controller import ElasticSearchController
from frappe.utils import add_days, getdate, now, nowdate ,random_string ,add_months, date_diff
from property_masters import create_lead_from_userid, make_conditions_for_duplicate_group
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





def post_property(data):
	if data:
		try:
			old_data = json.loads(data) if isinstance(data,unicode) else old_data = data
			email = putil.validate_for_user_id_exists(old_data.get("user_id"))
			subs_doc = putil.validate_for_postings_available(email)
			putil.convert_area_to_sqft_for_posting(old_data)
			data = putil.validate_property_posting_data(old_data,"property_json/property_mapper.json")
			putil.validate_property_status(data.get("status"))
			custom_id = "PROP-"  + cstr(int(time.time())) + '-' +  cstr(random.randint(10000,99999))
			data["property_id"] = custom_id
			meta_dict = add_meta_fields_before_posting(old_data)
			data.update(meta_dict)
			# return store_property_photos_in_propshikari(old_data.get("property_photos"),custom_id)
			property_photo_url_dict = store_property_photos_in_propshikari(old_data.get("property_photos"),custom_id)
			data["full_size_images"] = property_photo_url_dict.get("full_size",[])
			data["thumbnails"] = property_photo_url_dict.get("thumbnails",[])
			data["property_photo"] = property_photo_url_dict.get("thumbnails")[0] if len(property_photo_url_dict.get("thumbnails")) else ""
			data["posted_by"] = old_data.get("user_id")
			data["user_email"] = email
			data["posting_date"] = data.get("posting_date") if data.get("posting_date") else data["creation_date"]
			data["amenities"] = putil.prepare_amenities_data(data.get("amenities",""), data.get("property_type"))
			data["flat_facilities"] = putil.prepare_flat_facilities_data(data.get("flat_facilities",""), data.get("property_type"))
			data["possession_status"] = "Immediate" if data.get("possession") else data.get("possession_date")
			data.pop("possession_date", None)
			es = ElasticSearchController()
			response_data = es.index_document("property",data, custom_id)
			if subs_doc and response_data.get("created"):
				subs_doc.posted = cint(subs_doc.posted) + 1
				subs_doc.save(ignore_permissions=True)
			subscription = putil.get_subscriptions(email)
			response_msg = "Property posted successfully" if response_data.get("created",False) else "Property posting failed" 
			return {"operation":"Create", "message":response_msg, "property_id":response_data.get("_id"), "user_id":old_data.get("user_id"),"data":{"subscriptions":subscription}}	
		except elasticsearch.RequestError,e:
			raise ElasticInvalidInputFormatError(e.error)
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise e	



def search_property(data):
	if data:
		property_data = json.loads(data)
		property_data = putil.validate_property_posting_data(property_data, "property_json/property_search.json")
		putil.isolate_city_from_location(property_data)
		putil.convert_area_to_sqft_for_search(property_data)
		try:	
			
			# generate search query & result generation & list of fields which should be excluded.

			exclude_list = ["agent_name", "agent_no", "contact_no", "contact_person", "created_by", 
				"modified_by", "creation_date", "modified_date", "posted_datetime", "modified_datetime"]

			search_query = putil.generate_search_query(property_data)
			# return {"search_query":search_query}
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, property_data.get("page_number",1), property_data.get("records_per_page",40), exclude_list)
			
			# post property-search operation

			if not property_data.get("request_id"):	
				request_id = store_request_in_elastic_search(property_data, search_query, "Property Search")
			if property_data.get("user_id") != "Guest":				
				response_data = check_for_shortlisted_property(response_data,property_data.get("user_id"))
			response_data = putil.get_date_diff_from_posting(response_data)
			putil.convert_area_according_to_uom(response_data, property_data.get("unit_of_area", "Sq.Ft"))
			
			# response data & pagination logic

			response_msg = "Property found for specfied criteria" if len(response_data) else "Property not found"
			from_record = ( property_data.get("page_number",1) - 1 ) * cint( property_data.get("records_per_page",40) ) + 1
			no_of_pages = math.ceil( flt(total_records) / property_data.get("records_per_page",40))
			to_record = (from_record +  len(response_data) - 1) if response_data else ( from_record + property_data.get("records_per_page",40) - 1)
			return {
						"operation":"Search", 
						"message":response_msg ,
						"total_records":total_records, 
						"request_id":property_data.get("request_id") if property_data.get("request_id") else request_id, 
						"records_per_page":property_data.get("records_per_page",40),
						"from_record":from_record ,
						"to_record":to_record,
						"data":response_data, 
						"user_id":property_data.get("user_id"), 
						"no_of_pages":no_of_pages
					}
		
		except elasticsearch.RequestError,e:
			raise ElasticInvalidInputFormatError(e.error)
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise e


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
		city_list =  frappe.db.sql("select city_name,name as city_nm,state_name from `tabCity` ",as_dict=True)
		address_list = []
		for state in state_list:
			address_dict = OrderedDict()
			address_dict["state_name"] = state.get("state_name")
			address_dict["cities"] = [  { "city_name":city.get("city_name"), "location":frappe.db.sql(" select area as location_name , lattitude as geo_location_lat ,longitude as geo_location_lon from `tabArea` where city_name='{0}'  and state_name='{1}'".format(city.get("city_nm"), state.get("state_name")),as_dict=True) }  for city in city_list if city.get("state_name") == state.get("state_name")] 
			address_list.append(address_dict)
		state_dict = {"states":address_list}	
		return { "operation":"search", "message":"States Information Found", "user_id":request_data.get("user_id"), "data":state_dict}
	except Exception,e:
		raise GetStateInfoOperationFailed("Get State info Operation Failed")





def store_request_in_elastic_search(property_data, search_query, request_type):
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
		"request_type":request_type

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
	property_url_dict = {"full_size":[], "thumbnails":[]}
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
			group_search_conditions = make_conditions_for_duplicate_group(response)
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

			search_query = { "query":{ "match":{ "tag":request_data.get("tag") } }  } 
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40),exclude_list)	
			response_msg = "Property found for specfied criteria" if len(response_data) else "Property not found"
			from_record = (request_data.get("page_number",1) - 1) * cint(request_data.get("records_per_page",40)) + 1
			to_record = from_record +  len(response_data) - 1 if response_data else from_record + request_data.get("records_per_page",40) - 1
			no_of_pages = math.ceil( flt(total_records) / request_data.get("records_per_page",40))
			return {
						"operation":"Search", 
						"message":response_msg ,
						"total_records":total_records, 
						"records_per_page":request_data.get("records_per_page",40),
						"from_record":from_record ,
						"to_record": to_record,
						"data":response_data, 
						"user_id":request_data.get("user_id"), 
						"tag":request_data.get("tag"),
						"no_of_pages":no_of_pages
					}
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
			new_response = { "contact_no": response.get("contact_no"), "contact_person":response.get("contact_person")}
			# create_lead_from_userid(request_data, email, response)
			return {	
						"operation":"Search",
						"message":"Contact Details found" if len(new_response) else "Contact Details Not Found", 
						"user_id":request_data.get("user_id"), 
						"data":new_response
					}
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except Exception,e:
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
					"floor_no", "price_per_sq_ft", "property_id", "property_title", "tag"]

			search_query = { "query":{ "ids":{ "values":property_ids_list } }  } 
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40), [], sp_include_fields)	
			
			# response data & pagination logic 

			for response in response_data:
				new_list = response.get("tag",[])
				new_list.append("Shortlisted")
				response["tag"] = new_list
			response_msg = "Shortlisted Property Found" if len(response_data) else "Shortlsited Property not found"
			from_record = (request_data.get("page_number",1) - 1) * cint(request_data.get("records_per_page",40)) + 1
			to_record = from_record +  len(response_data) - 1 if response_data else from_record + request_data.get("records_per_page",40) - 1
			no_of_pages = math.ceil( flt(total_records) / request_data.get("records_per_page",40))
			return {
						"operation":"Search", 
						"message":response_msg ,
						"total_records":total_records, 
						"records_per_page":request_data.get("records_per_page",40),
						"from_record":from_record ,
						"to_record": to_record,
						"no_of_pages":no_of_pages,
						"data":response_data, 
						"user_id":request_data.get("user_id")
					}
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
		 	raise OperationFailed("Get Shortlisted Property Operation Failed")





"""  Get properties which are posted by particular user only  """


def get_user_properties(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		search_query =  { "query": { "match":{ "posted_by":request_data.get("user_id") } } }
		try:

			# fields_to_be_excluded from response and resultset generation 

			include_list = ["property_photo", "city", "location", "carpet_area", "amenities", "no_of_floors",
					"floor_no", "price_per_sq_ft", "property_id", "property_title", "tag"]
			
			es = ElasticSearchController()
			response_data, total_records  = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40), [], include_list)
			response_data = check_for_shortlisted_property(response_data, request_data.get("user_id"))
			
			# response data & pagination logic

			response_msg = "User Property Found" if len(response_data) else "User Property not found"
			from_record = (request_data.get("page_number",1) - 1) * cint(request_data.get("records_per_page",40)) + 1 
			to_record = from_record +  len(response_data) - 1 if response_data else from_record + request_data.get("records_per_page",40) - 1
			no_of_pages =  math.ceil( flt(total_records) / request_data.get("records_per_page",40))
			return {
						"operation":"Search",
						"message":response_msg ,
						"total_records":total_records, 
						"records_per_page":request_data.get("records_per_page",40),
						"from_record":from_record ,
						"to_record": to_record,
						"no_of_pages":no_of_pages,
						"data":response_data,
						"user_id":request_data.get("user_id")
					}
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
		user_name = frappe.db.get_value("User", email, ["first_name", "last_name"],as_dict=True)
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
			                      "city", "carpet_area", "price" ]
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",4), [], sp_include_fields)
			uom = "Sq.Ft" if uom not in ["Sq.Ft", "Acres", "Hectares"] else uom
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
		return search_query, "Sq.Ft"
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

	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		alert = frappe.db.sql("select * from `tabAlerts` where user_id='{0}' order by creation desc limit 1".format(request_data.get("user_id")),as_dict=1)
		try:
			if alert:
				property_search_query, uom = get_alerts_based_on_alert_doctype(alert)
			else:
				property_search_query, uom = get_alerts_based_on_last_request(request_data, email)
			
			# fields to be included in response and resultset generation

			include_fields_list = ["property_id", "property_title", "price", "property_photo", "location", "city", "carpet_area", "unit_of_area"]		
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], property_search_query, request_data.get("page_number",1), request_data.get("records_per_page",40), [], include_fields_list)
			putil.convert_area_according_to_uom(response_data, uom)

			#  response generation and pagination logic 

			from_record =  ((request_data.get("page_number",1) - 1) * cint(request_data.get("records_per_page",40)) + 1 )
			to_record = from_record +  len(response_data) - 1 if response_data else from_record + request_data.get("records_per_page",40) - 1
			response_msg = "Property Found" if response_data else "Property not found"
			no_of_pages = math.ceil(flt(total_records)/request_data.get("records_per_page",40))
			return {
						"operation":"Search", 
						"message":response_msg ,
						"total_records":total_records,
						"records_per_page":request_data.get("records_per_page",40),
						"from_record":from_record ,
						"to_record":to_record,
						"data":response_data, 
						"user_id":request_data.get("user_id"), 
						"no_of_pages":no_of_pages
					}
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
	alert[0]["unit_of_area"] = "Sq.Ft" if uom not in ["Sq.Ft", "Acres", "Hectares"] else uom
	putil.convert_area_to_sqft_for_search(alert[0])
	property_search_query = putil.generate_search_query(alert[0])
	new_query = property_search_query.get("query").get("bool").get("must")
	new_query.append({
					    "range" : {
					        "posted_datetime" : {
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
								        "posted_datetime" : {
								            "gte":last_month_date,
								        }
								    }
								})
			property_search_query["query"]["bool"]["must"] = new_query
			uom = response_data[0].get("unit_of_area")
			uom = "Sq.Ft" if uom not in ["Sq.Ft", "Acres", "Hectares"] else uom
			return property_search_query,  uom
		else:
			raise OperationFailed("No Alerts and Request Id found against User {0}".format(email))
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)		





def reindex_data(data):
	try:
		request_data = json.loads(data)
		es = Elasticsearch()
		helpers.reindex(client=es, source_index=request_data.get("source"), target_index=request_data.get("target"))
		return {"data":"sucess"}
	except elasticsearch.ElasticsearchException,e:
		return {"new":dir(e),"mes":e.message, "error":e.errors}



def get_all_property_data(data):
	es = ElasticSearchController()
	response_data, total_records = es.search_document(["property"], "", 1, 1000)
	return {"total_records":total_records, "data":response_data}



def update_tags_of_property(data):
	request_data = json.loads(data)
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	user_data = frappe.db.get_value("User",{"name":user_email}, "user_type", as_dict=True)
	if user_data.get("user_type") == "System User":
		try:
			es = ElasticSearchController()
			response = es.search_document_for_given_id("property",request_data.get("property_id"), [], [])
			get_tag_and_calculate_discounted_price(response, request_data)
			get_modified_datetime(response, user_email)	
			search_query = search_query = {"doc": response }
			es = ElasticSearchController()
			update_response = es.update_docuemnt("property", request_data.get("property_id"), search_query)
			return {	
						"operation":"update", 
						"user_id":request_data.get("user_id"), 
						"message":"Property Tags Updated Successfully"
					}
		except elasticsearch.TransportError:
			raise DoesNotExistError("Property Id does not exists")
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)					
	else:
		raise MandatoryError("User {0} not allowed to update property tags.".format(user_email))




def get_tag_and_calculate_discounted_price(response, request_data):
	property_tags = set(response.get("tag", []))
	new_tags = set(request_data.get("tags", []))
	new_tags = property_tags | new_tags
	response["tag"] = list(new_tags)
	if request_data.get("discount_percentage",0.0):
		discount_price = response.get("price",0.0) - (  response.get("price",0.0) * request_data.get("discount_percentage",0.0) / 100 )
		response["discounted_price"] = discount_price



def get_modified_datetime(response, user_email):
	response["modified_datetime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	response["modified_date"] = datetime.datetime.now().strftime("%d-%m-%Y")
	response["modified_by"]	= user_email




def get_property_details(data):
	request_data = json.loads(data)
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	include_list = request_data.get("fields",[])
	try:
		es = ElasticSearchController()
		response = es.search_document_for_given_id("property",request_data.get("property_id"), [], include_list)
		return {"opeartion":"Search", "message":"Property details Found", "data":response}
	except elasticsearch.TransportError:
		raise DoesNotExistError("Property Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)	












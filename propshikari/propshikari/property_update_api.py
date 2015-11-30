from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, flt
from elastic_controller import ElasticSearchController
from frappe.utils import add_days, getdate, now, nowdate ,random_string ,add_months, date_diff
from property_masters import create_lead_from_userid, make_conditions_for_duplicate_group
from percent_completion import project_mandatory_fields, property_mandatory_fields
from frappe.auth import _update_password
from propshikari_api import store_property_photos_in_propshikari, get_count_of_property_records, send_email
import property_utils as putil
import json ,ast
import datetime
import os
import elasticsearch
from elasticsearch import Elasticsearch
from elasticsearch import helpers
from api_handler.api_handler.exceptions import *






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
	user_data = frappe.db.get_value("User",{"email":user_email}, "user_type", as_dict=True)
	if user_data.get("user_type") == "System User":
		try:
			es = ElasticSearchController()
			response = es.search_document_for_given_id("property",request_data.get("property_id"), [], [])
			get_tag_and_calculate_discounted_price(response, request_data)
			get_modified_datetime(response, user_email)	
			search_query = search_query = {"doc": response }
			es = ElasticSearchController()
			update_response = es.update_docuemnt("property", request_data.get("property_id"), search_query)
			es = ElasticSearchController()
			es.refresh_index()
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



def update_property_fields(data):
	request_data = json.loads(data)
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	try:
		field_dict = get_updated_fields_dict(request_data, user_email)
		search_query = {"doc": field_dict }
		es = ElasticSearchController()
		update_response = es.update_docuemnt("property", request_data.get("property_id"), search_query)
		return {"opeartion":"Update", "message":"Property details Updated"}
	except elasticsearch.TransportError:
		raise DoesNotExistError("Property Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)


def get_updated_fields_dict(request_data, user_email):
	update_dict = {}
	update_dict.update(request_data.get("fields"))
	get_modified_datetime(update_dict, user_email)
	return update_dict


def get_amenities_data():
	return {"data": frappe.db.get_all("Amenities", ["amenity_name","icon"])}

def get_flat_data():
	return {"data": frappe.db.get_all("Flat Facilities", ["facility","icon"])}



""" 
	Update property related fields.
	Format will be {"property_id":"PROP-100000231-2312", fields:{} }
	fields dict will contain key-value pairs of property fields which should be updated.
	amenities & flat_facilities should be in list format.
	for property photo upload , existing list of full size images & thumbnails is necessary if 
	images already exists in elasticsearch. & format of property photo data will be same as
	property posting eg. { "property_photos":[{"file_name":"", "file_data":"", "file_ext":"" }]  } 

"""


def update_property(data):
	request_data = json.loads(data)
	user_email = putil.validate_for_user_id_exists(request_data.get("fields").get("user_id"))
	try:
		field_dict = putil.validate_property_posting_data(request_data.get("fields"), "property_json/property_update.json")
		get_modified_datetime(field_dict, user_email)
		update_property_photos(field_dict, request_data.get("fields"), request_data.get("property_id"))
		field_dict["possession_status"] = "Immediate" if field_dict.get("possession") else field_dict.get("possession_date")
		search_query = {"doc": field_dict }
		es = ElasticSearchController()
		update_response = es.update_docuemnt("property", request_data.get("property_id"), search_query)
		mandatory_list = property_mandatory_fields.get(field_dict.get("property_type"),[""])
		percent_script = get_percent_completion_script(mandatory_list)
		percent_response = es.update_docuemnt("property", request_data.get("property_id"), percent_script)
		return {"opeartion":"Update", "message":"Property details Updated"}
	except elasticsearch.TransportError:
		raise DoesNotExistError("Property Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)
	except Exception,e:
		print frappe.get_traceback()
		raise e




def update_property_photos(field_dict, property_fields, custom_id):
	if property_fields.get("property_photos"):
		photo_dict = store_property_photos_in_propshikari(property_fields.get("property_photos"), custom_id)
		photo_dict.get("full_size").extend(property_fields.get("full_size_images", []))
		photo_dict.get("thumbnails").extend(property_fields.get("thumbnails", []))
		field_dict["full_size_images"] = photo_dict.get("full_size")
		field_dict["thumbnails"] = photo_dict.get("thumbnails")
		field_dict["property_photo"] = field_dict.get("thumbnails")[0] if len(field_dict.get("thumbnails")) else ""



def get_agent_properties(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		search_query =  { "query": { "match":{ "posted_by":request_data.get("user_id") } } }
		try:
			
			es = ElasticSearchController()
			size = get_count_of_property_records(es)
			response_data, total_records  = es.search_document(["property"], search_query, request_data.get("page_number",1), size)

			# response data & pagination logic

			msg = "User Property Found" if len(response_data) else "User Property not found"
			return putil.init_pagination_and_response_generatrion(request_data, response_data, msg, total_records)

		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Get Agent Properties Operation Failed")





def get_property_of_given_id(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		try:
			exclude_list = ["agent_name", "agent_no", "created_by", 
							"modified_by", "creation_date", "modified_date", "posted_datetime", "modified_datetime"]

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


def get_all_properties(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		search_query =  { }
		try:
			include_list = ["property_id", "property_title", "property_photo"]
			es = ElasticSearchController()
			size = get_count_of_property_records(es)
			response_data, total_records  = es.search_document(["property"], search_query, request_data.get("page_number",1), size, [], include_list)

			# response data & pagination logic

			msg = "User Property Found" if len(response_data) else "User Property not found"
			return putil.init_pagination_and_response_generatrion(request_data, response_data, msg, total_records)

		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Get All Properties Operation Failed")


def get_all_projects(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		search_query =  { }
		try:
			include_list = ["project_id", "overview"]
			es = ElasticSearchController()
			size = get_count_of_project_records(es)
			response_data, total_records  = es.search_document(["project"], search_query, request_data.get("page_number",1), size, [], include_list)

			# response data & pagination logic

			msg = "Projects Found" if len(response_data) else "Projects not found"
			return putil.init_pagination_and_response_generatrion(request_data, response_data, msg, total_records)

		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise OperationFailed("Get All Projects Operation Failed")



def get_count_of_project_records(es):
	search_query = { "query": { "match_all":{} } }
	response_data, total_records = es.search_document(["project"], search_query, 1)
	return total_records



def share_property_to_agents(request_data):
	if request_data:
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		user_name = frappe.db.get_value("User", {"user_id":request_data.get("user_id")}, ["first_name", "last_name"],as_dict=True)
		putil.validate_property_data(request_data, ["comments", "email_id"])		
		try:
			property_ids_list = {  comment.get("property_id"):[comment.get("comment",""),comment.get("prop_through", "")]  for comment in request_data.get("comments") if comment.get("property_id")}
			search_query = { "query":{ "ids":{ "values":property_ids_list.keys() } }} 
			es = ElasticSearchController()
			response_data, total_records = es.search_document(["property"], search_query, request_data.get("page_number",1), request_data.get("records_per_page",40))				
			if response_data:
				for response in response_data:
					response["comments"] = property_ids_list.get(response.get("property_id"),"")[0]
					response["property_through"] = property_ids_list.get(response.get("property_id"),"")[1]
				args = { "title":"Property Shared by  {0}".format(email) , "property_data":response_data ,"first_name":user_name.get("first_name"), "last_name":user_name.get("last_name")}
				send_email(request_data.get("email_id"), "Propshikari properties shared with you", "/templates/share_agents_property.html", args)
				return { "operation":"Share", "message":"Property Shared Successfully"}
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





def update_project(request_data):
	user_email = putil.validate_for_user_id_exists(request_data.get("fields").get("user_id"))
	try:
		field_dict = putil.validate_property_posting_data(request_data.get("fields"), "property_json/project_post_mapper.json")
		get_modified_datetime(field_dict, user_email)
		
		es = ElasticSearchController()
		update_project_photos(field_dict, request_data.get("fields"), request_data.get("project_id"), es)
		field_dict["possession_status"] = "Immediate" if field_dict.get("possession") else field_dict.get("possession_date")
		search_query = {"doc": field_dict }
		update_response = es.update_docuemnt("project", request_data.get("project_id"), search_query)
		percent_script = get_percent_completion_script(project_mandatory_fields)
		per_response = es.update_docuemnt("project", request_data.get("project_id"), percent_script)
		return {"opeartion":"Update", "message":"Project details Updated"}
	except elasticsearch.TransportError:
		raise DoesNotExistError("Project Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)
	except Exception,e:
		print frappe.get_traceback()
		raise e



def add_photo_to_properties(field_dict, project_id, es):
	properties = get_properties_against_project_id(es, project_id)
	start_property_photo_addition(es, properties, field_dict)	



def start_property_photo_addition(es, properties, field_dict):
	prop_update_list = []
	for prop in properties:
		full_size_img = field_dict.get("full_size_images",[])
		thumbnails = field_dict.get("thumbnails",[])
		prop_photo = field_dict.get("project_photo","")
		update_query = get_property_photo_add_query(prop, full_size_img, thumbnails, prop_photo)
		prop_update_list.append(update_query)				
	response = es.bulk_upload(prop_update_list)



def update_project_photos(field_dict, property_fields, custom_id, es):
	if property_fields.get("project_photos"):
		photo_dict = store_property_photos_in_propshikari(property_fields.get("project_photos"), custom_id)
		photo_dict.get("full_size").extend(property_fields.get("full_size_images", []))
		photo_dict.get("thumbnails").extend(property_fields.get("thumbnails", []))
		field_dict["full_size_images"] = photo_dict.get("full_size")
		field_dict["thumbnails"] = photo_dict.get("thumbnails")
		field_dict["project_photo"] = field_dict.get("thumbnails")[0] if len(field_dict.get("thumbnails")) else ""
		add_photo_to_properties(field_dict, custom_id, es)



def upadate_project_status(request_data):
	email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	putil.validate_property_data(request_data, ["project_id"])
	try:
		search_query = {"doc":{ "status":request_data.get("project_status") }}
		es = ElasticSearchController()
		response = es.update_docuemnt("project", request_data.get("project_id"), search_query)
		return {
				"operation":"Update" , 
				"message":"Project status changed" if response else "Project Status not changed", 
				"user_id":request_data.get("user_id")
				}
	except elasticsearch.TransportError:
		raise DoesNotExistError("Project Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)	
	except Exception,e:
		raise OperationFailed("Update Project Status Operation Failed")



def get_project_details(request_data):
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	include_list = request_data.get("fields",[])
	try:
		es = ElasticSearchController()
		response = es.search_document_for_given_id("project",request_data.get("project_id"), [], include_list)
		return {"opeartion":"Search", "message":"Project details Found", "data":response}
	except elasticsearch.TransportError:
		raise DoesNotExistError("Project Id does not exists")
	except elasticsearch.ElasticsearchException,e:
		raise ElasticSearchException(e.error)



def delete_project_photo(doc, img_url):
	full, thumbnails, photo = init_for_photo_list_operation(doc, img_url)
	es = ElasticSearchController()
	search_query = {"doc":{ "full_size_images":full, "thumbnails":thumbnails, "project_photo":photo }}
	response = es.update_docuemnt("project", doc.get("project_id"), search_query)
	init_for_property_photo_update(es, img_url, doc.get("project_id"))
	return { 
				"message":"Project Photo deleted successfully",
				"full_size":','.join(full),
				"thumbnails":','.join(thumbnails),
				"photo":photo
			}




def init_for_photo_list_operation(doc ,img_url):
	thumbnails, full_size_list = get_new_photo_list(doc, img_url)
	prj_photo = doc.get("project_photo", "")
	prj_photo = "" if prj_photo == img_url else prj_photo
	delete_photo_from_propshikari(img_url)
	return full_size_list, thumbnails, prj_photo


def get_new_photo_list(doc, img_url):
	thumbnails = doc.get("thumbnails")
	thumbnails.remove(img_url)
	full_size_img_url = img_url.replace("thumbnail", "regular")
	full_size_list = doc.get("full_size_images")
	full_size_list.remove(full_size_img_url)
	return thumbnails, full_size_list      


def delete_photo_from_propshikari(thumbnail_url):
	thumbnail_index = thumbnail_url.find("files")
	thu_url = thumbnail_url[thumbnail_index:]
	img_path = frappe.get_site_path() + '/public/' + thu_url
	for path in [img_path , img_path.replace("thumbnail", "regular")]:
		if os.path.exists(path):
			os.remove(path)
		else:
			raise DoesNotExistError("Project Image not found")



def init_for_property_photo_update(es, img_url, project_id):
	properties = get_properties_against_project_id(es, project_id)
	start_property_photo_update(es, properties, img_url)



def start_property_photo_update(es, properties, img_url):
	prop_update_list = []
	for prop in properties:
		full_size_img = img_url.replace("thumbnail", "regular")
		update_query = get_update_query(prop, full_size_img, img_url)
		prop_update_list.append(update_query)				
	response = es.bulk_upload(prop_update_list)


def init_for_property_photo_list_operation(prop, img_url):
	thumbnails, full_size_list = get_new_photo_list(prop, img_url)
	prop_photo = prop.get("property_photo", "")
	prop_photo = "" if prop_photo == img_url else prop_photo
	return full_size_list, thumbnails, prop_photo




def get_properties_against_project_id(es, project_id):
	search_query = { "query": { "match": { "project_id": project_id } } }
	size = get_count_of_property_records(es)
	response_data, total_records = es.search_document(["property"], search_query, 1, size, [], 
										["thumbnails", "full_size_images", "property_photo", "property_id"])
	return response_data



def delete_property_photo(doc, img_url):
	full_size_img = img_url.replace("thumbnail", "regular")
	update_query = get_script_query(full_size_img, img_url)
	if not doc.get("project_id","") or (img_url.find("PROP")!= -1):
		delete_photo_from_propshikari(img_url)
	es = ElasticSearchController()	
	response = es.update_docuemnt("property", doc.get("property_id"), update_query)
	prop_dict = {"user_id":doc.get("user_id"), "sid":doc.get("sid"), "property_id":doc.get("property_id"), 
					"fields":["thumbnails", "full_size_images", "property_photo"]}
	prop_response = get_property_details(json.dumps(prop_dict))
	return { 
				"message":"Property Photo deleted successfully",
				"full_size":','.join(prop_response.get("data").get("full_size_images", [])),
				"thumbnails":','.join(prop_response.get("data").get("thumbnails", [])),
				"photo":prop_response.get("data").get("property_photo", [])
			}



def get_script_query(full_size_img, img_url):
	return {
		"script" : """	ctx._source.full_size_images -= full; ctx._source.thumbnails -= thumbnail; 
						if (ctx._source.property_photo == thumbnail){ctx._source.property_photo = new_photo }""", 
		"params" : {"full":full_size_img, "thumbnail":img_url, "new_photo":""}
	}	


def get_update_query(prop, full_size_img, img_url):
	return {  
		"_op_type": 'update',
		"_index": 'propshikari',
		"_type": 'property',
		"_id": prop.get("property_id"),
		"script" : """	ctx._source.full_size_images -= full; ctx._source.thumbnails -= thumbnail; 
						if (ctx._source.property_photo == thumbnail){ctx._source.property_photo = new_photo }""", 
		"params" : {"full":full_size_img, "thumbnail":img_url, "new_photo":""}
	}


def get_property_photo_add_query(prop, full_size_img, thumbnails, prop_photo):
	return {  
		"_op_type": 'update',
		"_index": 'propshikari',
		"_type": 'property',
		"_id": prop.get("property_id"),
		"script" : """	ctx._source.full_size_images += full; ctx._source.thumbnails += thumbnail; 
						if (! ctx._source.property_photo){ctx._source.property_photo = new_photo }""", 
		"params" : {"full":full_size_img, "thumbnail":thumbnails, "new_photo":prop_photo}
	}


def get_percent_completion_script(mandatory_list):
	return {
  				"script":"""
  							prop_fields=%s;
  							count = 0; 
  							for (prop in prop_fields){
  								if(ctx._source[prop]){
  									count += 1
  								};
  							};
  							ctx._source.percent_completion = ((count/%s)*100) as int 
  						"""%(mandatory_list, len(mandatory_list))
			}	
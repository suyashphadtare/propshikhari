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
import datetime
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
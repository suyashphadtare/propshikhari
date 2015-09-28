from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, flt
from elastic_controller import ElasticSearchController
from frappe.utils import add_days, getdate, now, nowdate ,random_string ,add_months
import property_utils as putil
from propshikari_api import store_request_in_elastic_search
import json ,ast
import time
import random
import datetime
import elasticsearch
import math
from api_handler.api_handler.exceptions import *




"""
	Get project of given id from elastic search.

"""

def get_project_of_given_id(request_data):
	request_data = json.loads(request_data)
	email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	if not request_data.get("project_id"):
		raise MandatoryError("Project id does not exists") 
	try:
		project_fields = ["project_id", "project_name", "project_type", "project_by", "project_subtype",
						   "property_details","website", "contact_no", "email_id", "contact_person", "project_photo"]
		es = ElasticSearchController()
		response = es.search_document_for_given_id("project", request_data.get("project_id"), [], project_fields)
		response["properties"]= {}
		for prop in response.get("property_details"):
			if not response["properties"].has_key(prop.get("property_type")):
				response["properties"][prop.get("property_type")] = { "option":{ prop.get("property_subtype_option"):{ "count":prop.get("count"), "area":prop.get("carpet_area")} }}
			else:
				response["properties"][prop.get("property_type")]["option"][prop.get("property_subtype_option")] = 	{ "count":prop.get("count"), "area":prop.get("carpet_area")} 
		response.pop("property_details")
		return {"operation":"Search", "message":"Project details found" if len(response) else "Project Not Found", "user_id":request_data.get("user_id"), "data":response}
	except elasticsearch.TransportError:
		raise DoesNotExistError("Project Id does not exists")
	except Exception,e:
		raise OperationFailed("Get Project Operation Failed")






"""  
	Search projects according to given criterias like
	project type , project subtype , location, area, price etc. 

"""


def search_project(request_data):
	if request_data:
		project_data = json.loads(request_data)
		project_data = putil.validate_property_posting_data(project_data,"property_json/project_search.json")
		putil.isolate_city_from_location(project_data)
		search_query = putil.generate_project_search_query(project_data)
		try:

			exclude_list = ["agent_name", "agent_no", "contact_no", "contact_person", "created_by", 
				"modified_by", "creation_date", "modified_date", "posted_datetime", "modified_datetime"]

			es = ElasticSearchController()
			response_data, total_records = es.search_document(["project"], search_query, project_data.get("page_number",1), project_data.get("records_per_page",40), exclude_list)
			if not project_data.get("request_id"):	
				request_id = store_request_in_elastic_search(project_data, search_query, "Project Search")
			response_data = putil.get_date_diff_from_posting(response_data)
			response_msg = "Project found for specfied criteria" if len(response_data) else "Project not found"
			from_record = (project_data.get("page_number",1) - 1) * cint(project_data.get("records_per_page",40)) + 1
			no_of_pages = math.ceil(flt(total_records)/project_data.get("records_per_page",40))
			to_record = from_record +  len(response_data) - 1 if response_data else from_record + project_data.get("records_per_page",40) - 1
			return {	
						"operation":"Search",
						 "message":response_msg ,
						 "total_records":total_records, 
						 "request_id":project_data.get("request_id") if project_data.get("request_id") else request_id, 
						 "records_per_page":project_data.get("records_per_page",40),
						 "from_record":from_record ,
						 "to_record":to_record,
						 "data":response_data, 
						 "user_id":project_data.get("user_id"), 
						 "no_of_pages":no_of_pages
					 }
		except elasticsearch.RequestError,e:
			raise ElasticInvalidInputFormatError(e.error)
		except elasticsearch.ElasticsearchException,e:
			raise ElasticSearchException(e.error)
		except Exception,e:
			raise e		
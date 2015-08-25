from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint
from elastic_controller import ElasticSearchController
import property_utils as putil
import json


@frappe.whitelist(allow_guest=True)
def post_property(data):
	if data:
		data = json.loads(data)
		required_field_list = ["property_title", "property_type", "property_subtype" ,"price", "location", "address", "carpet_area"]
		if putil.validate_property_data(data, required_field_list):
			custom_id = frappe.generate_hash()
			data["property_id"] = custom_id
			es = ElasticSearchController()
			es_result = es.index_document("property",data, custom_id)
			return es_result	


@frappe.whitelist(allow_guest=True)
def search_property(data):
	if data:
		property_data = json.loads(data)
		required_field_list = ["operation", "property_type", "property_subtype"]
		if putil.validate_property_data(property_data, required_field_list):
			search_query = putil.generate_search_query(property_data)
			es = ElasticSearchController()
			es_result = es.search_document(["property"], search_query, property_data.get("page_number",0), property_data.get("records_per_page",20))
			return es_result
		else:
			return "fail"
			





@frappe.whitelist(allow_guest=True)
def check_connection():
	import os
	return os.path.join()		

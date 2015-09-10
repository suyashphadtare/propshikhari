from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint
from elastic_controller import ElasticSearchController
from frappe.utils import add_days, getdate, now, nowdate ,random_string ,add_months
import property_utils as putil
import json ,ast
import time
import random
import datetime
import elasticsearch
from api_handler.api_handler.exceptions import *




"""
	Get project of given id from elastic search.

"""

def get_project_of_given_id(request_data):
	request_data = json.loads(request_data)
	email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	try:
		es = ElasticSearchController()
		response = es.search_document_for_given_id("project",request_data.get("project_id"))
		return {"operation":"Search", "message":"Project found" if len(response) else "Project Not Found", "user_id":request_data.get("user_id"), "data":response}
	except elasticsearch.TransportError:
		raise DoesNotExistError("Project Id does not exists")
	except Exception,e:
		raise OperationFailed("Get Project Operation Failed")
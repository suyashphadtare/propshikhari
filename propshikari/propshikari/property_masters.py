from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate
import property_utils as putil
import json
import time
import random
import datetime
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
			
		return {"operation":"Search","message":response_msg,"data":amenities_list, "user_id":data.get("user_id")}


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
			
		return {"operation":"Search","message":response_msg,"data":facilities_list, "user_id":data.get("user_id")}


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



""" 
	Create Group in Hunterscamp according to given request_data

"""


def create_group_in_hunterscamp(request_data):
	if request_data:
		request_data = json.loads(request_data)
		putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data, ["operation", "property_type", "property_subtype"])
		putil.isolate_city_from_location(request_data)
		group_search_conditions = make_conditions_for_duplicate_group(request_data)
		group_result = frappe.db.sql(""" select  name from `tabGroup` {0} """.format(group_search_conditions),as_dict=True)
		if group_result:
			group_result = [ group.get("name") for group in group_result if group ]
			raise DuplicateEntryError("Group {0} with same configuration already exists".format(','.join(group_result)))
		try:
			gr_doc = frappe.new_doc("Group")
			gr_doc.group_title = request_data.get("group_title")
			gr_doc.operation = request_data.get("operation")
			gr_doc.property_type =  request_data.get("property_type")
			gr_doc.property_subtype = request_data.get("property_subtype")
			gr_doc.location = request_data.get("location")
			gr_doc.property_subtype_option = request_data.get("property_subtype_option")
			gr_doc.creation_via  = "Website"
			gr_doc.min_area = request_data.get("min_area")
			gr_doc.max_area = request_data.get("max_area")
			gr_doc.min_budget = request_data.get("min_budget")
			gr_doc.max_budget = request_data.get("max_budget")
			gr_doc.unit_of_area = request_data.get("unit_of_area")
			gr_doc.city =request_data.get("city")
			gr_doc.status = "Active"
			gr_doc.save()
			return {"operation":"Create", "group_id":gr_doc.name, "message":"Group Created"}
		except frappe.MandatoryError,e:
			raise MandatoryError("Mandatory Field {0} missing".format(e.message))
		except (frappe.LinkValidationError, frappe.ValidationError)  as e:
			raise InvalidDataError(e.message)
		except Exception,e:
			return {"operation":"Create", "message":"Group not created"}



def join_user_with_group_id(request_data):			
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data,["user_id","group_id"])
		if not frappe.db.get_value("Group",{"name":request_data.get("group_id")},"name"):
			raise DoesNotExistError("Group ID {0} does not exists".format(request_data.get("group_id")))
		if frappe.db.get_value("Group User",{"group_id":request_data.get("group_id"), "user_id":request_data.get("user_id")},"name"):
			raise DuplicateEntryError("Group {0} already joined".format(request_data.get("group_id")))	
		try:
			grusr = frappe.new_doc("Group User")	
			grusr.user_id = request_data.get("user_id")
			grusr.group_id = request_data.get("group_id")
			grusr.user  = email
			grusr.save()
			return {"operation":"Search", "message":"Group joined"}
		except frappe.MandatoryError,e:
			raise MandatoryError("Mandatory Field {0} missing".format(e.message))
		except (frappe.LinkValidationError, frappe.ValidationError)  as e:
			raise InvalidDataError(e.message)
		except Exception,e:
			return {"operation":"Search", "message":"Group joining operation Failed"}



def shortlist_property(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		if not request_data.get("property_id"):
			raise MandatoryError("Mandatory Field Property Id missing")
		property_name = frappe.db.get_value("Shortlisted Property", {"property_id":request_data.get("property_id"), "user_id":request_data.get("user_id")} ,["name","status"], as_dict=1)
		if property_name:
			if property_name.get("status") == 'Active':	
				raise DuplicateEntryError("Property {0} already Shortlisted".format(request_data.get("property_id")))
			elif property_name.get("status") == 'Inactive':
				sp_doc = frappe.get_doc("Shortlisted Property", property_name.get("name"))
				sp_doc.status = "Active"
				sp_doc.save(ignore_permissions=True)
		else:
			try:
				sp_doc = frappe.new_doc("Shortlisted Property")
				sp_doc.user_id = request_data.get("user_id")
				sp_doc.property_id = request_data.get("property_id")
				sp_doc.status = "Active"
				sp_doc.save()
			except frappe.MandatoryError,e:
				raise MandatoryError("Mandatory Field {0} missing".format(e.message))
			except (frappe.LinkValidationError, frappe.ValidationError)  as e:
				raise InvalidDataError(e.message)
			except Exception,e:
				raise OperationFailed("Shortlist Property Operation Failed")
		return {"operation":"Create", "message":"Property Shortlisted" ,"property_id":request_data.get("property_id"), "user_id":request_data.get("user_id")}		



def create_feedback(request_data):
	if request_data:
		request_data = json.loads(request_data)
		email = putil.validate_for_user_id_exists(request_data.get("user_id"))
		putil.validate_property_data(request_data, ["request_type", "feedback"])
		try:
			fdbk = frappe.new_doc("Feedback")
			fdbk.property_id = request_data.get("property_id")
			fdbk.request_type = request_data.get("request_type")
			fdbk.user_feedback = request_data.get("feedback")
			fdbk.user_ratings = request_data.get("ratings") 
			fdbk.user_id = request_data.get("user_id")
			fdbk.save()
			return {"operation":"Create", "message":"Feedback Submitted"}
		except frappe.MandatoryError,e:
			raise MandatoryError("Mandatory Field {0} missing".format(e.message))
		except (frappe.LinkValidationError, frappe.ValidationError)  as e:
			raise InvalidDataError(e.message)
		except Exception,e:
			raise OperationFailed("Feedback Creation Failed")



def create_alerts(request_data):
	request_data = json.loads(request_data)
	putil.validate_for_user_id_exists(request_data.get("user_id"))
	putil.validate_property_data(request_data, ["operation", "property_type", "property_subtype"])
	putil.isolate_city_from_location(request_data)
	alert_search_conditions = make_conditions_for_duplicate_group(request_data)
	alert_result = frappe.db.sql(""" select  name from `tabAlerts` {0} """.format(alert_search_conditions),as_dict=True)
	if alert_result:
		alert_result = [ alert.get("name") for alert in alert_result if alert ]
		raise DuplicateEntryError("Alert {0} with same configuration already exists".format(','.join(alert_result)))
	try:
		alrt = frappe.new_doc("Alerts")
		alrt.alert_title = request_data.get("alert_title")
		alrt.operation = request_data.get("operation")
		alrt.property_type =  request_data.get("property_type")
		alrt.property_subtype = request_data.get("property_subtype")
		alrt.location = request_data.get("location")
		alrt.property_subtype_option = request_data.get("property_subtype_option")
		alrt.creation_via  = "Website"
		alrt.min_area = request_data.get("min_area")
		alrt.max_area = request_data.get("max_area")
		alrt.min_budget = request_data.get("min_budget")
		alrt.max_budget = request_data.get("max_budget")
		alrt.unit_of_area = request_data.get("unit_of_area")
		alrt.user_id = request_data.get("user_id")
		alrt.city = request_data.get("city")
		alrt.status = "Active"
		alrt.save()
		return {"operation":"Create", "alert_id":alrt.name, "message":"Alert Created"}
	except frappe.MandatoryError,e:
		raise MandatoryError("Mandatory Field {0} missing".format(e.message))
	except (frappe.LinkValidationError, frappe.ValidationError)  as e:
		raise InvalidDataError(e.message)
	except Exception,e:
		return {"operation":"Create", "message":"Alert not created"}


def make_conditions_for_duplicate_group(response):
	group_search_conditions = "where operation='{0}' and property_subtype='{1}' and property_type='{2}'  and status = 'Active'   ".format(response.get("operation"),response.get("property_subtype"),response.get("property_type"))
	group_field_set = {"property_subtype_option" ,"min_area", "max_area", "min_budget", "max_budget", "location", "city"}
	request_field_set = set()

	for group_field in group_field_set:
		if response.get(group_field):
			group_search_conditions += " and {0} = '{1}' ".format(group_field , response.get(group_field))
			request_field_set.add(group_field)

	for field in group_field_set - request_field_set:
		group_search_conditions += " and ({0}= ''  or {0} is null ) ".format(field)		

	return group_search_conditions



""" 
	Remove shortlised property for given user id.

"""

def remove_shortlisted_property(request_data):
	request_data = json.loads(request_data)
	email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	if not request_data.get("property_id"):
		raise MandatoryError("Mandatory Field Property Id missing")
	sp_nm = frappe.db.get_value("Shortlisted Property", {"user_id":request_data.get("user_id"), "property_id":request_data.get("property_id"), "status":"Active"}, "name")	
	if sp_nm:
		sp_doc = frappe.get_doc("Shortlisted Property", sp_nm)
		sp_doc.status = "Inactive"
		sp_doc.save(ignore_permissions=True)
		return { 
				"operation":"Update",
				"message":"Shortlisted Property removed successfully", 
				"user_id":request_data.get("user_id") 
			}
	else:
		raise DoesNotExistError("Property Id is not shortlised against user.")


def generate_title(request_data):
	title = ""
	property_type = request_data.get("property_type")
	property_subtype = request_data.get("property_subtype")
	property_subtype_option = request_data.get("property_subtype_option")
	location = request_data.get("location")
	current_date = datetime.datetime.now().strftime("%d/%m/%Y")

	if not location:
		title = '-'.join([property_type, property_subtype, current_date])
	else:
		if property_subtype_option:
			title = '-'.join([property_subtype_option, location, current_date])
		else:
			title = '-'.join([property_subtype, location, current_date])
	return title



def create_lead_from_userid(request_data, email, response):
	user_data = frappe.db.get_value("User", {"email":email}, '*',as_dict=True)
	try:
		lead_name = frappe.db.get_value("Lead",{"email_id":email},"name")
		if not lead_name:
			lead = frappe.new_doc("Lead")
			lead.lead_name = user_data.get("first_name")
			lead.email_id = user_data.get("email")
			lead.lead_from = "Propshikari"
			lead.mobile_no = user_data.get("mobile_no")
			lead.state = user_data.get("state")
			lead.city = user_data.get("city")
			lead.save(ignore_permissions=True)
			lead_name = lead.name
			address_nm = create_lead_address_from_user_data(user_data, lead_name)
		if not frappe.db.sql(""" select e.name from 
									`tabEnquiry` e , `tabProperty Details` pd
									where  pd.parent = e.name 
									and pd.property_id = '{0}'
									and e.lead = '{1}'
			                  """.format(response.get("property_id"), lead_name)):
			address_nm = frappe.db.get_value("Address", {"is_primary_address":1, "lead":lead_name},"name") 
			create_enquiry(user_data, lead_name, address_nm, response)
	except Exception,e:
		print "lead & Enquiry creation Error"
		print response.get("property_id")
		print frappe.get_traceback()



def create_lead_address_from_user_data(user_data, lead):
	if user_data.get("city") and user_data.get("area"):
		addr = frappe.new_doc("Address")
		addr.address_line1 = frappe.db.get_value("Area", user_data.get("area"), "area")
		addr.address_line2 = user_data.get("address")
		addr.city = frappe.db.get_value("City", user_data.get("city"), "city_name")
		addr.state = user_data.get("state")
		addr.email_id = user_data.get("email")
		addr.pincode = user_data.get("pincode")
		addr.lead = lead
		addr.lead_name = user_data.get("first_name")
		addr.save(ignore_permissions=True)
		return addr.name



def create_enquiry(user_data, lead, address, property_details):
	enquiry_child_row = [{
					"property_id"     :	property_details.get("property_id"),
					"property_type"   :	property_details.get("property_type"),
					"property_subtype": property_details.get("property_subtype"),
					"bhk"             : property_details.get("property_subtype_option",""),
					"property_name"   :	property_details.get("property_title"),
					"posting_date"    :	getdate(property_details.get("posting_date")) if property_details.get("posting_date") else "",
					"location"        : property_details.get("location"),
					"address"         : property_details.get("address"),
					"area"            : property_details.get("carpet_area"),
					"price"           : property_details.get("price"),
					"bathroom"        : property_details.get("no_of_bathroom")
			}]
	enq = frappe.get_doc({
					"doctype":"Enquiry",
					"lead":lead,
					"lead_name": user_data.get("first_name") + " " + user_data.get("last_name",""),
					"address":address if address else "",
					"property_type":property_details.get("property_type"),
					"property_subtype":property_details.get("property_subtype"),
					"property_subtype_option":property_details.get("property_subtype_option",""),
					"location":property_details.get("location"),
					"budget_minimum":0,
					"budget_maximum": property_details.get("price"),
					"area_minimum":0,
					"area_maximum":property_details.get("carpet_area"),
					"enquiry_from":"Lead",
					"property_details":enquiry_child_row
				})
	enq.flags.ignore_permissions = True
	enq.insert()






def create_contact_us_record(request_data):

	"""   Store User email_id , name, mobile no & message in contact us doctype.    """

	try:
		request_data = json.loads(request_data)
		cs = frappe.new_doc("Contact Us")
		cs.customer_name = request_data.get("name")
		cs.mobile_no = request_data.get("mobile_number")
		cs.message = request_data.get("message")
		cs.email_id = request_data.get("email_id")
		cs.save(ignore_permissions=True)
		return {"message":"Contact Submitted","user_id":request_data.get("user_id")}
	except Exception,e:
		raise OperationFailed("Contact Us operation failed")	

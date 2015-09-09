import frappe
import json
from api_handler.response import report_error
import time
import api_handler
from frappe.utils import cstr, cint


@frappe.whitelist(allow_guest=True)
def login(data):
	user_data = json.loads(data)
	try: 
		if user_data.get("email") and user_data.get("password"):
			loginmgr = frappe.auth.LoginManager()
			frappe.clear_cache(user = user_data["email"])
			loginmgr.authenticate(user_data["email"],user_data["password"])
			loginmgr.post_login()
			subscription = get_subscriptions(user_data["email"])
			frappe.response["sid"] = frappe.session.sid
			frappe.response["message"] = "Logged In"
			frappe.response["data"] = {"subscriptions":subscription}
			frappe.response["user_id"] = frappe.db.get_value("User",user_data["email"],"user_id")	
		else:
			raise api_handler.InvalidDataError("Invalid Input")
	except frappe.AuthenticationError,e:
		http_status_code = getattr(e, "http_status_code", 500)
		frappe.response["code"] = http_status_code
	finally:
		ts = int(time.time())
		frappe.response["timestamp"] = ts

def get_subscriptions(user):
	subs_dic = {}
	subs_name = frappe.db.get_value("User Subscription",{"user":user},"name")
	if subs_name:
		subs_doc = frappe.get_doc("User Subscription",subs_name)
		subs_dic["posting_allowed"] = cint(subs_doc.allowed)
		subs_dic["total_posted"] = cint(subs_doc.posted) or 0
		subs_dic["posting_available"] = cint(subs_doc.allowed) - cint(subs_doc.posted)
	return subs_dic	


		
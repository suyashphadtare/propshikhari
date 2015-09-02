import frappe
import json
from api_handler.response import report_error
import time
import api_handler



@frappe.whitelist(allow_guest=True)
def login(data):
	user_data = json.loads(data)
	try: 
		if user_data.get("email") and user_data.get("password"):
			loginmgr = frappe.auth.LoginManager()
			frappe.clear_cache(user = user_data["email"])
			loginmgr.authenticate(user_data["email"],user_data["password"])
			loginmgr.post_login()
			frappe.response["sid"] = frappe.session.sid
			frappe.response["message"] = "Logged In"
			frappe.response["user_id"] = frappe.db.get_value("User",user_data["email"],"user_id")	
		else:
			raise api_handler.InvalidDataError("Invalid Input")
	except frappe.AuthenticationError,e:
		http_status_code = getattr(e, "http_status_code", 500)
		frappe.response["code"] = http_status_code
	finally:
		ts = int(time.time())
		frappe.response["timestamp"] = ts

		
from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint
from frappe.utils import add_days, getdate, now, nowdate ,random_string ,add_months, getdate, formatdate
from frappe.auth import _update_password
import property_utils as putil
import json ,ast
import time
import random
import datetime
import os
import base64
from propshikari import login ,get_subscriptions
from api_handler.api_handler.exceptions import *





def register_user(data):
	user_data = json.loads(data)
	user = frappe.db.get("User", {"email": user_data.get("email")})
	putil.validate_property_data(user_data,["email","first_name","mobile_number","password","access_type"])
	if user:
		if user.disabled:
			raise UserRegisteredButDisabledError("User {0} Registered but disabled".format(user_data.get("email")))
		else:
			raise UserAlreadyRegisteredError("User {0} already Registered".format(user_data.get("email")))
	else:
		try:
			user_id = "USR-"  + cstr(int(time.time())) + '-' +  cstr(random.randint(1000,9999))
			user = frappe.get_doc({
					"doctype":"User",
					"email":user_data.get("email"),
					"first_name": user_data.get("first_name"),
					"enabled": 1,
					"last_name": user_data.get("last_name"),
					"new_password": user_data.get("password"),
					"user_id": user_id,
					"mobile_no":  user_data.get("mobile_number"),
					"access_type" :user_data.get("access_type"),
					"user_type": "Website User",
					"user_image":"assets/propshikari/default_user.gif",
					"send_welcome_email":0
				})

			user.flags.ignore_permissions = True
			user.insert()
			args = { "title":"Welcome to Propshikari", "first_name":user_data.get("first_name"), "last_name":user_data.get("last_name"), "user":user_data.get("email"), "password":user_data.get("password") }
			manage_subscription(user)
			create_mascot_status_for_user(user_id)
			send_email(user_data.get("email"), "Welcome to Propshikari", "/templates/new_user_template.html", args)
			login(data)
			frappe.response["message"] = "User Registeration done Successfully"
			return {"data":frappe.response.get("data")}
		except frappe.OutgoingEmailError:
			frappe.response["user_id"] = user_id
			raise OutgoingEmailError("User registered successfully but email not sent.")
		except frappe.MandatoryError,e:
			raise MandatoryError("Mandatory Field {0} missing".format(e.message))
		except (frappe.LinkValidationError, frappe.ValidationError)  as e:
			raise InvalidDataError(e.message)
		except Exception,e:
			raise UserRegisterationError("User Registration Failed")		





def manage_subscription(user):
	"""Add default Subscription for user to post post properties"""
	subs_doc = frappe.get_doc({
			"doctype":"User Subscription",
			"user":user.name
		})
	subs_doc.flags.ignore_permissions = True
	subs_doc.insert()
	return "Done"





def forgot_password(data):	
	user_data = json.loads(data)
	user_info = frappe.db.get("User", {"email": user_data.get("email")})
	if not user_info:
		raise DoesNotExistError("Email id does not exists")
	else:
		try:
			new_password = cstr(random.randint(1000000000,9999999999))
			_update_password(user_data.get("email"), new_password)
			args = {"first_name":user_info.get("first_name"), "new_password":new_password, "last_name":user_info.get("last_name")}
			send_email( user_data.get("email"), "Password Update Notification", "/templates/password_update.html", args)
			return {"operation":"Password Update", "message":"Password updated successfully"}
		except frappe.OutgoingEmailError:
			raise OutgoingEmailError("Password Updated successfully but email not sent.")
		except Exception:	
			raise ForgotPasswordOperationFailed("Forgot password operation failed")	



def update_password(data):
	user_data = json.loads(data)
	putil.validate_property_data(user_data,["old_password","new_password"])
	user_email = putil.validate_for_user_id_exists(user_data.get("user_id"))
	check_password = frappe.db.sql("""select `user` from __Auth where `user`=%s
			and `password`=password(%s)""", (user_email, user_data.get("old_password") ))
	if not check_password:
		raise InvalidPasswordError("Invalid Old Password")			
	else:
		try:
			new_password = user_data.get("new_password")
			_update_password(user_email, new_password)
			user_info = frappe.db.get("User", {"email": user_email})
			args = {"first_name":user_info.get("first_name"), "new_password":new_password, "last_name":user_info.get("last_name")}
			send_email(user_email, "Password Update Notification", "/templates/password_update.html", args)			
			return {"operation":"Password Update", "message":"Password updated successfully", "user_id":user_data.get("user_id")}
		except frappe.OutgoingEmailError:
			raise OutgoingEmailError("Password Updated successfully but email not sent.")
		except Exception,e:
			raise ForgotPasswordOperationFailed("Update password operation failed")	




def get_user_profile(data):
	request_data = json.loads(data)
	putil.validate_for_user_id_exists(request_data.get("user_id"))
	try:
		user_data = frappe.db.sql(""" SELECT 
											 ifnull(first_name, "") AS first_name,
										     ifnull(last_name, "") AS last_name,
										     ifnull(user_image,"") AS profile_photo,
										     ifnull(user_id,"") AS user_id,
										     ifnull(email, "") AS email,
										     ifnull(mobile_no, "") AS mobile_number,
										     ifnull(state, "") AS state,
										     ifnull(city,"") AS city,
										     ifnull(address, "") AS address,
										     ifnull(area, "") AS area,
										     ifnull(pincode, "") AS pincode,
										     ifnull(birth_date, "") AS dob,
										     ifnull(lattitude,"") AS geo_location_lat,
										     ifnull(longitude,"") AS geo_location_lon
										FROM `tabUser`
										WHERE user_id = '{0}'  """.format(request_data.get("user_id")),as_dict=True)
		user_data = user_data[0]
		if user_data.get("profile_photo"):
			user_data["profile_photo"] = frappe.request.host_url + user_data.get("profile_photo")
		user_data["city"] = frappe.db.get_value("City",user_data["city"],"city_name") or ""
		user_data["location"] = frappe.db.get_value("Area",user_data["area"],"area") or ""
		user_data["dob"] = datetime.datetime.strftime(getdate(user_data["dob"]), "%d-%m-%Y") if user_data["dob"] else ""
		user_data.pop("area",None)
		return {"operation":"Search", "message":"Profile Found", "data":user_data, "user_id":request_data.get("user_id")}	
	except Exception,e:
		print frappe.get_traceback()
		raise e
		raise GetUserProfileOperationFailed("User Profile Operation failed")	



def update_user_profile(data):
	request_data = json.loads(data)
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	city = frappe.db.get_value("City",{ "city_name":request_data.get("city") ,"state_name":request_data.get("state")}, "name")	
	area = frappe.db.get_value("Area",{ "city_name":city ,"state_name":request_data.get("state"), "area":request_data.get("location")}, "name")
	dob = getdate(getdate(request_data.get("dob")).strftime("%d-%m-%y")) if request_data.get("dob","") else ""  
	user_dict = {"first_name":request_data.get("first_name",""), "last_name":request_data.get("last_name",""), "mobile_no": request_data.get("mobile_number",""), "state": request_data.get("state",""), "city":city, "area":area, "address":request_data.get("address",""), "pincode":request_data.get("pincode",""), "birth_date":dob,"lattitude":request_data.get("geo_location_lat"),"longitude":request_data.get("geo_location_lon")}
	try:
		# user_dict["user_image"] = store_image_to_propshikari(request_data)
		user_doc = frappe.get_doc("User",user_email)
		user_doc.update(user_dict)
		user_doc.save(ignore_permissions=True)
		return {"operation":"Update", "message":"Profile Updated Successfully", "user_id":request_data.get("user_id")}
	except frappe.MandatoryError,e:
		raise MandatoryError("Mandatory Field {0} missing".format(e.message))
	except (frappe.LinkValidationError, frappe.ValidationError)  as e:
		raise InvalidDataError(e.message)
	except Exception,e:
		raise UserProfileUpdationFailed("Profile updation failed")	





def send_email(email, subject, template, args):
	frappe.sendmail(recipients=email, sender=None, subject=subject,
			message=frappe.get_template(template).render(args))


def store_image_to_propshikari(request_data):
	request_data = json.loads(request_data)
	putil.validate_property_data(request_data,["profile_photo"])
	if not request_data.get("profile_photo").get("file_ext"):
		raise MandatoryError("Image Extension not found")
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	if not os.path.exists(frappe.get_site_path("public","files",request_data.get("user_id"))):
		os.mkdir(frappe.get_site_path("public","files",request_data.get("user_id")))
	try:
		base64_data = request_data.get("profile_photo").get("file_data").encode("utf8")				
		base64_data = base64_data.split(',')[1]
		imgdata = base64.b64decode(base64_data)
		file_name = "PSUI-" + cstr(time.time())  + '.' + request_data.get("profile_photo").get("file_ext")
		with open(frappe.get_site_path("public","files",request_data.get("user_id"),file_name),"wb+") as fi_nm:
			fi_nm.write(imgdata)
		file_name = "files/"+request_data.get("user_id")+'/'+file_name
		frappe.db.set_value(dt="User",dn=user_email, field="user_image", val=file_name)
		return {"operation":"Update", "message":"Profile Image updated Successfully", "profile_image_url":frappe.request.host_url + file_name, "user_id":request_data.get("user_id")}
	except Exception,e:		
	 	raise ImageUploadError("Profile Image Updation Failed")



def validate_for_session_exists(request_data):
	request_data = json.loads(request_data)
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	sessions_status = frappe.db.get_value("Sessions", {"user":user_email, "sid":request_data.get("sid")}, "status")
	if sessions_status == "Active":
		return { "operation":"search", "session_expired":False, "message":"Session exists against user {0}".format(user_email)}
	else:
		return { "operation":"search", "session_expired":True, "message":"Session does not exists"}			


			

def create_mascot_status_for_user(user_id):
	
	"""  Create Mascot Status for Shortlisting and Alerts.   """

	try:
		ms = frappe.new_doc("Mascot Status")
		ms.user_id = user_id
		ms.shortlist_status = 0
		ms.alert_status = 0
		ms.mobile_shortlist_status = 0
		ms.mobile_alert_status = 0
		ms.save(ignore_permissions=True)
	except Exception,e:
		pass



def get_mascot_status_for_user(data):

	request_data = json.loads(data)
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	validate_mascot_source(request_data)
	fields = {"website":"shortlist_status, alert_status", "mobile":"mobile_alert_status as alert_status, mobile_shortlist_status as shortlist_status"}
	try:
		mascot_data = frappe.db.sql("""
										select {fields}
										from `tabMascot Status`
										where user_id = '{uid}'  
									""".format(fields=fields.get(request_data.get("mascot_source")), uid=request_data.get("user_id")), as_dict=True)
		
		return {
					"user_id":request_data.get("user_id"),
					"message":"Mascot Status Found" if mascot_data else "Mascot status not found",
					"data":mascot_data[0] if mascot_data else ""

				}
	except Exception,e:
		pass			



def update_mascot_status(data):

	request_data = json.loads(data)
	user_email = putil.validate_for_user_id_exists(request_data.get("user_id"))
	validate_mascot_source(request_data)
	mascot_dict = validate_mascot_data(request_data.get("mascot_list"))
	mobile_dict = {"mobile_shortlist_status":"shortlist_status", "mobile_alert_status":"alert_status"}	
	fields = {	
				"website":mascot_dict, 
				"mobile":{ mobile_field:mascot_dict.get(mascot_field) for mobile_field, mascot_field  in mobile_dict.items() if mascot_dict.has_key(mascot_field)   }
			 }
	try:
		ms = frappe.get_doc("Mascot Status", {"user_id":request_data.get("user_id")})
		ms.update(fields.get(request_data.get("mascot_source")))
		ms.save(ignore_permissions=True)
		return {"user_id":request_data.get("user_id"), "message":"Mascot Status Updated Successfully"}
	except Exception,e:
		return {"user_id":request_data.get("user_id"), "message":"Mascot status not found against user {0}".format(user_email)}
				


def validate_mascot_source(request_data):
	if request_data.get("mascot_source"):
		if request_data.get("mascot_source") not in ["website", "mobile"]:
			raise InvalidDataError("Invalid input of mascot source field")
	else:
		raise MandatoryError("Mandatory field mascot source is missing")


def validate_mascot_data(mascot_list):
	if not mascot_list: 
		raise MandatoryError("Mandatory field mascot list missing")
	else:
		mascot_dict= {}
		for mascot in mascot_list:
			mascot_dict[mascot] = 1
		return mascot_dict	 


def set_user_id(doc,method):
	pass

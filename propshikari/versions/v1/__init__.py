from __future__ import unicode_literals
import api_handler
import propshikari.propshikari.propshikari_api as api
from frappe.utils import cstr, cint
import frappe
import time
import json
import random
from frappe.utils.file_manager import  save_file



@frappe.whitelist()
def post_property(data):
	return api.post_property(data)


@frappe.whitelist(allow_guest=True)
def search_property(data):
	return api.search_property(data)



@frappe.whitelist(allow_guest=True)
def register_user(data):
	return api.register_user(data)


@frappe.whitelist(allow_guest=True)
def forgot_password(data):
	return api.forgot_password(data)



@frappe.whitelist()
def update_password(data):
	return api.update_password(data)



@frappe.whitelist()
def get_user_profile(data):
	return api.get_user_profile(data)


@frappe.whitelist()
def update_user_profile(data):
	return api.update_user_profile(data)


@frappe.whitelist()
def log_out(data):
	return api.log_out_from_propshikari(data)	


@frappe.whitelist(allow_guest=True)
def get_state_city_location_list(data):
	return api.get_states_cities_locations_from_propshikari(data)



@frappe.whitelist(allow_guest=True)
def store_image_to_propshikari(data):
	return api.store_image_to_propshikari(data)


	





		
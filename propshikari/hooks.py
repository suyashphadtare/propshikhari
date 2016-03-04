# -*- coding: utf-8 -*-
from __future__ import unicode_literals

app_name = "propshikari"
app_title = "Propshikari"
app_publisher = "New Indictrans"
app_description = "Application for hunterscamp and rest management"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "contact@indictranstech.com"
app_version = "0.0.1"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/propshikari/css/propshikari.css"
# app_include_js = "/assets/propshikari/js/propshikari.js"

# include js, css files in header of web template
# web_include_css = "/assets/propshikari/css/propshikari.css"
# web_include_js = "/assets/propshikari/js/propshikari.js"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

index_name = "propshikari"

snapshot_repo = "propshikari_elastic_backup"

# Installation
# ------------

# before_install = "propshikari.install.before_install"
# after_install = "propshikari.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "propshikari.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"propshikari.tasks.all"
# 	],
# 	"daily": [
# 		"propshikari.tasks.daily"
# 	],
# 	"hourly": [
# 		"propshikari.tasks.hourly"
# 	],
# 	"weekly": [
# 		"propshikari.tasks.weekly"
# 	]
# 	"monthly": [
# 		"propshikari.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "propshikari.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "propshikari.event.get_events"
# }


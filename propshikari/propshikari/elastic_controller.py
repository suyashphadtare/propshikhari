from __future__ import unicode_literals
import frappe
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from datetime import datetime
from elasticsearch import helpers


class ElasticSearchController():
	
	""" 
	    This is elastic search handler designed to cater all 
	    elastic search operations like search,indexing,update. 	
	"""
	
	index_name = frappe.get_hooks("index_name", app_name="propshikari")[0]
	#es = Elasticsearch(["192.168.5.26"])
	es = Elasticsearch()
	
	def __init__(self):
		self.create_index_if_not_exists()

	
	def index_document(self,type_name, data, custom_id):
		response = self.es.index(index=self.index_name, doc_type=type_name, body=data, id=custom_id)	
		return response

	
	
	def search_document(self, type_list, search_body, page_no, no_of_records=40, exclude_list=[], include_list=[]):
		
		""" 
			Search document in given type_list for given search criteria 
	   		with no of records to be returned.
		"""	
		response = self.es.search(index=self.index_name, doc_type=type_list, body=search_body, from_=(page_no - 1) * no_of_records, size=no_of_records, _source_exclude=exclude_list , _source_include=include_list)
		total_records = response["hits"]["total"]
		return [response["_source"] for response in response["hits"]["hits"]] , total_records


	
	
	def search_document_for_given_id(self, type_list, search_id, exclude_list=[], include_list=[]):

		""" Get document of given ids from elasticsearch """

		response = self.es.get(index=self.index_name, doc_type=type_list, id=search_id, _source_exclude=exclude_list ,_source_include=include_list)
		return response.get("_source")


	
	def update_docuemnt(self, type_name, search_id, search_body):

		"""  Update Document based on given id in elasticsearch """
		
		response = self.es.update(index=self.index_name, doc_type=type_name ,id=search_id, body=search_body)
		return response

	
	def create_index_if_not_exists(self):
		
		""" Check if index exists & if not exists create index & types & store their mappings.  """
		
		ic = IndicesClient(self.es)
		response = ic.exists(index=[self.index_name])
		if not response:
			es_mappings = ElasticSearchController.get_index_mapper_dict()			
			index_response = ic.create(index=self.index_name, body={ "mappings":es_mappings })

	
	def bulk_upload(self, actions_list):

		""" Bulk Upload of documents in elasticsearch having operations like index, create, update, delete. """
		
		response = helpers.bulk(client=self.es, actions=actions_list)
		return response
			
			
	
	@staticmethod
	def get_index_mapper_dict():
		from elastic_search_mappers import project_mapper, property_mapper, request_mapper
		mappings = {}
		mappings.update(project_mapper.project_mapper)
		mappings.update(property_mapper.property_mapper)
		mappings.update(request_mapper.request_mapper)
		return mappings


	def refresh_index(self):
		ic = IndicesClient(self.es)
		response = ic.refresh(index=[self.index_name])
		print response




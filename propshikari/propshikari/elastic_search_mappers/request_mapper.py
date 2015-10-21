request_mapper = {
	"request":{
		"properties":{
			"request_id":{
				"type": "string",
        		"index": "not_analyzed",
        		"store": "true"
			},
			"user_id":{
				"type": "string",
        		"index": "not_analyzed",
        		"store": "true"
			},
			"operation":{
				"type": "string",
        		"store": "true"
			},
			"property_type":{
				"type": "string",
        		"index": "not_analyzed",
        		"store": "true"
			},
			"property_subtype":{
				"type": "string",
        		"index": "not_analyzed",
        		"store": "true"
			},
			"project_type":{
				"type": "string",
        		"index": "not_analyzed",
        		"store": "true"
			},
			"project_subtype":{
				"type": "string",
        		"index": "not_analyzed",
        		"store": "true"
			},
			"property_subtype_option":{
				"type": "string",
        		"store": "true"
			},
			"min_area":{
				"type": "double",
        		"store": "true"
			},
			"max_area":{
				"type": "double",
        		"store": "true"
			},
			"min_budget":{
				"type": "double",
        		"store": "true"
			},
			"max_budget":{
				"type": "double",
        		"store": "true"
			},
			"search_query":{
				"type": "string",
        		"index": "not_analyzed",
        		"store": "true"
			},
			"adv_search_query":{
				"type": "string",
        		"index": "not_analyzed",
        		"store": "true"
			},
			"request_type":{
				"type": "string",
        		"index": "not_analyzed",
        		"store": "true"
			},
			"created_by":{
				"type": "string",
        		"store": "true"
			},
			"modified_by":{
				"type": "string",
        		"store": "true"
			},
			"creation_date":{
				"type": "date",
        		"format": "dd-MM-YYYY",
        		"store": "true"
			},
			"posted_datetime": {
        		"type": "date",
        		"store": "true",
        		"format": "yyyy-MM-dd HH:mm:ss"
      		},
		    "modified_datetime": {
		        "type": "date",
		        "store": "true",
		        "format": "yyyy-MM-dd HH:mm:ss"
		    },
		    "modified_date": {
		        "type": "date",
		        "format": "dd-MM-YYYY",
		        "store": "true"
		    },
		    "unit_of_area":{
        		"type": "string",
        		"store": "true"
      		}
		}
	}
}

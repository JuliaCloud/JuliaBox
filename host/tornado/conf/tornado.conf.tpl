{
    "port" : 8888,
    "gauth" : $$GAUTH,
    "dhostlocal" : True,
    # number of active containers to allow per instance
    "numlocalmax" : $$NUM_LOCALMAX,
    # maximum number of hops through the load balancer till the installation is declared overloaded
    "numhopmax": 10,
    "sesskey" : "$$SESSKEY",
    "expire" : $$EXPIRE,
    "admin_users" : ["$$ADMIN_USER"],
    "dhosts" : [],
    "protected_sessions" : [],
    # default 1GB containers. multiplier can be applied from user profile
    "mem_limit" : 1000000000,
    # max 1024 cpu slices. default maximum allowed is 1/8th of total cpu slices. multiplier can be applied from user profile.
    "cpu_limit" : 128,
    "inactivity_timeout" : 300,
    "delete_stopped_timeout" : 7200,
    "docker_image" : "$$DOCKER_IMAGE",
    "google_oauth": {
        "key": "$$CLIENT_ID", 
        "secret": "$$CLIENT_SECRET"
    },
    "cloud_host": {
    	"install_id": "JuliaBox",
    	"region": "us-east-1",
    	
    	# enable/disable features
    	"s3": True,
    	"dynamodb": True,
    	"cloudwatch": True,
    	
    	# configure names for tables and buckets
	    "jbox_users": "jbox_users",
	    "jbox_accounting": "jbox_accounting",
	    "backup_bucket": "juliabox_userbackup",
	    
    	"dummy" : "dummy"
    },
    "env_type" : "prod",
    "backup_location" : "~/juliabox_backup",
    "dummy" : "dummy"
}


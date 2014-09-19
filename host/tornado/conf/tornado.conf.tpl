{
    "port" : 8888,
    "gauth" : $$GAUTH,
    "invite_only" : $$INVITE,
    
    # Self teminate if required to scale down
    "scale_down" : False,
    # Number of active containers to allow per instance
    "numlocalmax" : $$NUM_LOCALMAX,
    # Number of disks available to be mounted to images
    "numdisksmax" : $$NUM_DISKSMAX,
    # Maximum number of hops through the load balancer till the installation is declared overloaded
    "numhopmax": 10,
    
    # Installation specific session key. Used for encryption and signing. 
    "sesskey" : "$$SESSKEY",
    
    # Users that have access to the admin tab
    "admin_users" : ["$$ADMIN_USER"],
    
    # Sessions which will not be timed out and auto-cleaned up
    "protected_sessions" : [],
    
    # Maximum memory allowed per docker container.
    # To be able to use `mem_limit`, the host kernel must be configured to support the same. 
    # See <http://docs.docker.io/en/latest/installation/kernel/#memory-and-swap-accounting-on-debian-ubuntu> 
    # Default 1GB containers. multiplier can be applied from user profile
    "mem_limit" : 1000000000,
    # Max 1024 cpu slices. default maximum allowed is 1/8th of total cpu slices. multiplier can be applied from user profile.
    "cpu_limit" : 128,
    # Max size of user home. Default 500MB. User home is backed up within 10 minutes of the container stopping.
    "disk_limit" : 500000000,
    
    # Seconds to wait before clearing an inactive session, for example, when the user closes the browser window (protected_sessions are not affected)
    "inactivity_timeout" : 300,
    # Upper time limit for a user session before it is auto-deleted. 0 means never expire (protected_sessions are not affected)
    "expire" : $$EXPIRE,
    # Seconds before a stopped container is backed up and deleted.
    "delete_stopped_timeout" : 300,
    # Number of parallel threads to run for backups
    "backup_threads" : 2,
    
    # The docker image to launch
    "docker_image" : "$$DOCKER_IMAGE",
    
    "google_oauth": {
        "key": "$$CLIENT_ID", 
        "secret": "$$CLIENT_SECRET"
    },
    
    "cloud_host": {
    	"install_id": "JuliaBox",
    	"region": "us-east-1",
    	
    	# Enable/disable features
    	"s3": True,
    	"dynamodb": True,
    	"cloudwatch": True,
    	
    	# Configure names for tables and buckets
	    "backup_bucket": "juliabox_userbackup",
	    
    	"dummy" : "dummy"
    },
    "env_type" : "prod",
    "backup_location" : "~/juliabox_backup",
    "mnt_location" : "/mnt/jbox/mnt",
    "user_home_image" : "~/user_home.tar.gz",
    "dummy" : "dummy"
}


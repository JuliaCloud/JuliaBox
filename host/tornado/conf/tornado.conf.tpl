{
    "port" : 8888,
    "async_job_ports" : (8889,8890),
    "websocket_protocol" : "wss",
    # debug:10, info:20, warning:30, error:40
    "jbox_log_level": 10,
    "root_log_level": 40,
    "gauth" : $$GAUTH,
    "invite_only" : $$INVITE,
    
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
    	"autoscale": True,
    	"route53": True,
    	"ebs": True,
        "ses": True,

    	"autoscale_group": "juliabox",
    	"route53_domain": "juliabox.org",

        # Average cluster load at which to initiate scale up
    	"scale_up_at_load": 70,
    	"scale_up_policy": "addinstance",
        # Self teminate if required to scale down
        "scale_down" : False,

    	# Configure names for tables and buckets
	    "backup_bucket": "juliabox-userbackup",

	    # EBS disk template snapshot id
	    "ebs_template": None,
	    "ebs_mnt_location": "/mnt/jbox/ebs",

    	"dummy" : "dummy"
    },

    "user_activation": {
        # maintenance runs are once in 5 minutes
        # max per hour activations = 60/5 * 10 = 120
        "max_activations_per_run": 10,
        "max_activations_per_sec": 10,
        "sender": "admin@juliabox.org",
        "mail_subject": "Your JuliaBox account is now active",
        "mail_body": """Congratulations!

We have now activated your JuliaBox account at http://www.juliabox.org/

For discussions and feedback, please use the mailing list: https://groups.google.com/forum/#!forum/julia-box

Please post any issues or feature requests on GitHub: https://github.com/JuliaLang/JuliaBox

Welcome to JuliaBox. We hope you will like it and also share with your friends.

- JuliaBox Team"""
    },

    "env_type" : "prod",
    "backup_location" : "~/juliabox_backup",
    "pkg_location": "~/julia_packages",
    "mnt_location" : "/mnt/jbox/mnt",
    "user_home_image" : "~/user_home.tar.gz",
    "pkg_image": "~/julia_packages.tar.gz",

    "plugins": [
        "juliabox.plugins.vol_loopback",
        "juliabox.plugins.vol_ebs",
        "juliabox.plugins.vol_defpkg",
        "juliabox.plugins.course_homework",
        "juliabox.plugins.parallel",
        ""
    ],

    "dummy" : "dummy"
}


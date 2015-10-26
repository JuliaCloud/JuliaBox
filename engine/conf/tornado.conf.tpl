{
    "container_manager_ports" : (8889,8890),
    "websocket_protocol" : "wss",
    # debug:10, info:20, warning:30, error:40
    "jbox_log_level": 10,
    "root_log_level": 40,

    # Number of disks available to be mounted to images
    "numdisksmax" : 30,
    # Maximum number of hops through the load balancer till the installation is declared overloaded
    "numhopmax": 10,
    # Max size of user home. Default 500MB. User home is backed up within 10 minutes of the container stopping.
    "disk_limit" : 500000000,

    # Installation specific session key. Used for encryption and signing. 
    "sesskey" : "$$SESSKEY",
    
    # Users that have access to the admin tab
    "admin_users" : [],

    # api container configuration
    "api": {
        "manager_port": 8887,
        # The docker image to launch
        "docker_image" : "juliabox/juliaboxapi",
        # Maximum memory allowed per docker container. Default 1GB. Per API multiplier from configuration
        "mem_limit" : 1000000000,
        # Of max 1024 cpu slices. Per API multiplier from configuration
        "cpu_limit" : 128,
        # Number of active containers to allow per instance
        "numlocalmax" : 30,
        # Number of active containers or each type to allow per instance
        "numapilocalmax" : 5,
        # Maximum number of requests in queue before rejecting new requests
        "numapilocalmax" : 5,
        # Seconds to wait before force deleting a non-responding container
        "expire" : 1800,
        # ulimit for container, set as both hard and soft limit
        "ulimits" : { "nofile": 1024 }
    },

    # interactive container configuration
    "interactive": {
        "manager_port" : 8888,
        # The docker image to launch
        "docker_image" : "juliabox/juliabox",
        # Maximum memory allowed per docker container.
        # Default 1GB containers. multiplier can be applied from user profile
        "mem_limit" : 1000000000,
        # Of max 1024 cpu slices. Per user multiplier from configuration
        "cpu_limit" : 128,
        # Number of active containers to allow per instance
        "numlocalmax" : 30,
        # Seconds to wait before clearing an inactive session, for example, when the user closes the browser window
        "inactivity_timeout" : 300,
        # Upper time limit for a user session before it is auto-deleted. 0 means never expire
        "expire" : 0,
        # ulimit for container, set as both hard and soft limit
        "ulimits" : { "nofile": 1024 }
    },

    # if using Google auth, the API key and secret to use
    "google_oauth": {
        "key": "",
        "secret": ""
    },
    
    "cloud_host": {
    	"install_id": "JuliaBox",
    	"region": "us-east-1",
        "domain": "juliabox.org",

    	"autoscale_group": "juliabox",
        "scale_down": True,

        # Average cluster load at which to initiate scale up
    	"scale_up_at_load": 70,
    	"scale_up_policy": "addinstance",

    	# Configure names for tables and buckets
	    "backup_bucket": "juliabox-userbackup",
        "status_bucket": "juliabox-status",

	    # EBS disk template snapshot id
	    "ebs_template": None,

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
    "backup_location" : "/jboxengine/data/backups",
    "pkg_location": "/jboxengine/data/packages",
    "mnt_location" : "/jboxengine/data/disks/loop/mnt",
    "user_home_image" : "/jboxengine/data/user_home.tar.gz",
    "pkg_image": "/jboxengine/data/julia_packages.tar.gz",

    "db": {
        # default connect string for sqlite database
        "connect_str": "/jboxengine/data/db/juliabox.db",
        # table name mappings
        # "tables" : {
        # }
    },

    "plugins": [
        "juliabox.plugins.compute_ec2",
        "juliabox.plugins.vol_loopback",
        "juliabox.plugins.vol_ebs",
        "juliabox.plugins.vol_defpkg",
        "juliabox.plugins.course_homework",
        "juliabox.plugins.parallel",
        "juliabox.plugins.auth_google",
        "juliabox.plugins.usage_accounting",
        "juliabox.plugins.db_dynamodb",
        "juliabox.plugins.bucket_s3",
        "juliabox.plugins.dns_route53",
        "juliabox.plugins.sendmail_ses",
        "juliabox.plugins.api_admin",
        "juliabox.plugins.user_admin",
        ""
    ],

    "dummy" : "dummy"
}


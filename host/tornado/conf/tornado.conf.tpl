{
    "port" : 8888,
    "gauth" : $$GAUTH,
    "dhostlocal" : True,
    "numlocalmax" : $$NUM_LOCALMAX,
    "sesskey" : "$$SESSKEY",
    "expire" : $$EXPIRE,
    "admin_users" : ["$$ADMIN_USER"],
    "dhosts" : [],
    "protected_sessions" : [],
    "mem_limit" : 1073741824,
    "inactivity_timeout" : 300,
    "docker_image" : "$$DOCKER_IMAGE",
    "google_oauth": {
        "key": "$$CLIENT_ID", 
        "secret": "$$CLIENT_SECRET"
    },
    "env_type" : "prod",
    "backup_location" : "~/juliabox_backup",
    "jbox_users": "jbox_users",    
    "backup_bucket": "juliabox_userbackup",
    "dummy" : "dummy"
}


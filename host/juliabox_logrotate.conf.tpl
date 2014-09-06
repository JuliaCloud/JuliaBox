$$JBOX_DIR/host/nginx/logs/error.log $$JBOX_DIR/host/nginx/logs/access.log {
	daily
	size 5M
	missingok
	rotate 7
	compress
	compressext .gz
	delaycompress
	
	dateext
	dateformat -%Y-%m-%d-%s
	
	notifempty
	sharedscripts
	postrotate
		[ ! -f $$JBOX_DIR/host/nginx/logs/nginx.pid ] || kill -USR1 `cat $$JBOX_DIR/host/nginx/logs/nginx.pid`
	endscript
}

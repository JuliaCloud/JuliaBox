var JuliaBox = (function($, _, undefined){
	var _msg_body = null;
	var _msg_div = null;
	var _gauth = null;
	var _locked = 0;
	var _ping_fails = 0;
	var _max_ping_fails = 1;
	var _loggedout = false;
	
	var self = {
	    send_keep_alive: function() {
	    	if((_ping_fails > _max_ping_fails) || _loggedout) return;
	        $.ajax({
	        	url: '/ping/',
	        	type: 'GET',
	        	success: function(res) {
	        		_ping_fails = 0;
	        	},
	        	error: function(res) {
	        		_ping_fails += 1;
	        		if (_ping_fails > _max_ping_fails) {
	        			self.inform_logged_out();
	        		}
	        	}
	        });
	    },
	    
	    comm: function(url, type, data, success, error) {
	    	self.lock_activity();
	    	$.ajax({
	    		url: url,
	    		type: type,
	    		data: data,
	    		success: function(res) {
	    			self.unlock_activity();
	    			success(res);
	    		},
	    		error: function(res) {
	    			self.unlock_activity();
	    			error(res);
	    		}
	    	});
	    },

	    show_ssh_key: function () {
	    	s = function(sshkey){ bootbox.alert('<pre>' + sshkey.data + '</pre>'); };
	    	f = function() { bootbox.alert("Oops. Unexpected error while retrieving the ssh key.<br/><br/>Please try again later."); };
	    	self.comm('/hostupload/sshkey', 'GET', null, s, f);
	    },

        make_invites_table: function(data) {
            var invites = data.data;

            function tr(i) {
		function fmt_date(date) {
			return new Date(Date.parse(date))
				.toLocaleString();
		}

                return _.reduce(
                    [ i.invite_code
                    , fmt_date(i.time_created)
                    , i.max_count || 'Unlimited'
                    , fmt_date(i.expires_on)
                    , i.count || 'NA'],
		    function(row, cell) {
			    return row.append($("<td/>").text(cell));
		    }, $("<tr/>"));
            }
	    var $header = $("<h2>Existing invite codes</h2>"),
                $thead = $("<thead></thead>");

            $("<tr></tr>")
		    .append("<th>Code</th>")
		    .append("<th>Created</th>")
		    .append("<th>Max</th>")
		    .append("<th>Expires</th>")
		    .append("<th>Used</th>").appendTo($thead)

            var $tbody = _.reduce(
                    _.map(invites, tr),
                    function (x, c) { return x.append(c); },
                    $("<tbody/>")
                    );
            var $table = $("<table/>")
                        .attr("class", "table table-striped")
                        .append($thead).append($tbody)

	    var $newinvite = $('<form method="POST" action="/hostadmin?action=make_invite"/>')
	    	.append($('<label for="invite_code">Code</label>' +
			    '<input class="form-control" id="invite_code" type="text" name="invite_code" placeholder="Create a new code">'))
		.append($('<label for="expires_on">Expires</label>' +
			     '<input class="form-control" id="expires_on" type="datetime" name="expires_on" placeholder="Expires on">'))
	    	.append($('<label for="max_count" for="max_count">Max</label>' +
			  '<input class="form-control" id="max_count" type="text" name="max_count" placeholder="Max">'))
	    	.append($('<input class="btn btn-primary" type="submit">'))

	    return $("<div/>").append($header).append($table);

        },

        show_invites_report: function () {
            s = function(data) {
                bootbox.alert(self.make_invites_table(data).html());
            };
            f = function () {
                bootbox.alert("Oops. Unexpected error occured while showing invite codes");
            }
            self.comm('/hostadmin/?action=invites_report', 'GET', null, s,f);
        },
	    
		do_upgrade: function () {
			s = function(res) {
				if(res.code == 0) {
					bootbox.alert('Upgrade initiated. You have been logged out. Press Ok to log in again and complete the upgrade.', function(){
						top.location.href = '/';
					});    					
				}
				else {
					bootbox.alert('Oops. Unexpected error while upgrading.<br/><br/>Please try again later.');
				}
			};
			f = function() { bootbox.alert("Oops. Unexpected error while upgrading.<br/><br/>Please try again later."); };
    		self.comm('/hostadmin/', 'GET', { 'upgrade_id' : 'me' }, s, f);
		},

		init_gauth_tok: function(tok) {
			_gauth = tok;
		},
		
		register_jquery_folder_field: function (fld, trig, loc) {
			jqtrig = $('#filesync-frame').contents().find(trig);
			if(_gauth == null) {
				jqtrig.click(function(e){
					self.sync_auth_gdrive();
				});
			}
			else {
				jqfld = $('#filesync-frame').contents().find(fld);
				jqloc = $('#filesync-frame').contents().find(loc);
				jqfld.change(function() {
	        		parts = jqfld.val().split('/');
	        		if(parts.length > 3) {
	        			jqloc.val(parts[2]);
	        		}
	        		else {
	        			jqloc.val('');
	        		}
	            });
				jqfld.prop('readonly', true);
				jqfld.gdrive('set', {
	    			'trigger': jqtrig, 
	    			'header': 'Select a folder to synchronize',
	    			'filter': 'application/vnd.google-apps.folder'
				});				
			}
		},

		sync_addgit: function(repo, loc, branch) {
			repo = repo.trim();
			loc = loc.trim();
			branch = branch.trim();
			if(repo.length == 0) {
				return;
			}
			self.inpage_alert('info', 'Adding repository...');
			s = function(res) {
				$('#filesync-frame').attr('src', '/hostupload/sync');
				if(res.code == 0) {
					self.inpage_alert('success', 'Repository added successfully');
				}
				else if(res.code == 1) {
					self.inpage_alert('warning', 'Repository added successfully. Pushing changes to remote repository not supported with HTTP URLs.');
				}
				else {
					self.inpage_alert('danger', 'Error adding repository');
				}
			};
			f = function() { self.inpage_alert('danger', 'Error adding repository.'); };
    		self.comm('/hostupload/sync', 'POST', {'action': 'addgit', 'repo': repo, 'loc': loc, 'branch': branch}, s, f);
		},

		sync_auth_gdrive: function(fn) {
			if(_gauth == null) {
				self.popup_confirm("You must authorize JuliaBox to access Google Drive. Would you like to do that now?", function(res) {
					if(res) {
						top.location.href = '/hostlaunchipnb/?state=ask_gdrive';
					}
				});
			}
			else {
				fn();
			}
		},

		sync_addgdrive: function(repo, loc) {
			repo = repo.trim();
			loc = loc.trim();
			data = {'action': 'addgdrive', 'repo': repo, 'loc': loc, 'gauth': _gauth};
			if(repo.length == 0) {
				return;
			}
			s = function(res) {
				$('#filesync-frame').attr('src', '/hostupload/sync');
				if(res.code == 0) {
					self.inpage_alert('success', 'Repository added successfully');
				}
				else {
					self.inpage_alert('danger', 'Error adding repository');
				}
			};
			f = function() { self.inpage_alert('danger', 'Error adding repository.'); };
			self.sync_auth_gdrive(function(){
				self.inpage_alert('info', 'Adding repository...');
	    		self.comm('/hostupload/sync', 'POST', data, s, f);
			});
		},

		sync_syncgit: function(repo) {
			self.inpage_alert('info', 'Synchronizing repository...');
			s = function(res) {
				if(res.code == 0) {
					self.inpage_alert('success', 'Repository synchronized successfully');
				}
				else if(res.code == 1) {
					self.inpage_alert('warning', 'Repository synchronized with some conflicts');
				}
				else {
					self.inpage_alert('danger', 'Error synchronizing repository');
				}
			};
			f = function() { self.inpage_alert('danger', 'Error synchronizing repository.'); };
    		self.comm('/hostupload/sync', 'POST', {'action': 'syncgit', 'repo': repo}, s, f);
		},

		sync_syncgdrive: function(repo) {
			data = {'action': 'syncgdrive', 'repo': repo, 'gauth': _gauth};
			s = function(res) {
				if(res.code == 0) {
					self.inpage_alert('success', 'Repository synchronized successfully');
				}
				else {
					self.inpage_alert('danger', 'Error synchronizing repository');
				}
			};
			f = function() { self.inpage_alert('danger', 'Error synchronizing repository.'); };
			self.sync_auth_gdrive(function(){
				self.inpage_alert('info', 'Synchronizing repository...');
	    		self.comm('/hostupload/sync', 'POST', data, s, f);
	   		});
		},

		sync_delgit: function(repo) {
			self.inpage_alert('warning', 'Deleting repository...');
			s = function(res) {
				$('#filesync-frame').attr('src', '/hostupload/sync');
				if(res.code == 0) {
					self.inpage_alert('success', 'Repository deleted successfully');
				}
				else {
					self.inpage_alert('danger', 'Error deleting repository');
				}
			};
			f = function() { self.inpage_alert('danger', 'Error deleting repository.'); };
    		self.comm('/hostupload/sync', 'POST', {'action': 'delgit', 'repo': repo}, s, f);
		},

		sync_delgdrive: function(repo) {
			data = {'action': 'delgdrive', 'repo': repo, 'gauth': _gauth};
			s = function(res) {
				$('#filesync-frame').attr('src', '/hostupload/sync');
				if(res.code == 0) {
					self.inpage_alert('success', 'Repository deleted successfully');
				}
				else {
					self.inpage_alert('danger', 'Error deleting repository');
				}
			};
			f = function() { self.inpage_alert('danger', 'Error deleting repository.'); };
			self.sync_auth_gdrive(function(){
				self.inpage_alert('warning', 'Deleting repository...');
	    		self.comm('/hostupload/sync', 'POST', data, s, f);
	   		});
		},
		
		sync_delgit_confirm: function(repo) {
			self.popup_confirm('Are you sure you want to delete this repository?', function(res) {
				if(res) {
					self.sync_delgit(repo);
				}
			});
	    },
		
		sync_delgdrive_confirm: function(repo) {
			self.popup_confirm('Are you sure you want to delete this repository?', function(res) {
				if(res) {
					self.sync_delgdrive(repo);
				}
			});
	    },
		
		init_inpage_alert: function (msg_body, msg_div) {
			_msg_body = msg_body;
			_msg_div = msg_div;
		},

    	inpage_alert: function (msg_level, msg_body) {
    		if(null == _msg_body) return;
    		
    		_msg_body.html(msg_body);
    		_msg_div.removeClass("alert-success alert-info alert-warning alert-danger");
    		_msg_div.addClass("alert-"+msg_level);
    		_msg_div.show();
    	},
    	
    	hide_inpage_alert: function () {
    		_msg_div.hide();
    	},
    	
    	logout_at_browser: function () {
			for (var it in $.cookie()) {
				if(["sessname", "hostshell", "hostupload", "hostipnb", "sign", "juliabox"].indexOf(it) > -1) {
					$.removeCookie(it);
				}
			}
			top.location.href = '/';
			top.location.reload(true);    		
    	},

		do_logout: function () {
			s = function(res) {};
			f = function() {};
    		self.comm('/hostadmin/', 'GET', { 'logout' : 'me' }, s, f);
		},

    	logout: function () {
			s = function(res) { self.logout_at_browser(); };
			f = function() { self.logout_at_browser(); };
    		self.popup_confirm('Logout from JuliaBox?', function(res) {
    			if(res) {
    			    self.comm('/hostadmin/', 'GET', { 'logout' : 'me' }, s, f);
    			}
    		});
    	},
    	
    	inform_logged_out: function () {
    		if(!_loggedout) {
	    		_loggedout = true;
	    		self.popup_alert("Your session has terminated / timed out. Please log in again.", function() { self.logout_at_browser(); });
    		}
    	},

		popup_alert: function(msg, fn) {
			bootbox.alert(msg, fn);
		},
		
		popup_confirm: function(msg, fn) {
			bootbox.confirm(msg, fn);
		},
		
		lock_activity: function() {
			_locked += 1;
			if(_locked == 1) {
				//$("#modal-overlay").show();
				$("#modal-overlay").fadeIn();				
			}
		},
		
		unlock_activity: function() {
			_locked -= 1;
			if(_locked == 0) {
				$("#modal-overlay").hide();				
			}
		},
	};
	
	return self;
})(jQuery, _);


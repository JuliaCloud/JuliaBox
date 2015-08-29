var APIAdmin = (function($, _, undefined){
	var _inop = false;

	var self = {
		is_valid_url: function (url) {
    		return /^(https?|s?ftp):\/\/(((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:)*@)?(((\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5]))|((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.?)(:\d*)?)(\/((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)+(\/(([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)*)*)?)?(\?((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)|[\uE000-\uF8FF]|\/|\?)*)?(#((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)|\/|\?)*)?$/i.test(url);
		},

		is_valid_name: function (name) {
			return /^[a-zA-Z0-9_\-\.]+$/.test(name);
		},

		create_api: function (api_name, cmd, description, oncreate) {
        	if(self._inop) {
        		return;
        	}

        	api_name = $.trim(api_name);
        	cmd = $.trim(cmd);
        	description = $.trim(description);

        	if(!self.is_valid_url(description)) {
        		JuliaBox.popup_alert("Invalid URL specified for the description link.");
        		return;
        	}
        	if(!self.is_valid_name(api_name)) {
        		JuliaBox.popup_alert("Invalid API name specified.");
        		return;
        	}
        	if(cmd.length == 0) {
        		JuliaBox.popup_alert("Command not specified.");
        		return;
        	}

            s = function(res) {
            	if (res.code == 0) {
            		if(oncreate) {
            			oncreate();
            		}
            	}
            	else {
					if (res.data) {
						JuliaBox.popup_alert("Error creating API. " + res.data);
					}
					else {
						JuliaBox.popup_alert("Unknown error creating API.");
					}
            	}
            };
            f = function() {
				JuliaBox.popup_alert("Communication error while creating API.");
            };
            self._inop = true;
            params = {
            	'mode': 'create',
            	'api_name': api_name,
            	'cmd': cmd,
            	'description': description
            };
            JuliaBox.comm('/jboxplugin/api_admin/', 'GET', params, s, f);
            self._inop = false
		},

		delete_api: function (api_name, ondelete) {
        	if(self._inop) {
        		return;
        	}
            s = function(res) {
            	if (res.code == 0) {
            		if(ondelete) {
            			ondelete();
            		}
            	}
            	else {
					if (res.data) {
						JuliaBox.popup_alert("Error deleting API. " + res.data);
					}
					else {
						JuliaBox.popup_alert("Unknown error deleting API.");
					}
            	}
            };
            f = function() {
				JuliaBox.popup_alert("Communication error while deleting API.");
            };

			self._inop = true;
			JuliaBox.popup_confirm('Delete API specification for ' + api_name + '?', function(res) {
				self._inop = false;
				if(res) {
					params = {
						'mode' : 'delete',
						'api_name': api_name
					};
					JuliaBox.comm('/jboxplugin/api_admin/', 'GET', params, s, f);
				}
			});
		},

        get_apis: function (cb_success, cb_failure) {
        	if(self._inop) {
        		return;
        	}
            s = function(res) {
            	if (res.code == 0) {
            	    cb_success(res.data)
            	}
            	else {
            	    cb_failure(res.data)
            	}
            };
            f = function() {
                cb_failure(null)
            };
            JuliaBox.comm('/jboxplugin/api_admin/', 'GET', { 'mode' : 'info' }, s, f, dolock=false);
        },

        enable_apis: function () {
        	if(self._inop) {
        		return;
        	}
            s = function(res) {
            	if (res.code == 0) {
            	    JuliaBox.popup_alert("API publishing is now enabled for your account. Logout and login again to be able to publish APIs.");
            	}
            	else {
            	    JuliaBox.popup_alert("Could not enable APIs for your account. " + res.data);
            	}
            };
            f = function() {
            	JuliaBox.popup_alert("Could not enable APIs for your account. Please contact JuliaBox administrator.");
            };
            JuliaBox.comm('/jboxplugin/api_admin/', 'GET', { 'mode' : 'enable' }, s, f);
        }
    };
	return self;
})(jQuery, _);
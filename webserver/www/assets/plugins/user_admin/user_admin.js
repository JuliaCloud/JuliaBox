var UserAdmin = (function($, _, undefined){
	var _inop = false;

	var self = {
		update: function (user_id, attribs, onupdate) {
        	if(self._inop) {
        		return;
        	}
            s = function(res) {
            	if (res.code == 0) {
            		if(onupdate) {
            			onupdate();
            		}
            	}
            	else {
					if (res.data) {
						JuliaBox.popup_alert("Error updating user. " + res.data);
					}
					else {
						JuliaBox.popup_alert("Unknown error updating user.");
					}
            	}
            };
            f = function() {
				JuliaBox.popup_alert("Communication error while updating user.");
            };

			self._inop = true;
			JuliaBox.popup_confirm('Update user ' + user_id + '?', function(res) {
				self._inop = false;
				if(res) {
					params = {
						'mode' : 'update',
						'user_id': user_id
					};
					for(n in attribs) {
						params[n] = attribs[n];
					}
					JuliaBox.comm('/jboxplugin/user_admin/', 'POST', params, s, f);
				}
			});
		},

        get: function (user_id, cb_success) {
        	if(self._inop) {
        		return;
        	}
            s = function(res) {
            	if (res.code == 0) {
            	    cb_success(res.data)
            	}
            	else {
            		JuliaBox.popup_alert("Error fetching user. " + res.data);
            	}
            };
            f = function() {
            	JuliaBox.popup_alert("Unknown error fetching user.");
            };
            JuliaBox.comm('/jboxplugin/user_admin/', 'GET', {'mode': 'fetch', 'user_id':  user_id}, s, f, dolock=true);
        }
    };
	return self;
})(jQuery, _);
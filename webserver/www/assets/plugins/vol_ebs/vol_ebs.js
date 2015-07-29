var DataVolEBS = (function($, _, undefined){
	var _inop = false;

	var self = {
        attach: function (onstrt) {
            s = function(res) {
            	if (res.code == 0) {
            	    resp = res.data
            		JuliaBox.popup_alert("Attaching data volume.");
            		if(onstrt){
            			onstrt();
            		}
            	}
            	else {
					if (res.data) {
						JuliaBox.popup_alert("Error attaching data volume. " + res.data);
					}
					else {
						JuliaBox.popup_alert("Unknown error attaching data volume.");
					}
            	}
            };
            f = function() {
				JuliaBox.popup_alert("Communication error while attaching data volume.");
            };
            self._inop = true;
            var msg = 'Attach your data disk?';
    		JuliaBox.popup_confirm(msg, function(res) {
            	self._inop = false;
    			if(res) {
					JuliaBox.comm('/jboxplugin/ebsdatavol/', 'GET', { 'action': 'attach' }, s, f);
				}
			});
        },

        detach: function (onstrt) {
            s = function(res) {
            	if (res.code == 0) {
            	    resp = res.data
            		JuliaBox.popup_alert("Detaching data volume.");
            		if(onstrt){
            			onstrt();
            		}
            	}
            	else {
					if (res.data) {
						JuliaBox.popup_alert("Error detaching data volume. " + res.data);
					}
					else {
						JuliaBox.popup_alert("Unknown error detaching data volume.");
					}
            	}
            };
            f = function() {
				JuliaBox.popup_alert("Communication error while detaching data volume.");
            };
            self._inop = true;
            var msg = 'Detach your data disk?';
    		JuliaBox.popup_confirm(msg, function(res) {
            	self._inop = false;
    			if(res) {
					JuliaBox.comm('/jboxplugin/ebsdatavol/', 'GET', { 'action': 'detach' }, s, f);
				}
			});
        },

        volume_status: function (cb_success, cb_failure) {
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
            JuliaBox.comm('/jboxplugin/ebsdatavol/', 'GET', { 'action': 'status' }, s, f, dolock=false);
        }
	};
	return self;
})(jQuery, _);
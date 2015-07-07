var Parallel = (function($, _, undefined){
	var _inclusterop = false;

	var self = {
        cluster_start: function (ninsts, avzone, spot_price, onstrt) {
            s = function(res) {
            	if (res.code == 0) {
            	    resp = res.data
            		JuliaBox.popup_alert("Requested cluster for " + ninsts + " instance(s).");
            		if(onstrt){
            			onstrt();
            		}
            	}
            	else {
					if (res.data) {
						JuliaBox.popup_alert("Error configuring cluster. " + res.data);
					}
					else {
						JuliaBox.popup_alert("Unknown error configuring cluster.");
					}
            	}
            };
            f = function() {
				JuliaBox.popup_alert("Communication error while configuring cluster.");
            };
            self._inclusterop = true;
            var msg = 'Start a cluster of ' + ninsts;
            if(spot_price > 0) {
            	msg += ' spot instance(s) at $' + spot_price + ' per instance per hour?'
            }
            else {
            	msg += ' regular instance(s)?'
            }
    		JuliaBox.popup_confirm(msg, function(res) {
            	self._inclusterop = false;
    			if(res) {
					JuliaBox.comm('/jboxplugin/par/', 'GET', { 'cluster':'create', 'ninsts':ninsts, 'avzone':avzone, 'spot_price':spot_price }, s, f);
				}
			});
        },

        cluster_stop: function (interactive, onstop) {
        	interactive = typeof interactive !== 'undefined' ? interactive : true;
            s = function(res) {
            	if (res.code == 0) {
            		if(interactive) {
            			JuliaBox.popup_alert("Requested cluster termination.");
            		}
            		if(onstop) {
            			onstop();
            		}
            	}
            	else {
					if (res.data) {
						JuliaBox.popup_alert("Error terminating cluster. " + res.data);
					}
					else {
						JuliaBox.popup_alert("Unknown error terminating cluster.");
					}
            	}
            };
            f = function() {
				JuliaBox.popup_alert("Communication error while terminating cluster.");
            };
            if(interactive) {
            	self._inclusterop = true;
				JuliaBox.popup_confirm('Terminate the cluster?', function(res) {
					self._inclusterop = false;
					if(res) {
						JuliaBox.comm('/jboxplugin/par/', 'GET', { 'cluster' : 'terminate' }, s, f);
					}
				});
            }
            else {
            	JuliaBox.comm('/jboxplugin/par/', 'GET', { 'cluster' : 'terminate' }, s, f, dolock=false);
            }
        },

        cluster_status: function (cb_success, cb_failure) {
        	if(self._inclusterop) {
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
            JuliaBox.comm('/jboxplugin/par/', 'GET', { 'cluster' : 'status' }, s, f, dolock=false);
        },

    	addcluster: function (clustername) {
            s = function(res) {
            	if (res.code == 0) {
            		JuliaBox.popup_alert("Added cluster " + clustername + ". Created machinefile at " + res.data);
            	}
            	else {
					if (res.data) {
						JuliaBox.popup_alert("Error adding cluster. " + res.data);
					}
					else {
						JuliaBox.popup_alert("Error adding cluster " + clustername + ". Please ensure it is started and healthy.");
					}
            	}
            };
            f = function() {
				JuliaBox.popup_alert("Error adding cluster " + clustername + ". Please ensure it is started and healthy.");
            };
            JuliaBox.comm('/jboxplugin/par/', 'GET', { 'addcluster' : clustername }, s, f);
    	}
	};
	return self;
})(jQuery, _);
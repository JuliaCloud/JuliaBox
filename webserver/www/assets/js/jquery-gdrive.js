(function($) {
	var result_target = '';
	var picker = null;
	var gopts = {
		'devkey': null, //api key
		'appid': null,
		'user': null,
		'scope': 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/drive',
		'authtok': null,
		'init_stage': 0,
		'width': 800,
		'height': 400,
		'callback': set_results,
		'debug': false
	};
	
	var dlgopts = {};
	
	function do_auth(callback) {
		google_api_load();
		if((gopts.authtok != null) && (gopts.user != null)) {
			if(callback) callback();
			return;
		}
		if(gopts.debug) console.log("invoking authorization");
		gapi.auth.authorize({
			'client_id': gopts.appid,
			'scope': gopts.scope,
			'immediate': false
			},
			function(auth_result){
				if (auth_result && !auth_result.error) {
					gopts.authtok = auth_result.access_token;
					get_user_id(callback);
  				}
				else {
					console.log("Could not authenticate you with Google");
				}
			});
	};
	
	function get_user_id(callback) {
		gapi.client.setApiKey(gopts.devkey);
		gapi.client.load('oauth2', 'v2', function(){
			gapi.client.oauth2.userinfo.get().execute(function(resp) {
				gopts.user = resp.email;
				if(callback) callback();
			});
		});
	};
	
	function google_api_load() {
		if((gopts.init_stage & 3) == 3) return;
		if(!(gopts.init_stage & 1)) gapi.load('auth', {'callback': function(){
			gopts.init_stage |= 1;
		}});
		if(!(gopts.init_stage & 2)) gapi.load('picker', {'callback': function(){
			gopts.init_stage |= 2;
		}});
	};
	
	function set_results(target, data) {
		if (data.action == google.picker.Action.PICKED) {
			var doc = data.docs[0];
			var file_id = doc.id;
	        var url = doc[google.picker.Document.URL];
	        var filename = doc[google.picker.Document.NAME];
	        var fullpath = "gdrive://" + filename + "/" + file_id;
	        target.val(fullpath);
	        target.change();
		}
	};
	
	function show_dlg(target) {
		target.val('');
		var elem_opts = dlgopts[target.attr('id')];
		
		var view = new google.picker.DocsView(google.picker.ViewId.FOLDERS);
		view.setMode(google.picker.DocsViewMode.LIST);
		if(elem_opts.filter == 'application/vnd.google-apps.folder') {
			view.setSelectFolderEnabled(true);
			view.setMimeTypes('application/vnd.google-apps.folder');      	
		}
		
		var picker_builder = new google.picker.PickerBuilder()
							.enableFeature(google.picker.Feature.NAV_HIDDEN)
							.disableFeature(google.picker.Feature.MULTISELECT_ENABLED)
							.setAppId(gopts.appid)
							.addView(view)
							//.addView(new google.picker.View(google.picker.ViewId.FOLDERS))
							.setOAuthToken(gopts.authtok)
							.setDeveloperKey(gopts.devkey)
							.setCallback(function(data){
									gopts.callback(target, data);
								})
	          				.setSize(gopts.width, gopts.height)
	          				.setTitle(elem_opts.header);
		if(gopts.user != null) picker_builder.setAuthUser(gopts.user);
		picker = picker_builder.build();
		picker.setVisible(true);
		return picker;
	};
	
	$.fn.gdrive = function(action, options) {
		if(action === 'init') {
			gopts = $.extend(gopts, options);
			google_api_load();
			return this;
		}
		if(action === 'set') {
			return this.each(function(){
				var elem = $(this)
				var elemid = elem.attr('id');
				var elem_opts = $.extend($.extend(dlgopts[elemid], {'trigger': null, 'header': '', 'filter': ''}), options);
				dlgopts[elemid] = elem_opts;
				var trig_elem = (elem_opts.trigger == null) ? $(this) : elem_opts.trigger;
				trig_elem.click(function(){
					do_auth(function() {
						picker = show_dlg(elem);
					});
				});
			});
		}
		if(action === 'show') {
			var elem = this;
			do_auth(function() {
				picker = show_dlg(elem);
			});
			return this;
		}
		if(action === 'hide') {
			if(null != picker) {
				picker.setVisible(false);
				picker = null;
			}
			return this;
		}
		if(action == 'token') {
			return gopts.authtok;
		}
		if(action == 'user') {
			return gopts.user;
		}
        if(action == 'setauth') {
            var elem_opts = $.extend({'uid': null, 'token': null, 'callback': null}, options);
            var target_uid = elem_opts.uid;
            var target_tok = elem_opts.token;
            var callback = elem_opts.callback;
            do_auth(function() {
                if(null != target_uid) $('#'+target_uid).val(gopts.user);
                if(null != target_tok) $('#'+target_tok).val(gopts.authtok);
                if(null != callback) callback();
            });
        }
		if(action == 'debug') {
			return gopts;
		}
	};
	
}(jQuery));

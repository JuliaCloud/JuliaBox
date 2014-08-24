<html lang="en">
<head>
	<meta charset="utf-8" />
	<title>{{sessname}} &mdash; JuliaBox</title>

	<link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    {% if cfg["env_type"] == "dev" %}
    <link rel="stylesheet/less" type="text/css" href="/assets/css/base.less" />
    <script src="//cdnjs.cloudflare.com/ajax/libs/less.js/1.7.3/less.min.js"></script>
    {% else %}
    <link rel="stylesheet" type="text/css" href="/assets/css/base.css" />
    {% end %}
	
    <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.2.0/bootbox.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/jquery-cookie/1.4.1/jquery.cookie.min.js"></script>
    <script src="//apis.google.com/js/client.js"></script>
    <script src="/assets/js/jquery-gdrive.js"></script>
    <script src="/assets/js/juliabox.js"></script>
    <script type="text/javascript" src="//use.typekit.net/cpz5ogz.js"></script>
    <script type="text/javascript">try{Typekit.load();}catch(e){}</script>
    <script type="text/javascript">
		$(document).ready(function() {
			var tab_init = {
				'#ijulia': {'status': true},
				'#console': {'status': false, 'content': '<iframe src="/hostshell/" id="console-frame" frameborder="0" height="100%" width="100%"></iframe>'},
				'#docs': {'status': false, 'content': '<iframe id="docs-frame" src="http://julia.readthedocs.org/en/latest/" frameborder="0" height="100%" width="100%"></iframe>'},
				'#admin': {'status': false, 'content': '<iframe src="/hostadmin/" id="admin-frame" frameborder="0" height="100%" width="100%"></iframe>'},
				'#filesync': {'status': false, 'content': '<iframe src="/hostupload/sync" id="filesync-frame" frameborder="0" height="100%" style="float: left" width="100%"></iframe>'},
				'#fileman': {'status': false, 'content': '<iframe src="/hostupload/" id="upload-frame" frameborder="0" height="100%" style="float: left" width="100%"></iframe>'}
			};
			
			$('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
				var target = $(e.target).attr("href");
				if(!tab_init[target].status) {
					$(target).append(tab_init[target].content);
					tab_init[target].status = true;
				}
			});	
			
			$('#logout_btn').click(function(event){
				event.preventDefault();
				JuliaBox.logout();
			});
            
        	JuliaBox.init_inpage_alert($('#msg_body'), $('#in_page_alert'));
	    	{%if None != creds %}
	    	JuliaBox.init_gauth_tok("{{creds}}");
            $().gdrive('init', {
                'devkey': 'AIzaSyADAHw6De_orDrpcP9_hC9utXqESDpaut8',
                'appid': '64159081293-43o683d0pcgdq6gn7ms86liljoeklvh3.apps.googleusercontent.com',
                'authtok': '{{authtok}}',
               	'user': '{{user_id}}'
            });
	    	{% end %}
	    	var myVar = setInterval(function(){JuliaBox.send_keep_alive()}, 60000);
        });
    </script>  
</head>
{% set admin_user = (sessname in cfg["admin_sessnames"]) or (cfg["admin_sessnames"] == []) %}
<body>
    <div class="header-wrap">
        <div class="container">
            <div class="row header-row">
                <div class="col-md-1">
                    <img class="brand-logo" src="/assets/img/juliacloudlogo.png"></img>
                </div>
                <div class="brand-title col-md-2">JuliaBox<sup>&nbsp;&beta;</sup></div>
                <div class="col-md-9">
                    <ul class="jb-nav nav nav-pills" role="tablist">
                    <li class="active"><a href="#ijulia" data-toggle="tab">IJulia</a></li>
                    <li><a href="#console" data-toggle="tab">Console</a></li>
                    <li><a href="#fileman" data-toggle="tab">File Manager</a></li>
                    <li><a href="#filesync" data-toggle="tab">Sync &amp; Share</a></li>
{% if admin_user %}
                    <li><a href="#admin" data-toggle="tab">Admin</a></li>
{% else %}
                    <li><a href="#admin" data-toggle="tab">Account</a></li>
{% end %}
                    <li><a href="#docs" data-toggle="tab">Docs</a></li>
                    <li><a href="#" id="logout_btn">Logout</a></li>
                    </ul>
                </div>
            </div><!-- row -->
            <div style="clear:both;"></div>
        </div>
    </div>

    <div class="tab-content modules">    	
        <div id="ijulia" class="tab-pane active">
            <iframe src="/hostipnbsession/" id="ijulia-frame" frameborder="0" height="100%" width="100%"></iframe>
        </div>
        <div id="console" class="tab-pane container"></div>
        <div id="docs" class="tab-pane container"></div>
        <div id="filesync" class="tab-pane container"></div>
        <div id="fileman" class="tab-pane container"></div>
        <div id="admin" class="tab-pane container"></div>
    </div>

	<div id="in_page_alert" class="alert alert-warning alert-dismissible container juliaboxmsg" role="alert" style="display: none;">
  		<button type="button" class="close" data-dismiss="alert"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
  		<span id="msg_body"></span>
	</div>		
</body>
</html>


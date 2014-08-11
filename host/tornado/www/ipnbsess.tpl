<html lang="en">
<head>
	<meta charset="utf-8" />
	<title>{{sessname}} &mdash; JuliaBox</title>

	<link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
	<link href='//fonts.googleapis.com/css?family=Raleway|Inconsolata' rel='stylesheet' type='text/css'>
	<link rel="stylesheet" type="text/css" href="/assets/css/base.css" />
	
    <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.2.0/bootbox.min.js"></script>
    <script src="//apis.google.com/js/client.js"></script>
    <script src="/assets/js/jquery-gdrive.js"></script>
    <script src="/assets/js/juliabox.js"></script>
    <script type="text/javascript">
		function inject_frame() {
			var frames = ["ijulia", "console"];
			for(var i=0, l=frames.length; i < l; i++) {
				var frame = $("#" + frames[i] +"-frame");
				head = frame.contents().find("head");
				frame.ready(function () {
					head.append('<link rel="stylesheet" type="text/css" href="/assets/css/frames.css"/>');
        			frame.show();
    			});
  			}
		};
		
		$(window).load(function(){
        	inject_frame();			
		});
		
		$(document).ready(function() {
            $().gdrive('init', {
                'devkey': 'AIzaSyADAHw6De_orDrpcP9_hC9utXqESDpaut8',
                'appid': '64159081293-43o683d0pcgdq6gn7ms86liljoeklvh3.apps.googleusercontent.com'
            });
            
        	JuliaBox.init_inpage_alert($('#msg_body'), $('#in_page_alert'));
	    	{%if None != creds %}
	    	JuliaBox.init_gauth_tok("{{creds}}");
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
                <div class="brand-header">
                    <img class="brand-logo" src="/assets/img/juliacloudlogo.png"></img>
                    <span class="brand-title">JuliaBox</span>
                </div>
                <div class="col-md-9">
                    <ul class="nav nav-pills" role="tablist">
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
        <div id="console" class="tab-pane container">
            This is a bash session. If you cannot see a blinking cursor below, please right-click, "reset" the terminal and hit "enter". <br/>
            Type "julia" to start a Julia REPL session.<br/><br/>
        
            <iframe src="/hostshell/" id="console-frame" frameborder="0" height="86%" width="100%"></iframe>
        </div>
        <div id="docs" class="tab-pane container">
            <iframe id="docs-frame" src="http://julia.readthedocs.org/en/latest/" frameborder="0" height="100%" width="100%"></iframe>
        </div>
        <div id="filesync" class="tab-pane container">
            <iframe src="/hostupload/sync" id="filesync-frame" frameborder="0" height="86%" style="float: left" width="100%"></iframe>
        </div>
        <div id="fileman" class="tab-pane container">
            <iframe src="/hostupload/" id="upload-frame" frameborder="0" height="86%" style="float: left" width="100%"></iframe>
        </div>
        <div id="admin" class="tab-pane container">
            <iframe src="/hostadmin/" id="admin-frame" frameborder="0" height="100%" width="100%"></iframe>
        </div>
    </div>

	<div id="in_page_alert" class="alert alert-warning alert-dismissible container juliaboxmsg" role="alert" style="display: none;">
  		<button type="button" class="close" data-dismiss="alert"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
  		<span id="msg_body"></span>
	</div>		
</body>
</html>


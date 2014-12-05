<html lang="en">
<head>
	<meta charset="utf-8" />
	<title>JuliaBox &mdash; {{user_id}}</title>
	<link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
	<link rel="stylesheet" href="/assets/css/icons.css" />
    <link rel="stylesheet" type="text/css" href="/assets/css/base.css" />

	<script src="//cdnjs.cloudflare.com/ajax/libs/underscore.js/1.7.0/underscore-min.js"></script>

    <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.3.0/bootbox.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/jquery-cookie/1.4.1/jquery.cookie.min.js"></script>
    <script src="//apis.google.com/js/client.js"></script>
    <script src="/assets/js/jquery-gdrive.js"></script>
    <script src="/assets/js/juliabox.js"></script>
    <script type="text/javascript" src="//use.typekit.net/cpz5ogz.js"></script>
    <script type="text/javascript">try{Typekit.load();}catch(e){}</script>
    <script>
        var monitor_loading_timer;

    	function monitor_loading() {
	        $.ajax({
	        	url: '/?monitor_loading=yes',
	        	type: 'GET',
	        	success: function(res) {
	        	    if(res.code != 0) {
	        	        clearInterval(monitor_loading_timer);
	        	        top.location.href = '/';
	        	    }
	        	},
	        	error: function(res) {
	        	    clearInterval(monitor_loading_timer);
	        	    top.location.href = '/';
	        	}
	        });
	    };

        $(document).ready(function() {
            monitor_loading_timer = setInterval(monitor_loading, 2000);
        });
    </script>
</head>
<body>
    <div class="header-wrap">
        <div class="container">
            <div class="row header-row">
                <div class="logo-and-name">
                    <img class="brand-logo" src="/assets/img/juliacloudlogo.png"></img>
                    <div class="brand-title hidden-xs hidden-sm">JuliaBox<sup> beta</sup></div>
		</div>
                <div class="navicons">
                    <ul class="jb-nav nav nav-tabs" role="tablist">
                    <li class="active"><a href="#"><em class="icon-uniE600"></em><span>IJulia</span></a></li>
                    <li><a href="#"><em class="icon-uniE603"></em><span>Console</span></a></li>
                    <li><a href="#"><em class="icon-uniE601"></em><span>Files</span></a></li>
                    <li><a href="#"><em class="icon-uniE602"></em><span>Sync</span></a></li>
                    <li class="pull-right"><a href="#"><em class="icon-uniE604"></em></a></li>
                    <li class="pull-right"><a href="#"><em class="icon-uniE605"></em></a></li>
                    <li class="pull-right"><a href="#"><em class="icon-uniE607"></em></a></li>
                    </ul>
                </div>
            </div><!-- row -->
            <div style="clear:both;"></div>
        </div>
    </div>

    <div class="container">
        <table width="100%" height="100%" align="center" valign="middle">
            <tr width="100%" height="100%" align="center" valign="middle">
                <td width="100%" height="100%" align="center" valign="middle">
                    <img src="/assets/img/loading.gif" width="64" height="64"/><br/><br/>
                    <div id="loading_state">Creating a JuliaBox instance just for you!</div>
                </td>
            </tr>
        </table>
    </div>
</body>
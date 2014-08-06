<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>IPNB Session {{ d["sessname"] }} </title>
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    <link href='http://fonts.googleapis.com/css?family=Raleway|Inconsolata' rel='stylesheet' type='text/css'>
    <link rel="stylesheet" type="text/css" href="/assets/css/frames.css">
    <style>
    	pre {
		    white-space: pre-wrap;       /* CSS 3 */
		    white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
		    white-space: -pre-wrap;      /* Opera 4-6 */
		    white-space: -o-pre-wrap;    /* Opera 7 */
		    word-wrap: break-word;       /* Internet Explorer 5.5+ */
		}
    </style>

	<script src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
	<script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
	<script src="//cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.2.0/bootbox.min.js"></script>
	<script type="text/javascript">
	    function sendKeepAlive() {
	        var xmlhttp=new XMLHttpRequest();
	        xmlhttp.open("GET","/ping/",true);
	        xmlhttp.send();
	    }
	    var myVar=setInterval(function(){sendKeepAlive()}, 60000);
	    
	    $(document).ready(function() {
	    	$('#showsshkey').click(function(event){
	    		event.preventDefault();
	    		$.ajax({
	    			url: "/hostupload/sshkey",
	    			success: function(sshkey) {
	    				bootbox.alert('<pre>' + sshkey.data + '</pre>');
	    			},
	    			error: function() {
	    				bootbox.alert("Oops. Unexpected error while retrieving the ssh key.<br/><br/>Please try again later.");
	    			}
	    		});
	    	});
	    	
	    	$('#upgrade').click(function(event){
	    		event.preventDefault();
	    		bootbox.confirm("Newer JuliaBox versions come with more recent versions of Julia and packages.<br/><br/>Files saved in your account would be available after the upgrade. Any unsaved changes would be lost. You will be logged out for the upgrade and will need to log in again.<br/><br/>Please confirm if you wish to upgrade to the latest JuliaBox version.", function(result){
	    			if(!result) return;
	    			location.href = "/hostadmin?upgrade_id=me";
	    		});
	    	});
	    });
	</script>    
</head>
<body>

<h3>Profile &amp; session info:</h3>
Profile Initialized at: {{d["created"]}} <br/>
Current session started at: {{d["started"]}} <br/>
SSH Public Key: <a href="#" id="showsshkey">View</a><br/>

<h3>JuliaBox version:</h3>
You are on the latest JuliaBox version: {{d["juliaboxver"]}} <br/>
{% if d["upgrade_available"] != None %}
Your JuliaBox version: {{d["juliaboxver"]}} <br/>
Latest JuliaBox version: {{d["upgrade_available"]}}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="#" id="upgrade">upgrade</a>
{% end %}
<br/>

{% if d["admin_user"] %}
    <hr/>
    <h3>Administer this installation</h3>
    <hr/>
    <a href="/hostadmin/" class="btn btn-primary btn-lg active" role="button">Refresh</a>
    <a href="/hostadmin/?stop_all=1" class="btn btn-primary btn-lg active" role="button">Stop all containers</a>
    
    <br/><br/>

    <h3> Config </h3>
    <table class="table table-striped">
        <tr><th>Parameter</th><th>Value</th></tr>
        {% for k,v in cfg.iteritems() %}
            {% if k not in ['dummy', 'sesskey'] %}
                <tr><td>{{ k }}</td><td>{{ str(v) }} </td></tr>
            {% end %}
        {% end %}
    </table>

    <br/><br/>
    
    {% for section in d["sections"] %}
        <h3> {{ section[0] }} containers </h3>
        <table class="table table-striped">
            <tr><th>Id</th><th>Status</th><th>Name</th><th colspan="2">Action</th></tr>
            {% for o in section[1] %}
                <tr>
                    <td> {{ o["Id"] }} </td>
                    <td>{{ o["Status"] }} </td>
                    <td>{{ o["Name"] }} </td>
                    <td><a href="/hostadmin/?stop_id={{ o['Id'] }}">Stop</a></td>
                    <td><a href="/hostadmin/?delete_id={{ o['Id'] }}">Delete</a></td>
                </tr>
            {% end %}
        </table>
        <br/><br/>
    {% end %}
{% end %}
</body>
</html>


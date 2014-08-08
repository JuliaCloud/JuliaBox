<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>IPNB Session {{ d["sessname"] }} </title>
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    <link href='http://fonts.googleapis.com/css?family=Raleway|Inconsolata' rel='stylesheet' type='text/css'>
    <link rel="stylesheet" type="text/css" href="/assets/css/frames.css">

	<script src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
	<script type="text/javascript">
	    $(document).ready(function() {
	    	$('#showsshkey').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_ssh_key();
	    	});
	    	
	    	$('#upgrade').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.popup_confirm("Newer JuliaBox versions come with more recent versions of Julia and packages.<br/><br/>Files saved in your account would be available after the upgrade. Any unsaved changes would be lost. You will be logged out for the upgrade and will need to log in again.<br/><br/>Please confirm if you wish to upgrade to the latest JuliaBox version.", function(result){
	    			if(result) {
	    				parent.JuliaBox.inpage_alert('info', 'Initiating backup and upgrade of your JuliaBox instance. Please wait...');
	    				parent.JuliaBox.do_upgrade();
	    			}
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
{% if d["upgrade_available"] != None %}
Your JuliaBox version: {{d["juliaboxver"]}} <br/>
Latest JuliaBox version: {{d["upgrade_available"]}}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="#" id="upgrade">upgrade</a><br/>
{% else %}
You are on the latest JuliaBox version: {{d["juliaboxver"]}} <br/>
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


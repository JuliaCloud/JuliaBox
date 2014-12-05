<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>JuliaBox &mdash; {{d["user_id"]}}</title>
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    <link rel="stylesheet" type="text/css" href="/assets/css/frames.css">

    <script type="text/javascript" src="//use.typekit.net/cpz5ogz.js"></script>
    <script type="text/javascript">try{Typekit.load();}catch(e){}</script>

	<script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
	<script type="text/javascript">
		var disp_timer;
		function secs_to_str(secs) {
			if(secs <= 60) return "0 Minutes";

		    var days = Math.floor(secs / 60 / (60 * 24));
		    var hours = Math.floor((secs - days * 24 * 60 * 60) / (60 * 60));
		    var mins = Math.floor((secs - days * 24 * 60 * 60 - hours * 60 * 60) / 60);

		    var out_str = "";
		    if(days > 0) out_str = (days + " Days ");
		    if(hours > 0) out_str = out_str + (hours + " Hours ");
		    if((hours == 0) || (mins > 0)) out_str = out_str + (mins + " Minutes ");
		    return out_str;
		};
		function show_time_remaining() {
		    var datetime = new Date('{{d["allowed_till"]}}').getTime();
		    var now = new Date().getTime();
		    var remain_secs = Math.floor((datetime - now)/1000);
		    var expire = {{d["expire"]}};
		    if(remain_secs > expire) remain_secs = expire;
		    var remain = secs_to_str(remain_secs);
		    
		    if(expire > 0) {
			    total = secs_to_str({{d["expire"]}});
			    if(remain_secs >= expire) remain = total;
			    
			    $('#disp_time_remaining').html(remain + " (of allotted " + total + ")");
			    
			    if(remain_secs < 5 * 60) {		    
				    if (remain_secs <= 0) {
				    	clearInterval(disp_timer);
				    	parent.JuliaBox.inform_logged_out();
				    }
				    else {
			    		parent.JuliaBox.inpage_alert('info', 'Your session has only ' + remain + ' of allotted time remaining.');			    	
				    }
			    }		    	
		    }
		    else {
		    	$('#disp_date_allowed_till').html("unlimited");
		    	$('#disp_time_remaining').html("unlimited");
		    	clearInterval(disp_timer);
		    }
		};
		
		function size_with_suffix(sz) {
	    	var suffix = "";
	    	if(sz >= 1000000000) {
	    		sz = (sz * 1.0 / 1000000000);
	    		suffix = " GB";
	    	}
	    	else {
	    		sz = (sz * 1.0 / 1000000);
	    		suffix = " MB";
	    	}
	    	return ((Math.round(sz) === sz) ? Math.round(sz).toFixed(0) : sz.toFixed(2)) + suffix;
		};
		
	    $(document).ready(function() {
	    	$('#showsshkey').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_ssh_key();
	    	});

{% if d["manage_containers"] %}
            $('#showcfg').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_config();
	    	});

	    	$('#showuserstats').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_stats('stat_users', 'Users');
	    	});

	    	$('#showvolumestats').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_stats('stat_volmgr', 'Volumes');
	    	});

	    	$('#showinstanceloads').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_instance_info('load', 'Instance Loads (percent)');
	    	});
{% end %}

	    	$('#disp_date_init').html((new Date('{{d["created"]}}')).toLocaleString());
	    	$('#disp_date_start').html((new Date('{{d["started"]}}')).toLocaleString());
	    	$('#disp_date_allowed_till').html((new Date('{{d["allowed_till"]}}')).toLocaleString());
	    	
	    	$('#disp_mem').html(size_with_suffix({{d["mem"]}}));
	    	$('#disp_disk').html(size_with_suffix({{d["disk"]}}));
	    	
	    	show_time_remaining();
	    	disp_timer = setInterval(show_time_remaining, 60000);
	    });
	</script>
</head>
<body>

<h3>Profile &amp; session info:</h3>
<table class="table">
	<tr><td>Logged in as:</td><td>{{d["user_id"]}}</td></tr>
	<tr><td>Session initialized at:</td><td><span id='disp_date_init'></span></td></tr>
	<tr><td>Session last started at:</td><td><span id='disp_date_start'></span></td></tr>
	<tr><td>Session allowed till:</td><td><span id='disp_date_allowed_till'></span></td></tr>
	<tr><td>Time remaining:</td><td><span id='disp_time_remaining'> of {{d["expire"]}} secs</span></td></tr>	
	<tr><td>File Backup Quota:</td><td><span id='disp_disk'></span></td></tr>
	<tr><td>Allocated Memory:</td><td><span id='disp_mem'></span></td></tr>
	<tr><td>Allocated CPUs:</td><td>{{d["cpu"]}}</td></tr>
	<tr><td>SSH Public Key:</td><td><a href="#" id="showsshkey">View</a></td></tr>
</table>

<h3>JuliaBox version:</h3>
JuliaBox version: {{d["juliaboxver"]}} <br/>
<br/>

{% if d["show_report"] %}
    <h3 id="stats">System statistics</h3>
    <p> Stats for the:
       {% if d["report_span"] == "day" %}
        <b>Day</b> | <a href="/hostadmin/?range=week#stats">Week</a>
       {% else %}
        <a href="/hostadmin/?range=day#stats">Day</a> | <b>Week</b>
       {% end %}
    </p>
    <table class="table table-striped">
        <tr><td>Number of sessions</td><td>{{d["report"]["session_count"]}}</td></tr>
        <tr><td>Average time spent</td><td>{{d["report"]["avg_time"]}}</td></tr>
    </table>
    <h3>Most used containers</h3>
    <table class="table table-striped">
      {% for x in d["report"]["images_used"] %}
        <tr><td>{{x["image_id"]}}</td><td>{{x["count"]}}</td></tr>
      {% end %}
    </table>

{% end %}

{% if d["manage_containers"] %}
    <hr/>
    <h3>Administer this installation</h3>
    <hr/>
    <a href="/hostadmin/" class="btn btn-primary btn-lg active" role="button">Refresh</a>
    <a href="/hostadmin/?stop_all=1" class="btn btn-primary btn-lg active" role="button">Stop all containers</a>
    
    <br/><br/>

    <table class="table">
        <tr><td>Users Statistics:</td><td><a href="#" id="showuserstats">View</a></td></tr>
        <tr><td>Volume Statistics:</td><td><a href="#" id="showvolumestats">View</a></td></tr>
        <tr><td>Configuration:</td><td><a href="#" id="showcfg">View</a></td></tr>
        <tr><td>Instance Loads:</td><td><a href="#" id="showinstanceloads">View</a></td></tr>
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


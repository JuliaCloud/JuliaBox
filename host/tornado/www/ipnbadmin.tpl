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

{% if (d["use_cluster"]) %}
		var instance_loc;
		var stopping = false;
		var cluster_start_time = 0;

		function show_cluster_state() {
			parent.JuliaBox.cluster_status(set_cluster_state, error_cluster_state);
		};

		function set_cluster_state(state) {
			instance_loc = state.config.instance_loc;
			$('#credits').html('$ ' + state.limits.credits);
			$('#cores_per_unit').html(state.config.instance_cores);
			if(!state.exists || state.inerror) {
				stopping = false;
				cluster_start_time = 0;
				$('.cluster_stopped').show();
				$('.cluster_running').hide();

				var cores_selector = $('#cluster_start_cores_selector');
				var price_selector = $('#price_per_core_selector');
				var options = '';

				cores_selector.empty();
				for(cores = state.config.instance_cores; cores <= state.limits.max_cores; cores += state.config.instance_cores) {
					options += '<option value="' + Math.round(cores/state.config.instance_cores) + '">' + cores + ' cores</option>';
				}
				cores_selector.append(options);

				price_selector.empty();
				var p1 = Math.max(state.config.instance_cost_range.median, state.config.instance_cost_range.avg);
				var p2 = Math.min(state.config.instance_cost_range.max, state.config.instance_cost);
				var spot = (p1+p2)/2
				spot = Math.round(spot * 100) / 100;

				options = '<option value="0">$ ' + state.config.instance_cost + ' (regular instance)</option>';
				options += '<option value="' + spot + '">$ ' + spot + ' (spot instance)</option>';
				price_selector.append(options);
			}
			else {
				$('.cluster_running').show();
				$('.cluster_stopped').hide();

				var active = state.instances.count;
				var desired = state.instances.desired_count;
				var price = state.instances.instance_cost;

				if((active > 0) && (desired == 0)) {
					stopping = true;
				}

				if((cluster_start_time == 0) && (active > 0)) {
					cluster_start_time = new Date().getTime();
				}

				if(cluster_start_time == 0) {
					$('#cluster_run_time').html(secs_to_str(0));
				}
				else {
					nowtime = new Date().getTime();
					tdiff = Math.round((nowtime - cluster_start_time)/1000);
					$('#cluster_run_time').html(secs_to_str(tdiff));
				}

				$('#cluster_active_cores').html(active * state.config.instance_cores);
				$('#cluster_desired_cores').html(desired * state.config.instance_cores);
				$('#instance_cost').html(price);
				$('#cores_per_unit1').html(state.config.instance_cores);
				if(stopping) {
					$('#cluster_stopping').show();
					$('#btn_cluster_stop').hide();
					if((active == 0) && (desired == 0)) {
						// cluster has stopped, terminate now
						parent.JuliaBox.cluster_stop(confirm=false, onstop=null);
					}
				}
				else {
					$('#cluster_stopping').hide();
					$('#btn_cluster_stop').show();
				}
			}
			$('#cs_state_unknown').hide();
			$('#cs_state').show();
		};

		function error_cluster_state(msg) {
			if(msg) {
				$('#cluster_err_msg').html('(' + msg + ')');
			}
			else {
				$('#cluster_err_msg').html("");
			}
			$('#cs_state_unknown').show();
			$('#cs_state').hide();
		};
{% end %}

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

	    	$('#jimg_switch').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.switch_julia_image($('#jimg_curr'), $('#jimg_new'));
	    	});

	    	$('#websocktest').click(function(event){
	    	    event.preventDefault();
	    	    parent.JuliaBox.websocktest();
	    	});

{% if (d["manage_containers"] or d["show_report"]) %}
	    	$('#showuserstats').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_stats('stat_users', 'Users');
	    	});

	    	$('#showsessionstats').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_stats('stat_sessions', 'Sessions');
	    	});

	    	$('#showvolumestats').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_stats('stat_volmgr', 'Volumes');
	    	});
{% end %}

{% if d["manage_containers"] %}
            $('#showcfg').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_config();
	    	});


	    	$('#showinstanceloads').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_instance_info('load', 'Instance Loads (percent)');
	    	});

	    	$('#showsessions').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_instance_info('sessions', 'Sessions');
	    	});
{% end %}

            parent.JuliaBox.set_julia_image_type($('#jimg_curr'), $('#jimg_new'), {{d["jimg_type"]}});
	    	$('#disp_date_init').html((new Date('{{d["created"]}}')).toLocaleString());
	    	$('#disp_date_start').html((new Date('{{d["started"]}}')).toLocaleString());
	    	$('#disp_date_allowed_till').html((new Date('{{d["allowed_till"]}}')).toLocaleString());
	    	
	    	$('#disp_mem').html(size_with_suffix({{d["mem"]}}));
	    	$('#disp_disk').html(size_with_suffix({{d["disk"]}}));
	    	
	    	show_time_remaining();
	    	disp_timer = setInterval(show_time_remaining, 60000);

{% if (d["use_cluster"]) %}
            $('#addcluster').click(function(event){
                event.preventDefault();
                parent.JuliaBox.addcluster($('#clustername').val());
            });

            $('#btn_cluster_start').click(function(event){
            	event.preventDefault();
            	var ninsts = $('#cluster_start_cores_selector').val();
            	var spot_price = $('#price_per_core_selector').val();
            	//alert("start cluster, ninsts:" + ninsts + ", spot_price:" + spot_price + " at " + instance_loc);
            	parent.JuliaBox.cluster_start(ninsts, instance_loc, spot_price, onstrt=function(){
            		//error_cluster_state("Cluster start requested");
            		show_cluster_state();
            	});
            });

            $('#btn_cluster_stop').click(function(event){
            	event.preventDefault();
            	//alert("stopping cluster");
            	parent.JuliaBox.cluster_stop(confirm=true, onstop=function(){
            		stopping = true;
            		//error_cluster_state("Cluster stop requested");
            		show_cluster_state();
            	});
            });

	    	show_cluster_state();
	    	cluster_state_timer = setInterval(show_cluster_state, 60000);
{% end %}
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
	<tr><td>Julia Image:</td><td><span id='jimg_curr'>precompiled packages</span> (<a href="#" id="jimg_switch"><small>switch to: <span id='jimg_new'>standard</span></small></a>)</td></tr>
	<tr><td>Network Connectivity Test:</td><td><a href="#" id="websocktest">Start</a></td></tr>
</table>

{% if (d["use_cluster"]) %}
<h3>Cluster:</h3>
<div id="cs_state_unknown">Retrieving cluster status...<br/><small><span id="cluster_err_msg"></span></small></div>
<table class="table" id="cs_state" style="display:none">
	<tr style="display:none"><td>Credits&nbsp;Remaining:</td><td><span id='credits'></span></td></tr>
	<tr class="cluster_stopped">
		<td>Start&nbsp;cluster:</td>
		<td>
			<select id='cluster_start_cores_selector'></select>
			at <select id='price_per_core_selector'></select>
			<input type="button" value="Start" id="btn_cluster_start" class="btn btn-primary"/>
			<br/>
			<small>
				Prices are per <span id='cores_per_unit'></span> cores per hour.<br/>
				Spot instances have a delay in getting the instances. They may also get terminated when spot prices rise beyond the selected price.
			</small>
		</td>
	</tr>
	<tr class="cluster_running cluster_stopping">
		<td>Cores&nbsp;allocated:</td>
		<td>
			<span id='cluster_active_cores'></span> of desired <span id='cluster_desired_cores'></span> cores<br/>
			at $ <span id="instance_cost"></span> per <span id='cores_per_unit1'></span> cores per hour.
		</td>
	</tr>
	<tr class="cluster_running"><td>Run&nbsp;time:</td><td><span id="cluster_run_time"></span></td></tr>
	<tr class="cluster_running"><td>Machinefile location:</td><td><span id='cluster_machinefile'>/home/juser/.juliabox/machinefile</span></td></tr>
	<tr class="cluster_running"><td>Terminate:</td><td><input type="button" value="Terminate" id="btn_cluster_stop" class="btn btn-primary"/><span id="cluster_stopping">terminating...</span></td></tr>
</table>
{% end %}

<h3>JuliaBox version:</h3>
JuliaBox version: {{d["juliaboxver"]}} <br/>
Julia version: 0.3.9 <br/>
<br/>
{% if (d["manage_containers"] or d["show_report"]) %}
    <hr/>
    <h3>System statistics{% if d["manage_containers"] %} &amp; administration{% end %}</h3>

    <table class="table">
        <tr><td>Session Statistics:</td><td><a href="#" id="showsessionstats">View</a></td></tr>
        <tr><td>Users Statistics:</td><td><a href="#" id="showuserstats">View</a></td></tr>
        <tr><td>Volume Statistics:</td><td><a href="#" id="showvolumestats">View</a></td></tr>
{% if d["manage_containers"] %}
        <tr><td>Configuration:</td><td><a href="#" id="showcfg">View</a></td></tr>
        <tr><td>Sessions:</td><td><a href="#" id="showsessions">View</a></td></tr>
        <tr><td>Instance Loads:</td><td><a href="#" id="showinstanceloads">View</a></td></tr>
{% end %}
    </table>
    <br/><br/>
{% end %}
</body>
</html>

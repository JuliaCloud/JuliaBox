{% from juliabox.plugins.parallel import ParallelUIModule %}
<script type="text/javascript">
{% if not ParallelUIModule.is_allowed(handler) %}
/**
{% end %}
    var instance_loc;
    var stopping = false;
    var cluster_start_time = 0;

    function show_cluster_state() {
        parent.Parallel.cluster_status(set_cluster_state, error_cluster_state);
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
                    parent.Parallel.cluster_stop(confirm=false, onstop=null);
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

    $(document).ready(function() {
        $('#addcluster').click(function(event){
            event.preventDefault();
            parent.Parallel.addcluster($('#clustername').val());
        });

        $('#btn_cluster_start').click(function(event){
            event.preventDefault();
            var ninsts = $('#cluster_start_cores_selector').val();
            var spot_price = $('#price_per_core_selector').val();
            //alert("start cluster, ninsts:" + ninsts + ", spot_price:" + spot_price + " at " + instance_loc);
            parent.Parallel.cluster_start(ninsts, instance_loc, spot_price, onstrt=function(){
                //error_cluster_state("Cluster start requested");
                show_cluster_state();
            });
        });

        $('#btn_cluster_stop').click(function(event){
            event.preventDefault();
            //alert("stopping cluster");
            parent.Parallel.cluster_stop(confirm=true, onstop=function(){
                stopping = true;
                //error_cluster_state("Cluster stop requested");
                show_cluster_state();
            });
        });

        show_cluster_state();
        cluster_state_timer = setInterval(show_cluster_state, 60000);
    });
{% if not ParallelUIModule.is_allowed(handler) %}
**/
{% end %}
</script>

{% if not ParallelUIModule.is_allowed(handler) %}
<span style="display:none">
{% end %}
<hr/>
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
<br/>
{% if not ParallelUIModule.is_allowed(handler) %}
</span>
{% end %}
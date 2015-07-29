{% from juliabox.plugins.vol_ebs import JBoxEBSVolUIModule %}
<script type="text/javascript">
{% if not JBoxEBSVolUIModule.is_allowed(handler) %}
/**
{% end %}
    var show_state_timer;
    var all_sections = ['attaching', 'detaching', 'detached', 'attached_ok', 'attached_notok'];

    function show_vol_state() {
        parent.DataVolEBS.volume_status(set_vol_state, error_vol_state);
    };

    function set_vol_state(vs) {
        $('#vol_size').html(vs.disk_size);
        $('#vol_state').show();
        set_visible_section(vs.state);
    };

    function set_visible_section(state) {
        var start_timer = !((state == 0) || (state == 1));
        var timer_interval = 10000;
        var show_section = null;
        if(state == 1) {
            show_section = 'attached_ok';
        }
        else if(state == 0) {
            show_section = 'detached';
        }
        else if(state == 2) {
            show_section = 'attaching';
        }
        else if(state == 3) {
            show_section = 'detaching';
        }
        else if(state == -1) {
            show_section = 'attached_notok';
            timer_interval = 60000;
        }

        for(var idx=0; idx < all_sections.length; idx++) {
            section = all_sections[idx];
            if(section == show_section) {
                $('#vol_' + section).show();
            }
            else {
                $('#vol_' + section).hide();
            }
        }

        if(!start_timer && show_state_timer) {
            clearInterval(show_state_timer);
            show_state_timer = null;
        }
        else if(start_timer && !show_state_timer) {
            show_state_timer = setInterval(show_vol_state, timer_interval);
        }
    };

    function error_vol_state(msg) {
        $('#vol_state').hide();
    };

    $(document).ready(function() {
        $('#btn_vol_attach').click(function(event){
            event.preventDefault();
            parent.DataVolEBS.attach(onstrt=function(){
                set_visible_section(2);
            });
        });
        show_vol_state();
    });
{% if not JBoxEBSVolUIModule.is_allowed(handler) %}
**/
{% end %}
</script>

{% if not JBoxEBSVolUIModule.is_allowed(handler) %}
<span style="display:none">
{% end %}
<hr/>
<h3>Data Volume:</h3>
    <table class="table">
	    <tr><td>Size:</td><td><span id='vol_size'>Unknown</span></td></tr>
        <tr id="vol_state" style="display:none">
            <td>State:</td>
            <td>
                <span id="vol_attaching">Attaching</span>
                <span id="vol_detaching">Detaching</span>
                <span id="vol_attached_ok">Attached <small>(/mnt/data)</small></span>
                <span id="vol_attached_notok">
                    <small>
                        Your data volume appears to be in error. <span id="vol_error_state"></span><br/>
                        Please contact the administrators if it does not recover automatically (may take up to 30 minutes).
                    </small>
                </span>
                <span id="vol_detached">
                    Detached &nbsp;&nbsp;&nbsp;&nbsp;
                    <input type="button" value="Attach" id="btn_vol_attach" class="btn btn-primary"/>
                    <br/>
                    <small>
                        Volume will be attached at /mnt/data. It may take up to a minute.<br/>
                        Logging out will detach the volume and schedule a backup.
                    </small>
                </span>
            </td>
        </tr>
</table>
<br/>
{% if not JBoxEBSVolUIModule.is_allowed(handler) %}
</span>
{% end %}
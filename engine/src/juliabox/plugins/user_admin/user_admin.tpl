{% from juliabox.plugins.user_admin import UserAdminUIModule %}
<script type="text/javascript">
{% if not UserAdminUIModule.is_allowed(handler) %}
/**
{% end %}

    function encode_str(unsafestring) {
        var safestring = $('<div>').text(unsafestring).html();
        return safestring;
    };

    function large_bit_and(val1, val2) {
        var shift = 0, result = 0;
        var mask = ~((~0) << 30); // Gives us a bit mask like 01111..1 (30 ones)
        var divisor = 1 << 30; // To work with the bit mask, we need to clear bits at a time
        while( (val1 != 0) && (val2 != 0) ) {
            var rs = (mask & val1) & (mask & val2);
            val1 = Math.floor(val1 / divisor); // val1 >>> 30
            val2 = Math.floor(val2 / divisor); // val2 >>> 30
            for(var i = shift++; i--;) {
                rs *= divisor; // rs << 30
            }
            result += rs;
        }
        return result;
    };

    function set_checkbox(cbname, val, mask) {
        $('#user_admin_' + cbname).prop('checked', (large_bit_and(val, mask) == mask));
    };

    function get_checkbox(cbname, val, mask) {
        if($('#user_admin_' + cbname).prop('checked') != true) {
            return val;
        }
        if((val == 8589934591) || (mask == 8589934591)) {
            return 8589934591;
        }
        return val | mask;
    };

    function display_user(user) {
        if(user.user_id != $('#user_admin_user_id').val()) {
            return;
        }
        $('#user_admin_save').show();
        $('#user_admin_user_props').show();

        var ncores = user.cores;
        $('#user_admin_ncores').val(ncores);

        var courses = user.courses;
        $('#user_admin_courses').val(courses);

        var role = user.role;
        set_checkbox('role_reports', role, 1 << 0);
        set_checkbox('role_containers', role, 1 << 2);
        set_checkbox('role_courses', role, 1 << 3);
        set_checkbox('role_super', role, 8589934591);

        var resprof = user.resprof;
        set_checkbox('resprof_datavol', resprof, 1 << 0);
        set_checkbox('resprof_precomp', resprof, 1 << 12);
        set_checkbox('resprof_cluster', resprof, 1 << 13);
        set_checkbox('resprof_api', resprof, 1 << 14);
    };

    function get_user() {
        parent.UserAdmin.get($('#user_admin_user_id').val(), display_user);
    };

    function update_user() {
        var courses = $('#user_admin_courses').val();
        var ncores = $('#user_admin_ncores').val();
        ncores = $.trim(ncores);
        if($.isNumeric(ncores)) {
            ncores = parseInt(ncores);
        }
        else {
            return;
        }

        var role = 0;
        role = get_checkbox('role_reports', role, 1 << 0);
        role = get_checkbox('role_containers', role, 1 << 2);
        role = get_checkbox('role_courses', role, 1 << 3);
        role = get_checkbox('role_super', role, 8589934591);

        var resprof = 0;
        resprof = get_checkbox('resprof_datavol', resprof, 1 << 0);
        resprof = get_checkbox('resprof_precomp', resprof, 1 << 12);
        resprof = get_checkbox('resprof_cluster', resprof, 1 << 13);
        resprof = get_checkbox('resprof_api', resprof, 1 << 14);

        attribs = {
            'role': role,
            'resprof': resprof,
            'cores': ncores,
            'courses': courses
        };
        parent.UserAdmin.update($('#user_admin_user_id').val(), attribs, clear_form);
        return false;
    };

    function clear_form() {
        $('#user_admin_save').hide();
        $('#user_admin_user_props').hide();
    };

    $(document).ready(function() {
        clear_form();
        $('#user_admin_view').click(function(event){
            event.preventDefault();
            get_user();
            return false;
        });
        $('#user_admin_save').click(function(event){
            event.preventDefault();
            update_user();
            return false;
        });
    });
{% if not UserAdminUIModule.is_allowed(handler) %}
**/
{% end %}
</script>

{% if not UserAdminUIModule.is_allowed(handler) %}
<span style="display:none">
{% end %}
<hr/>
<h3>User Administration:</h3>
    <input type="text" id="user_admin_user_id" onkeydown="clear_form()"/>
    &nbsp; &nbsp; &nbsp; <a href="#" id="user_admin_view">View</a> &nbsp; &nbsp; &nbsp; <a href="#" id="user_admin_save" style="display: none">Save</a>
    <table class="table" id="user_admin_user_props" style="display: none">
        <tr>
            <td>Role:</td>
            <td>
                <div class="checkbox" id="user_admin_role_div">
                    <label><input id="user_admin_role_reports" type="checkbox" value="1"/>View Reports</label>
                    <label><input id="user_admin_role_containers" type="checkbox" value="4"/>Manage Containers</label>
                    <label><input id="user_admin_role_courses" type="checkbox" value="8"/>Offer Courses</label>
                    <label><input id="user_admin_role_super" type="checkbox" value="8589934591"/>Superuser</label>
                </div>
            </td>
        </tr>
        <tr>
            <td>Resource Profile:</td>
            <td>
                <div class="checkbox" id="user_admin_resprof_div">
                    <label><input id="user_admin_resprof_datavol" type="checkbox" value="1"/>10GB Data Volume</label>
                    <label><input id="user_admin_resprof_precomp" type="checkbox" value="4096"/>Precompiled Packages</label>
                    <label><input id="user_admin_resprof_cluster" type="checkbox" value="8192"/>Parallel Compute</label>
                    <label><input id="user_admin_resprof_api" type="checkbox" value="16384"/>Publish APIs</label>
                </div>
            </td>
        </tr>
        <tr><td>Max Parallel Cores:</td><td><input type="text" id="user_admin_ncores" value=""/></td></tr>
        <tr><td>Courses:</td><td><input type="text" id="user_admin_courses" value=""/></td></tr>
    </table>
<br/>
{% if not UserAdminUIModule.is_allowed(handler) %}
</span>
{% end %}
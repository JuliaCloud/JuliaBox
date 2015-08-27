{% from juliabox.plugins.api_admin import APIAdminUIModule %}
<script type="text/javascript">
{% if not APIAdminUIModule.is_allowed(handler) %}
    function enable_apis() {
        parent.APIAdmin.enable_apis();
        return false;
    };
{% end %}
{% if APIAdminUIModule.is_allowed(handler) %}
    function encode_str(unsafestring) {
        var safestring = $('<div>').text(unsafestring).html();
        return safestring;
    };

    function display_apis(apis) {
        var tbl = '<tr><th>API Name</th><th>Command</th><th>Description URL</th><th>&nbsp;</th></tr>';

        for(var idx=0; idx < apis.length; idx++) {
            api = apis[idx];
            var apirow = '<tr id="api_' + idx + '">';
            apirow += '<td>' + encode_str(api['api_name'])     + '</td>';
            apirow += '<td>' + encode_str(api['cmd'])          + '</td>';
            apirow += '<td><a target="_blank" href="' + api['description'] + '"><span class="glyphicon glyphicon-new-window btn" title="Open description"></span></a></td>';
            apirow += '<td><a href="#" id="btn_api_del_' + idx + '" onclick=\'return delete_api("' + api['api_name'] + '");\'><span class="glyphicon glyphicon-trash" title="Delete"></span></a></td>';
            apirow += '</tr>';
            tbl += apirow;
        }

        tbl += '<tr id="new_api"><td><input type="text" id="n_name" maxlength="32" style="width:100%"/></td><td><input type="text" id="n_cmd" maxlength="512" style="width:100%"/></td><td><input type="text" id="n_desc" maxlength="512" style="width:100%"/></td><td><a href="#" id="btn_add" onclick="return add_api();"><span class="glyphicon glyphicon-plus" title="Add"></span></a></td></tr>';
        $('#api_list').html(tbl);
    };

    function get_apis() {
        parent.APIAdmin.get_apis(display_apis, function(){});
    };

    function add_api() {
        parent.APIAdmin.create_api($('#n_name').val(), $('#n_cmd').val(), $('#n_desc').val(), get_apis);
        return false;
    };

    function delete_api(api_name) {
        parent.APIAdmin.delete_api(api_name, get_apis);
        return false;
    };

    $(document).ready(function() {
        // get apis to display
        get_apis();
        // add hooks on buttons

    });
{% end %}
</script>

<hr/>
<h3>Published APIs:</h3>
{% if not APIAdminUIModule.is_allowed(handler) %}
Host useful packages and functions as REST APIs on JuliaBox.<br/><a href="https://github.com/tanmaykm/JuliaWebAPI.jl" target="_blank">Learn more...</a><br/>
<a href="#" onclick="return enable_apis();">Enable API Publishing</a>
{% end %}
{% if APIAdminUIModule.is_allowed(handler) %}
<table class="table" id="api_list">
</table>
{% end %}
<br/>
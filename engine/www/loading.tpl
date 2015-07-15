{% extends "../../../www/authenticated.tpl" %}

{% block head %}
<script type="text/javascript">
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
{% end %}

{% block tabs %}
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
{% end %}

{% block body %}
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
{% end %}

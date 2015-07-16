{% extends "../../../www/authenticated.tpl" %}

{% block head %}
<script type="text/javascript">
    var tab_init = {
        '#ijulia': {'status': true},
        '#console': {'status': false, 'content': '<iframe src="/hostshell/" id="console-frame" frameborder="0" height="100%" width="100%"></iframe>'},
        '#docs': {'status': false, 'content': '<iframe id="docs-frame" src="//julia.readthedocs.org/en/latest/" frameborder="0" height="100%" width="100%"></iframe>'},
        '#admin': {'status': false, 'content': '<iframe src="/hostadmin/" id="admin-frame" frameborder="0" height="100%" width="100%"></iframe>'},
        '#filesync': {'status': false, 'content': '<iframe src="/hostupload/sync" id="filesync-frame" frameborder="0" height="100%" style="float: left" width="100%"></iframe>'},
        '#fileman': {'status': false, 'content': '<iframe src="/hostupload/" id="upload-frame" frameborder="0" height="100%" style="float: left" width="100%"></iframe>'}
    };

    var ping_timer;

    function load_tab(target) {
        if(!tab_init[target].status) {
            $(target).append(tab_init[target].content);
            tab_init[target].status = true;
        }
    };

    function do_ping() {
        if(JuliaBox._loggedout) {
            clearInterval(ping_timer);
        }
        else {
            JuliaBox.send_keep_alive();
            load_tab('#admin');
        }
    };

    $(document).ready(function() {
        $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
            var target = $(e.target).attr("href");
            load_tab(target);
        });

        $('#logout_btn').click(function(event){
            event.preventDefault();
            JuliaBox.logout();
        });

        JuliaBox.init_inpage_alert($('#msg_body'), $('#in_page_alert'));
        {%if None != creds %}
        JuliaBox.init_gauth_tok("{{creds}}");
        $().gdrive('init', {
            'devkey': 'AIzaSyADAHw6De_orDrpcP9_hC9utXqESDpaut8',
            'appid': '64159081293-43o683d0pcgdq6gn7ms86liljoeklvh3.apps.googleusercontent.com',
            'authtok': '{{authtok}}',
            'user': '{{user_id}}'
        });
        {% end %}
        ping_timer = setInterval(do_ping, 15000);
    });
</script>
<style>
    .bootbox100 { margin: 0 auto; width: 1000px; }
    .bootbox90 { margin: 0 auto; width: 900px; }
    .bootbox80 { margin: 0 auto; width: 800px; }
    .bootbox70 { margin: 0 auto; width: 700px; }
</style>
{% end %}

{% block tabs %}
{% set admin_user = (sessname in cfg["admin_sessnames"]) or (cfg["admin_sessnames"] == []) %}
<div class="navicons">
    <ul class="jb-nav nav nav-tabs" role="tablist">
    <li class="active"><a href="#ijulia" data-toggle="tab"><em class="icon-uniE600"></em><span>IJulia</span></a></li>
    <li><a href="#console" data-toggle="tab" title="Console"><em class="icon-uniE603"></em><span>Console</span></a></li>
    <li><a href="#fileman" data-toggle="tab" title="File Manager"><em class="icon-uniE601"></em><span>Files</span></a></li>
    <li><a href="#filesync" data-toggle="tab" title="Sync &amp; Share"><em class="icon-uniE602"></em><span>Sync</span></a></li>
    <li class="pull-right"><a href="#" id="logout_btn" title="Logout" class="pull-right"><em class="icon-uniE604"></em></a></li>
    <li class="pull-right"><a href="#docs" data-toggle="tab" title="Docs"><em class="icon-uniE605"></em></a></li>
    <li class="pull-right"><a href="#admin" data-toggle="tab" title="{% if admin_user %} Admin {% else %} Account {% end %}"><em class="icon-uniE607"></em></a></li>
    </ul>
</div>
{% end %}

{% block body %}
<div class="tab-content modules">
    <div id="ijulia" class="tab-pane active">
        <iframe src="/hostipnbsession/" id="ijulia-frame" frameborder="0" height="100%" width="100%"></iframe>
        <iframe src="/cors/" id="ijulia-cors" frameborder="0" height="0" width="0" style="display: none"></iframe>
    </div>
    <div id="console" class="tab-pane content-pad"></div>
    <div id="docs" class="tab-pane"></div>
    <div id="filesync" class="tab-pane container"></div>
    <div id="fileman" class="tab-pane container" style="padding-top: 1em;"></div>
    <div id="admin" class="tab-pane container"></div>
</div>

<div id="in_page_alert" class="alert alert-warning alert-dismissible container juliaboxmsg" role="alert" style="display: none;">
    <button type="button" class="close" onclick="JuliaBox.hide_inpage_alert();"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
    <span id="msg_body"></span>
</div>
<div id="modal-overlay" style="display: none;"></div>
<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-28835595-2', 'auto');
  ga('send', 'pageview');
</script>
{% end %}

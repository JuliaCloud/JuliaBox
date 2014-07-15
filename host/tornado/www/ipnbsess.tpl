<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>$$SESSNAME&mdash;TryJulia</title>
  <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
  <link href='http://fonts.googleapis.com/css?family=Raleway|Inconsolata' rel='stylesheet' type='text/css'>
  {% if cfg["env_type"] == "dev" %}
  <link rel="stylesheet/less" type="text/css" href="/assets/css/base.less" />
  <script src="//cdnjs.cloudflare.com/ajax/libs/less.js/1.7.3/less.min.js"></script>
  {% else %}
  <link rel="stylesheet" type="text/css" href="/assets/css/base.css" />
  {% end %}
  <style>iframe{display:none}</style>

</head>
<body>
  <div class="container">
    <div class="row header-row">
      <div class="brand-header">
	<img class="brand-logo" src="/assets/img/juliacloudlogo.png"></img>
	<span class="brand-title">TryJulia</span>
      </div>
      <div class="col-md-9">
	<ul class="nav nav-pills" role="tablist">
	  <li class="active"><a href="#ijulia" data-toggle="tab">IJulia</a></li>
	  <li><a href="#console" data-toggle="tab">Console</a></li>
	  <li><a href="#fileman" data-toggle="tab">File Manager</a></li>
	  <li><a href="#admin" data-toggle="tab">Admin</a></li>
	</ul>
      </div>
    </div><!-- row -->
    <div style="clear:both;"></div>
  </div>

  <div class="tab-content modules">
    <div id="ijulia" class="tab-pane active">
        <iframe src="/hostipnbsession/" id="ijulia-frame" frameborder="0" width="100%"></iframe>  
    </div>
    <div id="console" class="tab-pane fade">
      <div class="container"><!-- IJulia already comes in a bootstrap container -->
        This is a bash session. If you cannot see a blinking cursor below, please right-click, "reset" the terminal and hit "enter". <br/>
        Type "julia" to start a Julia REPL session.<br/><br/>
        
        <iframe src="/hostipnbupl/shellinabox" id="console-frame" frameborder="0" width="100%"></iframe>
      </div>
    </div>
    <div id="fileman" class="tab-pane fade">
      <div class="container">
        Your work directory on this machine is &quot;/home/juser&quot;.<br/>
        All uploaded files would be placed here.<br/><br/>

	<!-- tables! yay! -->
	<table border="0" width="100%">
	  <tr>
            <td width="50%" valign="top">
              <iframe src="/hostipnbupl/" id="upload-frame" frameborder="0" width="100%"></iframe>
            </td>
            <td width="50%" valign="top">
              <iframe src="/hostipnbupl/home/juser/" id="filelist-frame" frameborder="0" width="100%"></iframe>
            </td>
	  </tr>
	</table>
      </div>
    </div>
    <div id="admin" class="tab-pane fade">
      <div class="container">
        <iframe src="/hostadmin/" id="admin-frame" frameborder="0" width="100%"></iframe>
      </div>
    </div>
  </div>

<script src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
<script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
<script src="/assets/js/framebehavior.js" type="text/javascript"></script>
<script type="text/javascript">
$(window).load(function() {
  var frames = ["ijulia", "console", "upload", "filelist", "admin"];
  for(var i=0, l=frames.length; i < l; i++) {
    var frame = $("#" + frames[i] +"-frame"),
    head = frame.contents().find("head");
    function adjustFrame (){
      setIframeHeight(frame[0]);
      head.append('<link rel="stylesheet" href="/assets/css/base.css"/>');
    };
    adjustFrame();
    frame.show(300);
    //head.append('<link rel="stylesheet/less" type="text/css" href="/assets/css/base.less"/>');
    //head.append('<script src="//cdnjs.cloudflare.com/ajax/libs/less.js/1.7.3/less.min.js"><\/script>');
  }

});
</script>

</body>
</html>


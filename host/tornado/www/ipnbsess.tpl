<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>IPNB Session $$SESSNAME</title>
  <link rel="stylesheet" href="http://code.jquery.com/ui/1.11.0/themes/smoothness/jquery-ui.css" />
  <script src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
  <script src="http://code.jquery.com/ui/1.11.0/jquery-ui.min.js"></script>
  <script>
  $(function() {
    $( "#tabs" ).tabs();
  });
  </script>
</head>
<body>
 
<div id="tabs">
  <ul>
    <li><a href="#ijulia">IJulia</a></li>
    <li><a href="#console">Console</a></li>
    <li><a href="#fileman">File Manager</a></li>
    <li><a href="#admin">Admin</a></li>
  </ul>
    <div id="ijulia">
        <iframe src="/hostipnbsession/" frameborder="0" width="100%" height="1000"></iframe>  
    </div>
    <div id="console">
        This is a bash session. If you cannot see a blinking cursor below, please right-click, "reset" the terminal and hit "enter". <br/>
        Type "julia" to start a Julia REPL session.<br/><br/>
        
        <iframe src="/hostipnbupl/shellinabox" frameborder="0" width="100%" height="800"></iframe>  
    </div>
    <div id="fileman">
        Your work directory on this machine is &quot;/home/juser&quot;.<br/>
        All uploaded files would be placed here.<br/><br/>

        <iframe src="/hostipnbupl/" frameborder="0" width="100%" height="1000"></iframe>  
    </div>
    <div id="admin">
        <iframe src="/hostadmin/" frameborder="0" width="100%" height="1000"></iframe>  
    </div>
</div>
 
 
</body>
</html>




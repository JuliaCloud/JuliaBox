<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>IPNB Session $$SESSNAME</title>
  <link rel="stylesheet" href="http://code.jquery.com/ui/1.10.3/themes/smoothness/jquery-ui.css" />
  <script src="http://code.jquery.com/jquery-1.9.1.js"></script>
  <script src="http://code.jquery.com/ui/1.10.3/jquery-ui.js"></script>
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
        <iframe src="/hostipnbupl/shellinabox" frameborder="0" width="100%" height="800"></iframe>  
    </div>
    <div id="fileman">
        <iframe src="/hostipnbupl/" frameborder="0" width="100%" height="1000"></iframe>  
    </div>
    <div id="admin">
        <iframe src="/hostadmin/" frameborder="0" width="100%" height="1000"></iframe>  
    </div>
</div>
 
 
</body>
</html>




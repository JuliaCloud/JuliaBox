<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="">
    <meta name="author" content="">

    <title>JuliaBox</title>

    <!-- Bootstrap core CSS -->
    <link href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css" rel="stylesheet">
    {% if cfg["env_type"] == "dev" %}
    <link rel="stylesheet/less" type="text/css" href="/assets/css/index.less" />
    <script src="//cdnjs.cloudflare.com/ajax/libs/less.js/1.7.3/less.min.js"></script>
    {% else %}
    <link rel="stylesheet" type="text/css" href="/assets/css/index.css" />
    {% end %}

    <!-- Just for debugging purposes. Don't actually copy this line! -->
    <!--[if lt IE 9]><script src="../../docs-assets/js/ie8-responsive-file-warning.js"></script><![endif]-->

    <!-- HTML5 shim and Respond.js IE8 support of HTML5 elements and media queries -->
    <!--[if lt IE 9]>
      <script src="//oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
      <script src="//oss.maxcdn.com/libs/respond.js/1.3.0/respond.min.js"></script>
      <![endif]-->
    <script type="text/javascript" src="//use.typekit.net/cpz5ogz.js"></script>
    <script type="text/javascript">try{Typekit.load();}catch(e){}</script>
  </head>

  <body>
    <div class="container banner-container">
      <div class="col-md-2">
	<img class="logo" src="/assets/img/juliacloudlogo.png">
      </div>
      <div class="col-md-3">
	<h1>Julia<span>Box</span></h1>
      </div>
      <div class="description col-md-7">Run Julia from the Browser. No setup.</div>
    </div>
    <div class="dark-wings">
      <div class="container">
	<div class="col-md-6">
	<div class="punchline line-1">The Julia community is doing amazing things.</div>
	<div class="punchline line-2">We want you in on it!</div>
	</div>
	<div class="col-md-6">
	  <div class="big-button col-md-8 col-md-offset-2 col-sm-offset-0">
	    <form class="form-signin" role="form" action="/hostlaunchipnb/">
	      {% if cfg["gauth"] %}
	      <button class="btn btn-lg btn-primary btn-block gauth-btn" type="submit"  value="Launch">Sign in via Google. <span>It's free!</span></button>
	      {% else %}
	      <input type="text" placeholder="Choose a session name. Hit Return &#x23ce;" class="form-control sessname-box" name="sessname" required autofocus>
	      <input style="display:none" type="submit"  value="Launch">
	      {% end %}
	    </form>
	  </div>
	</div><!-- 6 col -->
      </div>
    </div>
    <div class="container features-container">
      <div class="col-md-3 col-sm-6">
	<img class="icon" src="/assets/img/ipynblogo.png">
	<h3>IJulia</h3>
	<p class="feature-desc">
	  Create IJulia Notebooks<br> and share them.
	</p>
      </div>
      <div class="col-md-3 col-sm-6">
	<img class="icon" src="/assets/img/consoleicon.png">
	<h3>Console</h3>
	<p class="feature-desc">
	  Use in-browser terminal <br> emulator to fully control<br> your Docker instance.
	</p>
      </div>
      <div class="col-md-3 col-sm-6">
	<img class="icon" src="/assets/img/drivelogo.png">
	<h3>Google Drive</h3>
	<p class="feature-desc">
	  Collaborate with others. <br> Sync notebooks and data <br> via Google Drive.
	</p>
      </div>
      <div class="col-md-3 col-sm-6">
	<img class="icon" src="/assets/img/syncicon.png">
	<h3>Sync &amp; Share</h3>
	<p class="feature-desc">
	  Setup folders to sync with <br> remote git repositories.
	</p>
      </div>
    </div>
    <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
</body>
</html>

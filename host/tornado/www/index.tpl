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
      <script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
      <script src="https://oss.maxcdn.com/libs/respond.js/1.3.0/respond.min.js"></script>
      <![endif]-->
  </head>

  <body>
    <div class="container">
	<table class="page-wrap">
	  <tbody>
	    <tr>
	      <td class="banner">
		<div class="description">
		  <img src="/assets/img/juliacloudlogo.png">
		  <h1 class="title">JuliaBox</h1>
		  <p class="subtitle">Run Julia without the fuss of installation.</p>
		</div>
	      </td>
	      <td>
		<form class="form-signin" role="form" action="/hostlaunchipnb/">
		  <h2 class="form-signin-heading">Sign in</h2>
		  {% if cfg["gauth"] == True %}
		  (with your Google id)<br/><br/>
		  {% else %}
		  Please enter a name for your JuliaBox session. <br> 
		  {% end %}
		  {% if cfg["gauth"] == False %}
		  <input type="text" class="form-control" name="sessname" required autofocus>
		  {% end %}
		  <button class="btn btn-lg btn-primary btn-block" type="submit"  value="Launch">Launch JuliaBox</button>
            <!--
		  <label class="checkbox" for="clear_old_sess">
		    <input type="checkbox" name="clear_old_sess" value="true"> Force new session
		  </label>
		  <h3 style="color:Red">{{ err }}</h3>    

		  <p class="instructions">
		    
		    {% if cfg["gauth"] == False %}
		    <b>Session Names: </b> Please use alphanumeric characters only. Underscores are OK.<br><br>
		    {% end %}
		    <b>Rejoing existing sessions: </b> By default, existing sessions with the same name (if found) are reconnected to. <br> 
		    If "Force new" is checked, any old sessions are deleted and a new one instantiated.  
		  </p>
            -->
		</form>
              </td>
	    </tr>
	  </tbody>
	</table>
    </div>
</div><!-- /.container -->
      <!-- Bootstrap core JavaScript
	   ================================================== -->
      <!-- Placed at the end of the document so the pages load faster -->
      <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
</body>
</html>

























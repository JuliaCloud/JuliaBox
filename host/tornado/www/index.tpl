<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="">
    <meta name="author" content="">

    <title>Hosted IJulia</title>

    <!-- Bootstrap core CSS -->
    <link href="//netdna.bootstrapcdn.com/bootstrap/3.0.3/css/bootstrap.min.css" rel="stylesheet">

    <!-- Custom styles for this template -->
    <style>
        body {
        padding-top: 40px;
        padding-bottom: 40px;
        background-color: #eee;
        }

        .form-signin {
        max-width: 330px;
        padding: 15px;
        margin: 0 auto;
        }
        .form-signin .form-signin-heading,
        .form-signin .checkbox {
        margin-bottom: 10px;
        }
        .form-signin .checkbox {
        font-weight: normal;
        }
        .form-signin .form-control {
        position: relative;
        font-size: 16px;
        height: auto;
        padding: 10px;
        -webkit-box-sizing: border-box;
            -moz-box-sizing: border-box;
                box-sizing: border-box;
        }
        .form-signin .form-control:focus {
        z-index: 2;
        }
        .form-signin input[type="text"] {
        margin-bottom: -1px;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
        }
        .form-signin input[type="password"] {
        margin-bottom: 10px;
        border-top-left-radius: 0;
        border-top-right-radius: 0;
        }
    </style>
    
    <!-- Just for debugging purposes. Don't actually copy this line! -->
    <!--[if lt IE 9]><script src="../../docs-assets/js/ie8-responsive-file-warning.js"></script><![endif]-->

    <!-- HTML5 shim and Respond.js IE8 support of HTML5 elements and media queries -->
    <!--[if lt IE 9]>
      <script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
      <script src="https://oss.maxcdn.com/libs/respond.js/1.3.0/respond.min.js"></script>
    <![endif]-->
  </head>

  <body>

    <div class="navbar navbar-inverse navbar-fixed-top" role="navigation">
      <div class="container">
        <div class="navbar-header">
          <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-collapse">
            <span class="sr-only">Toggle navigation</span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
          </button>
          <a class="navbar-brand" href="#">Hosted IJulia</a>
        </div>
        <div class="collapse navbar-collapse">
          <ul class="nav navbar-nav">
            <li class="active"><a href="#">Home</a></li>
            <li><a href="#about">About</a></li>
            <li><a href="#contact">Contact</a></li>
          </ul>
        </div><!--/.nav-collapse -->
      </div>
    </div>

    <div class="container">
    

    
     <form class="form-signin" role="form" action="/hostlaunchipnb/">
        <h2 class="form-signin-heading">Try IJulia!</h2>
        {% if cfg["gauth"] == True %}
            Please sign in using your Google id.<br> 
        {% else %}
            Please enter a name for your IPNB session. <br> 
        {% end %}
        {% if cfg["gauth"] == False %}
        <input type="text" class="form-control" name="sessname" required autofocus>
        {% end %}
        
        <label class="checkbox">
          <input type="checkbox" name="clear_old_sess" value="true"> Force new session
        </label>
        <button class="btn btn-lg btn-primary btn-block" type="submit"  value="Launch">Launch IJulia</button>
        <h3 style="color:Red">{{ err }}</h3>    
        
        {% if cfg["gauth"] == False %}
            <b>NOTE : </b> <br>
            <b>Session Names : </b> Please use alphanumeric characters only. Underscores are OK. 
        {% end %}

            <br>
            <br>
            <b>Rejoing existing sessions : </b> By default, existing sessions with the same name (if found) are reconnected to. <br> 
            If "Force new" is checked, any old sessions are deleted and a new one instantiated.  
            <br>
        
        
      </form>
      
    </div><!-- /.container -->


    <!-- Bootstrap core JavaScript
    ================================================== -->
    <!-- Placed at the end of the document so the pages load faster -->
    <script src="//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
    <script src="//netdna.bootstrapcdn.com/bootstrap/3.0.3/js/bootstrap.min.js"></script>
</body>
</html>

























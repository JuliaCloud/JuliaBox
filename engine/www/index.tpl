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

    <!-- HTML5 shim and Respond.js IE8 support of HTML5 elements and media queries -->
    <!--[if lt IE 9]>
    <script src="//oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
    <script src="//oss.maxcdn.com/libs/respond.js/1.3.0/respond.min.js"></script>
    <![endif]-->
    <script type="text/javascript" src="//use.typekit.net/cpz5ogz.js"></script>
    <script type="text/javascript">try{Typekit.load();}catch(e){}</script>
    <script type="text/javascript">
        function areCookiesEnabled() {
            var cookieEnabled = navigator.cookieEnabled;
            if (cookieEnabled === false) return false;
            if (!document.cookie && (cookieEnabled === null || /*@cc_on!@*/false)) {
                document.cookie = "testcookie=1";
                if (!document.cookie) return false;
                else document.cookie = "testcookie=; expires=" + new Date(0).toUTCString();
            }
            return true;
        };
        
        function valLoginForm() {
        	if(!areCookiesEnabled()) {
        		alert("Your browser settings do not allow cookies. JuliaBox requires cookies to log you in. Please enable them in your browser settings and try again.");
        		return false; 
        	}
        	return true;
        }
        function deleteAllCookies() {
            var cookies = document.cookie.split(";");

            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i];
                var eqPos = cookie.indexOf("=");
                var name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
                document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT";
            }
        }
        function resetState() {
            deleteAllCookies();
            window.location = "//accounts.google.com/logout";
        }
    </script>
</head>
<body>
    <div class="container banner-container">
        <div class="col-md-2"><img class="logo" src="/assets/img/juliacloudlogo.png"></div>
        <div class="col-md-3"><h1>JuliaBox <sup>beta</sup></h1></div>
        <div class="description col-md-7">Run Julia from the Browser. No setup.</div>
    </div>

    <div class="dark-wings">
        <div class="container">
            <div class="punchline-wrap col-md-6">
                <div class="punchline line-1">The Julia community is doing amazing things.</div>
                <div class="punchline line-2">We want you in on it!</div>
            </div>
            <div class="col-md-6">
                <div class="big-button col-md-8 col-md-offset-2 col-sm-offset-0">
                    <br/>
                    <div class="sign-in-container">
                        {% if len(state["error"]) > 0 %}
                        <div class="alert alert-danger" role="alert">
                            <span>{{state["error"]}}</span>
                        </div>
                        {% end %}
                        {% if len(state["info"]) > 0 %}
                        <div class="alert alert-info" role="alert">
                            {{state["info"]}}
                        </div>
                        {% end %}
                        {% if len(state["success"]) > 0 %}
                        <div class="alert alert-success" role="alert">
                            {{state["success"]}}
                        </div>
                        {% end %}
                        {% if len(state["success"]) == 0 and len(state["info"]) == 0 and len(state["error"]) == 0 %}
                        <br/><br/>
                        {% end %}
                        {% if state["pending_activation"] %}
                        <div>Logging in as {{ state["user_id"] }}. <a href="javascript:resetState();">Change</a>.</div>
                        {% else %}
                        <br/>
                        {% include "../../../www/auth_modules.tpl" %}
                        {% end %}
                    </div>
                    <br/>
                </div>
            </div><!-- 6 col -->
        </div>
    </div>

    <div class="container notice" style="border-box: rounded; border-radius: 6px; text-align: center; padding: 1em 4em; margin: 2em auto; background: #da7a3e; display: none;"></div>

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

    <div class="footer">
        <div class="container u-center">
            Classes in these universities are using JuliaBox.
            <br/>
            <a href="http://web.mit.edu"><img height="60" style="padding:.8em" src="/assets/img/mit.jpg"></a>
            <a href="http://stanford.edu"><img height="60" style="padding:.8em" src="/assets/img/stanford.png"></a>
            <a href="http://cuny.edu"><img height="60" style="padding:.8em" src="/assets/img/cuny.jpg"></a>
            <br/>
            <br/>
        </div>
        <div class="container u-center">
            Thank you <a href="http://aws.amazon.com"><img alt="Amazon AWS" class="aws-logo" src="/assets/img/aws-logo.png" ></a> for generously hosting JuliaBox!
        </div>
    </div>
    <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
	<script>
	(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
	(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
	m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
	})(window,document,'script','//www.google-analytics.com/analytics.js','ga');
	
    ga('create', 'UA-28835595-2', 'auto');
    ga('send', 'pageview');
	</script>    
</body>
</html>

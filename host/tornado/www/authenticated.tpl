<html lang="en">
<head>
	<meta charset="utf-8" />
	<title>JuliaBox &mdash; {{user_id}}</title>

	<link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
	<link rel="stylesheet" href="/assets/css/icons.css" />
    {% if cfg["env_type"] == "dev" %}
    <link rel="stylesheet/less" type="text/css" href="/assets/css/base.less" />
    <script src="//cdnjs.cloudflare.com/ajax/libs/less.js/1.7.3/less.min.js"></script>
    {% else %}
    <link rel="stylesheet" type="text/css" href="/assets/css/base.css" />
    {% end %}

	<script src="//cdnjs.cloudflare.com/ajax/libs/underscore.js/1.7.0/underscore-min.js"></script>

    <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.3.0/bootbox.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/jquery-cookie/1.4.1/jquery.cookie.min.js"></script>
    <script src="//apis.google.com/js/client.js"></script>
    <script src="/assets/js/jquery-gdrive.js"></script>
    <script src="/assets/js/juliabox.js"></script>
    {% for js_include in js_includes %}
    <script type="text/javascript" src="{{js_include}}"></script>
    {% end %}
    <script type="text/javascript" src="//use.typekit.net/cpz5ogz.js"></script>
    <script type="text/javascript">try{Typekit.load();}catch(e){}</script>
    {% block head %}
    {% end %}
</head>
<body>
    <div class="header-wrap">
        <div class="container">
            <div class="row header-row">
                <div class="logo-and-name">
                    <img class="brand-logo" src="/assets/img/juliacloudlogo.png"/>
                    <div class="brand-title hidden-xs hidden-sm">JuliaBox<sup> beta</sup></div>
                </div>
                {% block tabs %}
                {% end %}
            </div><!-- row -->
            <div style="clear:both;"></div>
        </div>
    </div>

    {% block body %}
    {% end %}
</body>
</html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>JuliaBox</title>

  <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
  <link rel="stylesheet" href="/assets/css/icons.css" />
    {% if cfg["env_type"] == "dev" %}
    <link rel="stylesheet/less" type="text/css" href="/assets/css/base.less" />
    <script src="//cdnjs.cloudflare.com/ajax/libs/less.js/1.7.3/less.min.js"></script>
    {% else %}
    <link rel="stylesheet" type="text/css" href="/assets/css/base.css" />
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

    <div class="container">
        <table width="100%" height="100%" align="center" valign="middle">
            <tr width="100%" height="100%" align="center" valign="middle">
                <td width="100%" height="100%" align="center" valign="middle">
                    <div>
                      <div>{{message}}</div>
                    </div>
                </td>
            </tr>
        </table>
    </div>
</body>
</html>

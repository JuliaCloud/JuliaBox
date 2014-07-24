<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>IPNB Session {{ d["sessname"] }} </title>
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    <link href='http://fonts.googleapis.com/css?family=Raleway|Inconsolata' rel='stylesheet' type='text/css'>
    <link rel="stylesheet" type="text/css" href="/assets/css/frames.css">
</head>
<body>

<h3>Profile &amp; session info:</h3>
Profile Initialized at: {{d["created"]}} <br/>
Current session started at: {{d["started"]}} <br/>


{% if d["admin_user"] %}
    <hr/>
    <a href="/hostadmin/" class="btn btn-primary btn-lg active" role="button">Refresh</a>
    <a href="/hostadmin/?stop_all=1" class="btn btn-primary btn-lg active" role="button">Stop all containers</a>
    
    <br/><br/>

    <h3> Config </h3>
    <table class="table table-striped">
        <tr><th>Parameter</th><th>Value</th></tr>
        {% for k,v in cfg.iteritems() %}
            {% if k not in ['dummy', 'sesskey'] %}
                <tr><td>{{ k }}</td><td>{{ str(v) }} </td></tr>
            {% end %}
        {% end %}
    </table>

    <br/><br/>
    
    {% for section in d["sections"] %}
        <h3> {{ section[0] }} containers </h3>
        <table class="table table-striped">
            <tr><th>Id</th><th>Status</th><th>Name</th><th colspan="2">Action</th></tr>
            {% for o in section[1] %}
                <tr>
                    <td> {{ o["Id"] }} </td>
                    <td>{{ o["Status"] }} </td>
                    <td>{{ o["Name"] }} </td>
                    <td><a href="/hostadmin/?stop_id={{ o['Id'] }}">Stop</a></td>
                    <td><a href="/hostadmin/?delete_id={{ o['Id'] }}">Delete</a></td>
                </tr>
            {% end %}
        </table>
        <br/><br/>
    {% end %}
{% end %}

<script src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
<script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
<script type="text/javascript">
    var myVar=setInterval(function(){sendKeepAlive()}, 60000);
    function sendKeepAlive() {
        var xmlhttp=new XMLHttpRequest();
        xmlhttp.open("GET","/ping/",true);
        xmlhttp.send();
    }
</script>

</body>
</html>


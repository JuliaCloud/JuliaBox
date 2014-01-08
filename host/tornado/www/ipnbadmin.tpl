<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>IPNB Session {{ d["sessname"] }} </title>
</head>
<body>

{% if d["admin_user"] %}
    <a href="/hostadmin/">Refresh</a><br><br>
    <a href="/hostadmin/?delete_all_inactive=1">Delete all inactive containers</a><br><br>
    <a href="/hostadmin/?delete_all=1">Delete all containers</a> (Active protected containers are not deleted) <br><br>
    
    <br><br>

    <h3> Config </h3>
    <table border="1">  
        <tr><th>Parameter</th><th>Value</th></tr>
        {% for k,v in cfg.iteritems() %}
            {% if k not in ['dummy', 'sesskey'] %}
                <tr><td>{{ k }}</td><td>{{ str(v) }} </td></tr>
            {% end %}
        {% end %}
    </table>

    
    {% for section in d["sections"] %}
        <h3> {{ section[0] }} containers </h3>
        <table border="1">  
            <tr><th>Id</th><th>Status</th><th>Name</th><th>Action</th></tr>
            {% for o in section[1] %}
                <tr>
                <td> {{ o["Id"] }} </td>
                <td>{{ o["Status"] }} </td>
                <td>{{ o["Name"] }} </td>
                <td><a href="/hostadmin/?delete_id={{ o['Id'] }}">Delete</a></td>
                </tr>
            {% end %}
        </table>
        <br><br>
    {% end %}
        
        

{% else %}
    Coming soon...
{% end %}

</body>
</html>




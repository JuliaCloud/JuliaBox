<!DOCTYPE html>
<html>
    <head>
        <title>Hosted IJulia</title>
    </head>
    <body>
    <h1>Try IJulia!</h1>
    <br>
    
    <h3 style="color:Red">{{ err }}</h3>    
{% if cfg["gauth"] == True %}
    We are using Google's authentication facility to identify and authenticate you. <br> 
    Your Google provided email-id will be used to identify your sessions.<br> 
    
{% else %}
    Please enter a name for your IPNB session. <br> 
{% end %}

    <form action="/hostlaunchipnb/">
        Force new : <input type="checkbox" name="clear_old_sess" value="true"> <br> 
    
{% if cfg["gauth"] == False %}
        Name : <input type="text" name="sessname"> Use a unique name <br> 
{% end %}

        <input type="submit" value="Launch">
    </form>

    <br>

{% if cfg["gauth"] == False %}
    <b>NOTE : </b> <br>
    <b>Session Names : </b> Please use alphanumeric characters only. Underscores are OK. 
{% end %}

    <br>
    <br>
    <b>Rejoing existing sessions : </b> By default, existing sessions with the same name (if found) are reconnected to. 
    If "Force new" is checked, any old sessions are deleted and a new one instantiated.  
    <br>
</body>
</html>

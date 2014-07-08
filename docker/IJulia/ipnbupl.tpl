<html>
    <head>
        <title>Session data files</title>
        <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    </head>
<body>

$$ERRMSG

<table border="0" width="100%">
    <tr>
        <td width="50%" valign="top">
            <h2>Upload Files</h2>
            <form name="upload" method="POST" enctype="multipart/form-data" action="/hostipnbupl/upload">
                <input type="file" name="file1"><br>
                <input type="file" name="file2"><br>
                <input type="file" name="file3"><br>
                <input type="file" name="file4"><br>
                <input type="file" name="file5"><br>
                <input type="file" name="file6"><br>
                <input type="submit" class="btn btn-primary" name="submit" value="Upload">
            </form>
        </td>
        <td width="50%" valign="top">
            <iframe src="/hostipnbupl/home/juser/" frameborder="0" width="100%" height="1000"></iframe>  
        </td>
    </tr>
</table>

</body>
</html>

<html>
<head>
    <script src="//cdnjs.cloudflare.com/ajax/libs/dropzone/3.8.4/dropzone.js"></script>
    <link rel="stylesheet" href="//cdnjs.cloudflare.com/ajax/libs/dropzone/3.8.4/css/dropzone.css" />
    <link rel="stylesheet" href="//cdnjs.cloudflare.com/ajax/libs/dropzone/3.8.4/css/basic.css" />
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    <link rel="stylesheet" type="text/css" href="/assets/css/frames.css"/>
</head>

<body>
    <center><table width="100%"><tr><td valign="top">
        <div class="dropzone">
            <table id="dirlistingtbl" class="table table-striped">
                <thead>
                    <tr>
                        <th class="text-left" data-sort="string">
                            {% if currdir != '/' %}
                            <a href="?rel_dir={{prevdir}}"><span class="glyphicon glyphicon-arrow-left btn"></span></a>
                            {% end %}
                            <a href="?rel_dir={{currdir}}"><span class="glyphicon glyphicon-refresh btn"></span></a>
                            {{currdir}}
                        </th>
                    </tr>
                </thead>
                {% for fname in folders %}
                    <tr>
                        <td data-sort-value="{{fname}}"><span class="glyphicon glyphicon-folder-close"></span>&nbsp;<a href="?rel_dir={{currdir}}{{fname}}/"><strong>{{fname}}</strong></a></td>
                    </tr>
                {% end %}
                {% for fname in files %}
                    <tr>
                        <td data-sort-value="{{fname}}"><span class="glyphicon glyphicon-file"></span>&nbsp;<a href="?fetch={{fname}}">{{fname}}</a></td>
                    </tr>
                {% end %}
                <tfoot>
                    <tr>
                        <td colspan="3"><small class="pull-left text-muted">{{nfolders}} folders, {{nfiles}} files</small></td>
                    </tr>
                </tfoot>
            </table>
        </div>
    </td>
    <td width="500px" valign="top" id="juliadropzone" class="dropzone"></td>
    </tr></table></center>

    <script language="javascript">
        var jDropzone = new Dropzone("#juliadropzone", { 
                            url: "file-upload",
                            init: function() {
                                this.on("addedfile", function(file) { 
                                            window.setTimeout(function() {
                                                    location.reload(); 
                                                }, 2000);
                                        });
                                },
                                paramName: "file", // The name that will be used to transfer the file
                                maxFilesize: 10, // MB
                            });
    </script>
</body>
</html>

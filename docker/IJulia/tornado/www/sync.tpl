<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script>    
    	$(document).ready(function() {
    		$('.syncgit').click(function(event){
    			repo = event.target.id.split('_')[1];
    			parent.JuliaBox.sync_syncgit(repo);
    		});

    		$('.syncgdrive').click(function(event){
    			repo = event.target.id.split('_')[1];
    			parent.JuliaBox.sync_syncgdrive(repo);
    		});
    		
    		$('.delgit').click(function(event){
    			repo = event.target.id.split('_')[1];
    			parent.JuliaBox.sync_delgit_confirm(repo);
    		});
    		
    		$('.delgdrive').click(function(event){
    			repo = event.target.id.split('_')[1];
    			parent.JuliaBox.sync_delgdrive_confirm(repo);
    		});
    		
    		$('#addgit').click(function(event){
    			repo = $('#gitrepo').val();
    			loc = $('#gitrepoloc').val();
    			branch = $('#gitbranch').val();
    			parent.JuliaBox.sync_addgit(repo, loc, branch);
    		});
    		
    		$('#addgdrive').click(function(event){
    			gfolder = $('#gfolder').val();
    			loc = $('#gfolderloc').val();
    			parent.JuliaBox.sync_addgdrive(gfolder, loc);
    		});
    		
    		$('#gitrepo').change(function(event){
    			n = $('#gitrepo').val();
    			if(n.length > 0) {
    				d = n.split('/').pop().slice(0, -4)
	    			$('#gitbranch').val('master');
	    			$('#gitrepoloc').val(d)
    			}
    		});

            parent.JuliaBox.register_jquery_folder_field('#gfolder', '#gfolder_selector', '#gfolderloc');
    	});    	
    </script>
</head>

{% import os %}

<body>
	<h3>Google Drive</h3>
    <table class="table table-striped">
        <tr><th>Google Drive Folder</th><th>JuliaBox Folder</th><th>Action</th></tr>
        {% for repokey,repo in gdrive_repos.iteritems() %}
        	{% set reponame = os.path.basename(repo.loc) %}
        	{% set loc = repo.loc %}
            <tr>
            	<td><small>{{reponame}}</small></td>
            	<td><b>{{loc}}</b></td>
            	<td>
            		<span class="glyphicon glyphicon-refresh syncgdrive btn" id="syncgdrive_{{repokey}}" title="Synchronize with Google Drive"></span>
            		<span class="glyphicon glyphicon-trash delgdrive btn" id="delgdrive_{{repokey}}" title="Delete from JuliaBox"></span>
            	</td>
            </tr>
        {% end %}
        <tr>
        	<td>
        		<table width="100%">
        			<tr>
        				<td><input type="text" id="gfolder" class="form-control"></td>
        				<td><span class="glyphicon glyphicon-folder-open btn" id="gfolder_selector" title="Select Google Drive folder"></span></td>
        			</tr>
        		</table>
			</td>
        	<td><input type="text" id="gfolderloc" class="form-control"/></td>
        	<td><span class="glyphicon glyphicon-plus btn" id="addgdrive" title="Add to JuliaBox"></span></td>
        </tr>
    </table>

	<br/>
	<h3>Git Repositories</h3>
    <table class="table table-striped">
        <tr><th>Git Clone URL</th><th>Branch</th><th>JuliaBox Folder</th><th>Action</th></tr>
        {% for repokey,repo in gitrepos.iteritems() %}
        	{% set reponame = os.path.basename(repo.loc) %}
        	{% set repourl = repo.remote_url() %}
        	{% set repobranch = repo.branch_name() %}
        	{% set reposyncicon = "download" if repo.remote_url().startswith("https://") else "refresh" %}
            <tr>
            	<td><small>{{repourl}}</small></td>
            	<td><small><i>{{repobranch}}</i></small></td>
            	<td><b>{{reponame}}</b></td>
            	<td>
            		<span class="glyphicon glyphicon-{{reposyncicon}} syncgit btn" id="syncgit_{{repokey}}" title="Synchronize with remote"></span>
            		<span class="glyphicon glyphicon-trash delgit btn" id="delgit_{{repokey}}" title="Delete from JuliaBox"></span>
            	</td>
            </tr>
        {% end %}
        <tr>
        	<td><input type="text" id="gitrepo" class="form-control"/></td>
        	<td><input type="text" id="gitbranch" class="form-control"/></td>
        	<td><input type="text" id="gitrepoloc" class="form-control"/></td>
        	<td><span class="glyphicon glyphicon-plus btn" id="addgit" title="Add to JuliaBox"></span></td>
        </tr>
    </table>
</body>
</html>


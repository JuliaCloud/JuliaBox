<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    <script src="http://code.jquery.com/jquery-1.11.0.min.js"></script>
    <script>
    	var is_busy = false;
    	
    	function do_action(act, msg_level, msg_body) {
    		if(!is_busy) {
    			is_busy = true;
    			parent.JuliaBox.inpage_alert(msg_level, msg_body);
    			window.location = act;
    		}
    	};
    	
    	function del_repo(repo_id) {
			do_action('?action=delgit&repo=' + repo, 'warning', 'Deleting repository...');    					
    	};
    	
    	function confirm_del_repo(repo_id) {
    		if(is_busy) { return; }
			parent.JuliaBox.popup_confirm('Are you sure you want to delete this repository?', function(res) {
				if(res) {
					del_repo(repo);
				}
			});
    	};
    
    	$(document).ready(function() {
    		$('.syncgit').click(function(event){
    			repo = event.target.id.split('_')[1];
    			do_action('?action=syncgit&repo=' + repo, 'info', 'Synchronizing repository...');
    		});
    		
    		$('.delgit').click(function(event){
    			repo = event.target.id.split('_')[1];
    			confirm_del_repo(repo);
    		});
    		
    		$('#addgit').click(function(event){
    			repo = $('#gitrepo').val();
    			loc = $('#gitrepoloc').val();
    			branch = $('#gitbranch').val();
    			do_action('?action=addgit&repo=' + repo + '&loc=' + loc + '&branch=' + branch, 'info', 'Adding repository...');
    		});
    		
    		$('#addgdrive').click(function(event){
    			gfolder = $('#gfolder').val();
    			loc = $('#gfolderloc').val();
    			do_action('?action=addgdrive&gfolder=' + gfolder + '&loc=' + loc, 'info', 'Adding repository...');
    		});
    		
			{% if None != msg %}
			parent.JuliaBox.inpage_alert('{{msg[0]}}', '{{msg[1]}}');
			{% end %}

            parent.JuliaBox.register_jquery_folder_field('#gfolder', '#gfolder_selector', '#gfolderloc');
    	});    	
    </script>
</head>

{% import os %}

<body>
	<h3>Google Drive</h3>
    <table class="table table-striped">
        <tr><th>JuliaBox Folder</th><th>Google Drive Folder</th><th>Action</th></tr>
        <tr>
        	<td><input type="text" id="gfolderloc" class="form-control"/></td>
        	<td>
        		<table width="100%">
        			<tr>
        				<td><input type="text" id="gfolder" class="form-control"></td>
        				<td><span class="glyphicon glyphicon-folder-open btn" id="gfolder_selector"></span></td>
        			</tr>
        		</table>
			</td>
        	<td><span class="glyphicon glyphicon-plus btn" id="addgdrive"></span></td>
        </tr>
    </table>

	<h3>Git Repositories</h3>
    <table class="table table-striped">
        <tr><th>JuliaBox Folder</th><th>Repository</th><th>Branch</th><th>Action</th></tr>
        {% for repokey,repo in gitrepos.iteritems() %}
        	{% set reponame = os.path.basename(repo.loc) %}
        	{% set repourl = repo.remote_url() %}
        	{% set repobranch = repo.branch_name() %}
        	{% set reposyncicon = "download" if repo.remote_url().startswith("https://") else "refresh" %}
            <tr>
            	<td><b>{{reponame}}</b></td>
            	<td><small>{{repourl}}</small></td>
            	<td><small><i>{{repobranch}}</i></small></td>
            	<td>
            		<span class="glyphicon glyphicon-{{reposyncicon}} syncgit btn" id="syncgit_{{repokey}}"></span>
            		<span class="glyphicon glyphicon-trash delgit btn" id="delgit_{{repokey}}"></span>
            	</td>
            </tr>
        {% end %}
        <tr>
        	<td><input type="text" id="gitrepoloc" class="form-control"/></td>
        	<td><input type="text" id="gitrepo" class="form-control"/></td>
        	<td><input type="text" id="gitbranch" class="form-control"/></td>
        	<td><span class="glyphicon glyphicon-plus btn" id="addgit"></span></td>
        </tr>
    </table>
</body>
</html>


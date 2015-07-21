{% from juliabox.plugins.auth_google import GoogleAuthUIHandler %}
{% set updated_creds = GoogleAuthUIHandler.get_updated_token(handler) %}
<script type="text/javascript">
{% if updated_creds['creds'] is None %}
/**
{% end %}
    $(document).ready(function() {
        JuliaBox.init_gauth_tok("{{updated_creds['creds']}}");
        $().gdrive('init', {
            'devkey': 'AIzaSyADAHw6De_orDrpcP9_hC9utXqESDpaut8',
            'appid': '64159081293-43o683d0pcgdq6gn7ms86liljoeklvh3.apps.googleusercontent.com',
            'authtok': '{{updated_creds['authtok']}}',
            'user': '{{updated_creds['user_id']}}'
        });
    });
{% if updated_creds['creds'] is None %}
**/
{% end %}
</script>
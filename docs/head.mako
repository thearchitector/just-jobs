<%!
    from pdoc.html_helpers import minify_css
%>
<%def name="homelink()" filter="minify_css">
    .homelink {
        display: block;
        font-size: 2em;
        font-weight: bold;
        color: #555;
        padding-bottom: 0.5em;
        border-bottom: 1px solid silver;
    }
    .homelink:hover {
        color: inherit;
    }
    .homelink img {
        width: 100px;
        height: 100px;
        margin: auto;
        margin-bottom: 0.3em;
    }
</%def>

<style>${homelink()}</style>
<link rel="canonical" href="https://thearchitector.github.io/just-jobs/just_jobs">
<link rel="icon" href="https://thearchitector.github.io/just-jobs/logo.png">
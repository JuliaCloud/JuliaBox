// Cheat and inject a CSS or less file into an iframe

function injectStyle(frameId, name, dev) {
    if (dev) {
	var link = document.createElement("link") 
	link.href = "/assets/css/" + name + ".less";
	link.rel = "stylesheet/less";
	link.type = "text/css";
	//frames[frameId].document.head.appendChild(link);
	console.log(document.getElementById(frameId)
		    .contentDocument.head);

	document.getElementById(frameId)
	    .contentDocument.head.appendChild(link);
	var script = document.createElement("script");
	script.src = "/assets/js/less-1.7.3.js";
	script.type="text/javascript";
	//frames[frameId].document.head.appendChild(script);
	document.getElementById(frameId)
	    .contentDocument.head.appendChild(script);
    } else {
	var link = document.createElement("link") 
	link.href = "/assets/css/" + name + ".css";
	link.rel = "stylesheet";
	link.type = "text/css";
	//frames[frameId].document.head.appendChild(link);
	document.getElementById(frameId)
	    .contentDocument.head.appendChild(link);
    }
}

function setIframeHeight(iframe) {
    if (iframe) {
        var iframeWin = iframe.contentWindow || iframe.contentDocument.parentWindow;
        if (iframeWin.document.body) {
            iframe.height = iframeWin.document.documentElement.scrollHeight || iframeWin.document.body.scrollHeight;
        }
    }
};

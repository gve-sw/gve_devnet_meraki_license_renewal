
/*Loading indicator on button*/
function showLoadingText() {
    document.getElementById("login-submit").value = "Loading...";
    document.getElementById("loading-info").hidden = false;
}

function showOriginalText(originalButtonText){
    document.getElementById("login-submit").value = originalButtonText;
}

                          
  
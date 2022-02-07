$(function() {
    /*Show corresponding network list as soon as organization is choosen in dropdown + reset child fields*/
    $('#organizations_select').bind('change', function() {
          $('.network-select').attr("hidden", true);
          $('.network-select .networks').val("0");
          $('.network-select .networks').attr("required", true);
          $('.camera-checkboxes').attr("hidden", true);
          var selectid = $( "#organizations_select option:selected" ).val();
          $('#' + selectid).attr("hidden",false);       
      });                            
  });  

$(function(){
    $("#upload_link").on('click', function(e){
        e.preventDefault();
        $("#upload:hidden").trigger('click');
        document.getElementById("upload").value=""
    });

    $('#upload').on('change', function (e){
        let file = document.getElementById("upload").files[0];
    
        console.log("Uploading file...");
        const API_ENDPOINT = "/extract-api-keys";
        const request = new XMLHttpRequest();
        const formData = new FormData();

        request.open("POST", API_ENDPOINT, true);
        
        request.onreadystatechange = () => {
        if (request.readyState === XMLHttpRequest.DONE && request.status === 200) {
            console.log(request.responseText);
            document.getElementById("api-key-input").value = request.responseText;
        }
        };
        formData.append("file", file);

        request.setRequestHeader('X-CSRFToken', CSRF_TOKEN);
        request.send(formData);
        document.getElementById("upload").value=""
    } );
});

function checkCountry(element) {
    var countryList = [].slice.call(element.parentNode.parentNode.parentNode.parentNode.children);

    for (let c=0; c < countryList.length; c++) {
        if (countryList[c].children[0].children[0].children[0].checked && (countryList[c].children[0].children[0].children[0] !== element) && element.checked) {
            countryList[c].children[0].children[0].children[0].checked = false;
        }
    }

    if (element.checked) {
        document.getElementById("country-display").value = element.getAttribute('data-country');
    } else {
        document.getElementById("country-display").value = 'Select a country...';
    }
}